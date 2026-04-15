#!/usr/bin/env python3
"""
Claude Code 周刊
聚合社区文章 · Reddit · GitHub · Web Search → Claude 总结 → Readwise Reader
用法：python claude_code_weekly.py [--today]
"""

import os
import json
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import anthropic
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
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")

REPO = "anthropics/claude-code"
CC_KEYWORDS = ["claude code", "claude-code", "claudecode", "agentic coding"]
UA = {"User-Agent": "Mozilla/5.0"}

# ── 通用工具 ──────────────────────────────────────────────────────────
def _get_json(url, headers=None):
    h = {**UA, **(headers or {})}
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())
# MARKER_A


def _fetch_rss(url, limit=10):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()
    root = ET.fromstring(content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []
    for item in root.findall(".//item")[:limit]:
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link":  (item.findtext("link") or "").strip(),
            "desc":  (item.findtext("description") or "").strip()[:600],
        })
    if not items:
        for entry in root.findall("atom:entry", ns)[:limit]:
            link_el = entry.find("atom:link", ns)
            items.append({
                "title": (entry.findtext("atom:title", "", ns) or "").strip(),
                "link":  link_el.get("href", "") if link_el is not None else "",
                "desc":  (entry.findtext("atom:summary", "", ns) or "").strip()[:600],
            })
    return items


def _searxng(query, count=10):
    instances = ["https://search.sapti.me", "https://searx.be", "https://search.bus-hit.me"]
    params = urllib.parse.urlencode({"q": query, "format": "json", "categories": "general"})
    for base in instances:
        try:
            data = _get_json(f"{base}/search?{params}")
            results = [{"title": r.get("title",""), "link": r.get("url",""), "desc": r.get("content","")[:400]}
                       for r in data.get("results", [])[:count]]
            if results:
                return results
        except Exception:
            continue
    return []


def _fmt(items):
    return "\n".join(f"- [{it['title']}]({it['link']})\n  {it['desc'][:300]}" for it in items)
# MARKER_B


# ── 信息源（社区优先）────────────────────────────────────────────────

def fetch_devto():
    print("  dev.to...")
    try:
        items = _fetch_rss("https://dev.to/feed/tag/claudecode", limit=15)
        if not items:
            items = _fetch_rss("https://dev.to/feed/tag/claude-code", limit=15)
        return f"\n### dev.to 社区文章\n{_fmt(items)}" if items else ""
    except Exception as e:
        print(f"  ⚠️  dev.to 失败: {e}")
        return ""


def fetch_medium():
    print("  Medium...")
    try:
        items = _fetch_rss("https://medium.com/feed/tag/claude-code", limit=15)
        return f"\n### Medium 文章\n{_fmt(items)}" if items else ""
    except Exception as e:
        print(f"  ⚠️  Medium 失败: {e}")
        return ""


