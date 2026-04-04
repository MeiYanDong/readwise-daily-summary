#!/usr/bin/env python3
"""
每日 AI 信息总结
抓取 RSS 源 → Claude 总结 → 写入 Readwise Reader
"""

import os
import json
import datetime
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import anthropic
import urllib.parse
import markdown as md
from pathlib import Path

# ── 加载 .env ─────────────────────────────────────────────────────────
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── 配置 ──────────────────────────────────────────────────────────────
READWISE_TOKEN     = os.environ.get("READWISE_TOKEN",     "KdNIlPZ2Tus2qVqsOUpNP5PXcS1vHRfHZ97eM5h5sAWUU4HgnO")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY",  "sk-9vj9M2U8pZEuWNTiiE6NARw8prlNkmx14DSO7aRc0veqsXWH")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://yunwu.ai")

RSS_SOURCES = [
    ("AINews 每日速报",    "https://news.smol.ai/rss.xml",                        3),
    ("Simon Willison",     "https://simonwillison.net/atom/everything/",           5),
    ("Ben's Bites",        "https://www.bensbites.com/feed",                       2),
    ("Hacker News Best",   "https://hnrss.org/best",                               8),
    ("arXiv cs.AI",        "https://export.arxiv.org/rss/cs.AI",                   5),
]

SUMMARY_PROMPT = """
## 角色
你是一名信息整理助手，擅长从碎片化的每日信息流（RSS、论文、技术博客等）中提炼当日的信息全景。
目标：帮读者在 3 分钟内掌握"今天 AI 领域发生了什么"。

## 任务
将下方的 RSS 内容整理为一份每日信息总结。

## 核心要求
- **按主题聚类**：将内容按话题归类（如 模型发布、工程工具、行业动态、值得思考 等），不按来源罗列
- **区分信号与噪声**：突出有信息量的内容，忽略纯广告、招聘、重复信息
- **保留原始表达**：引用原文中有力的表达和关键术语，不要过度改写
- **必须附链接**：每条信息后附原文链接，格式 `→ [链接](url)`
- **简洁为上**：每条用 1-2 句话概括，抓重点

## 输出格式

# [日期] AI 日报

## 📌 今日值得细读
- **[标题]** — 一句话说明价值 → [链接](url)

## [主题一]
- 要点 → [链接](url)

## [主题二]
- 要点 → [链接](url)

---
> 来源：X 个 RSS 源 | 共 Y 条内容
"""

# ── 抓取 RSS ──────────────────────────────────────────────────────────
def fetch_rss(name, url, limit):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        items = []

        # RSS 2.0
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", "").strip()
            link  = item.findtext("link", "").strip()
            desc  = item.findtext("description", "").strip()[:500]
            date  = item.findtext("pubDate", "")[:16]
            items.append(f"- [{title}]({link})\n  {desc} ({date})")

        # Atom
        if not items:
            for entry in root.findall("atom:entry", ns)[:limit]:
                title = (entry.findtext("atom:title", "", ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link  = link_el.get("href", "") if link_el is not None else ""
                summary = (entry.findtext("atom:summary", "", ns) or "").strip()[:500]
                date  = (entry.findtext("atom:updated", "", ns) or "")[:10]
                items.append(f"- [{title}]({link})\n  {summary} ({date})")

        return f"\n### {name}\n" + "\n".join(items) if items else ""

    except Exception as e:
        print(f"  ⚠️  {name} 抓取失败: {e}")
        return ""


def collect_feeds():
    print("📡 抓取 RSS 源...")
    parts = []
    for name, url, limit in RSS_SOURCES:
        print(f"  {name}...")
        part = fetch_rss(name, url, limit)
        if part:
            parts.append(part)
    return "\n".join(parts)


# ── Claude 总结 ───────────────────────────────────────────────────────
def summarize(raw_content, date_str):
    print("🤖 Claude 生成总结...")
    client = anthropic.Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
    )
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"{SUMMARY_PROMPT}\n\n## 今日内容（{date_str}）\n{raw_content}"
        }]
    )
    return message.content[0].text


# ── 写入 Readwise ─────────────────────────────────────────────────────
def save_to_readwise(summary, date_str):
    print("📥 写入 Readwise Reader...")
    payload = json.dumps({
        "url":            f"https://daily-ai-summary.local/{date_str}",
        "title":          f"{date_str} AI 日报",
        "author":         "Daily Summary",
        "category":       "article",
        "tags":           ["daily-summary"],
        "published_date": date_str,
        "html":           md.markdown(summary, extensions=["extra"]),
    }).encode()
    req = urllib.request.Request(
        "https://readwise.io/api/v3/save/",
        data=payload,
        headers={
            "Authorization": f"Token {READWISE_TOKEN}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            url = f"https://read.readwise.io/read/{data['id']}"
            print(f"✅ 已保存：{url}")
            return url
    except Exception as e:
        print(f"❌ 写入失败：{e}")
        return None


# ── 主流程 ────────────────────────────────────────────────────────────
def main():
    # 默认总结昨天（保证内容完整），传参 --today 则总结今天
    import sys
    if "--today" in sys.argv:
        target = datetime.date.today()
    else:
        target = datetime.date.today() - datetime.timedelta(days=1)

    date_str = target.isoformat()
    print(f"\n🗓  生成 {date_str} 的 AI 日报\n")

    raw = collect_feeds()
    if not raw.strip():
        print("⚠️  所有源均抓取失败，退出")
        return

    summary = summarize(raw, date_str)
    print("\n" + "─" * 60)
    print(summary)
    print("─" * 60 + "\n")

    save_to_readwise(summary, date_str)


if __name__ == "__main__":
    main()