def fetch_reddit():
    print("  Reddit r/ClaudeAI...")
    try:
        req = urllib.request.Request(
            "https://old.reddit.com/r/ClaudeAI/.rss",
            headers={"User-Agent": "claude-code-weekly/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = []
        for entry in root.findall("atom:entry", ns)[:25]:
            title = (entry.findtext("atom:title", "", ns) or "").strip()
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            desc = (entry.findtext("atom:summary", "", ns) or "").strip()[:600]
            text = f"{title} {desc}".lower()
            if any(kw in text for kw in CC_KEYWORDS):
                items.append(f"- [{title}]({link})\n  {desc[:300]}")
        return f"\n### Reddit 讨论\n" + "\n".join(items) if items else ""
    except Exception as e:
        print(f"  ⚠️  Reddit 失败: {e}")
        return ""


def fetch_web_search():
    print("  Web Search...")
    try:
        results = _searxng("claude code 教程 技巧 工作流 2026", count=10)
        lines = [f"- [{r['title']}]({r['link']})\n  {r['desc']}" for r in results]
        return f"\n### Web 搜索\n" + "\n".join(lines) if lines else ""
    except Exception as e:
        print(f"  ⚠️  Web Search 失败: {e}")
        return ""


def fetch_github_releases():
    print("  GitHub Releases...")
    try:
        gh = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            gh["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        releases = _get_json(f"https://api.github.com/repos/{REPO}/releases?per_page=5", gh)
        lines = []
        for r in releases:
            name = r.get("name") or r.get("tag_name", "")
            date = r.get("published_at", "")[:10]
            body = r.get("body", "")[:2000]
            url  = r.get("html_url", "")
            lines.append(f"- **{name}** ({date})\n  {body}\n  → [链接]({url})")
        return f"\n### GitHub 版本发布\n" + "\n".join(lines) if lines else ""
    except Exception as e:
        print(f"  ⚠️  GitHub Releases 失败: {e}")
        return ""


def fetch_github_issues():
    print("  GitHub Issues (高热度)...")
    try:
        gh = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            gh["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        issues = _get_json(f"https://api.github.com/repos/{REPO}/issues?state=open&sort=comments&direction=desc&per_page=5", gh)
        lines = []
        for i in issues:
            if "pull_request" in i:
                continue
            title = i.get("title", "")
            url   = i.get("html_url", "")
            comments = i.get("comments", 0)
            lines.append(f"- **{title}** ({comments} comments) → [链接]({url})")
        return f"\n### GitHub 热门 Issue\n" + "\n".join(lines) if lines else ""
    except Exception as e:
        print(f"  ⚠️  GitHub Issues 失败: {e}")
        return ""
# MARKER_C


# ── 聚合（社区内容排前面）────────────────────────────────────────────
FETCHERS = [
    fetch_devto,
    fetch_medium,
    fetch_reddit,
    fetch_web_search,
    fetch_github_releases,
    fetch_github_issues,
]

def collect_all():
    print("📡 抓取信息源...")
    parts = []
    for fn in FETCHERS:
        try:
            r = fn()
            if r:
                parts.append(r)
        except Exception:
            pass
    print(f"  ✅ {len(parts)}/{len(FETCHERS)} 个源返回数据")
    return "\n".join(parts)


# ── Prompt（从同目录的 Markdown 文件读取）────────────────────────────
WEEKLY_PROMPT = (Path(__file__).parent / "claude_code_weekly_prompt.md").read_text(encoding="utf-8")
# MARKER_D


# ── Claude 总结 ───────────────────────────────────────────────────────
def summarize(raw_content, date_label):
    print("🤖 Claude 生成周刊...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": f"{WEEKLY_PROMPT}\n\n## 本周原始素材（{date_label}）\n{raw_content}"}],
    )
    return message.content[0].text


# ── 写入 Readwise ─────────────────────────────────────────────────────
def save_to_readwise(summary, date_str):
    print("📥 写入 Readwise Reader...")
    payload = json.dumps({
        "url":            f"https://claude-code-weekly.local/{date_str}",
        "title":          f"Claude Code 周刊 · {date_str}",
        "author":         "Claude Code 周刊",
        "category":       "article",
        "tags":           ["claude-code-weekly"],
        "published_date": date_str,
        "html":           md.markdown(summary, extensions=["extra"]),
    }).encode()
    req = urllib.request.Request(
        "https://readwise.io/api/v3/save/", data=payload,
        headers={"Authorization": f"Token {READWISE_TOKEN}", "Content-Type": "application/json"},
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
    tz_bj = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tz_bj).date()
    end   = today - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=6)
    date_label = f"{start.month}月{start.day}日 ~ {end.month}月{end.day}日"
    date_str   = end.isoformat()

    print(f"\n🗓  生成 Claude Code 周刊 · {date_label}\n")

    raw = collect_all()
    if not raw.strip():
        print("⚠️  所有源均抓取失败，退出")
        return

    summary = summarize(raw, date_label)
    print("\n" + "─" * 60)
    print(summary)
    print("─" * 60 + "\n")

    save_to_readwise(summary, date_str)


if __name__ == "__main__":
    main()