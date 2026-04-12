#!/usr/bin/env python3
"""
Readwise Reader Feed 每日总结
拉取昨日 feed 内容 → Claude 总结 → 写回 Reader
"""

import os
import json
import datetime
import urllib.request
import markdown as md

READWISE_TOKEN     = os.environ.get("READWISE_TOKEN")     or "KdNIlPZ2Tus2qVqsOUpNP5PXcS1vHRfHZ97eM5h5sAWUU4HgnO"
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")  or "sk-9vj9M2U8pZEuWNTiiE6NARw8prlNkmx14DSO7aRc0veqsXWH"
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL") or "https://yunwu.ai"

SUMMARY_PROMPT = """
## 角色
你是一名信息整理助手，擅长从碎片化的每日信息流（RSS、推文合集、邮件、播客、短文等）中提炼当日的信息全景。
你的目标不是逐篇做深度笔记，而是帮读者在 3 分钟内掌握"今天我的信息流里发生了什么"。

## 任务
将用户提供的某一天的全部 feed 内容，整理为一份**每日信息总结**。

### 核心要求
- **按主题聚类，不按来源罗列**：将当日所有内容按话题/领域归类（如 AI、Crypto、投资、思考/观点、公司动态等），而非按 RSS 源或时间顺序排列。
- **区分信号与噪声**：重点突出有信息量的内容（独到观点、重要事件、值得深读的文章），对纯转发、重复信息、无实质内容的条目可直接忽略或一笔带过。
- **保留原始表达**：引用原文中有力的表达、金句、关键术语，不要过度改写。推文类内容保留其口语化风格。
- **标注值得深读的内容**：对字数较多（>500字）且有深度的文章/newsletter，用 `📌 值得细读` 标记，并附上文章标题、一句话说明为什么值得读，以及**原文链接**。
- **每条信息必须附链接**：每个要点后附上原文 URL。格式：`→ [链接](url)`
- **简洁为上**：每个主题下的条目，用 1-2 句话概括核心信息即可。

### 输出结构

# [日期] Feed 总结

## 📌 今日值得细读
- **[文章标题]** — 一句话说明为什么值得读 → [链接](url)

## [主题1]
- 要点 → [链接](url)

## [主题2]
- 要点 → [链接](url)

---
> 统计：共 X 条 feed，Y 条有实质内容

### 注意事项
- Twitter List 聚合帖：提取其中有信息量的推文要点，忽略无内容转发。
- SEC 文件（8-K 等）：仅保留公司名+一句话说明，不展开。
- 播客：提炼主题和嘉宾信息。
- 如果某天内容很少或全是低质量内容，如实说明，不需要硬凑。
- 语言跟随 feed 内容的主要语言，简洁直接，不加评论不推荐行动。
"""


# ── 拉取 feed 文档列表 ────────────────────────────────────────────────
def fetch_feed_docs(date_str):
    """拉取指定日期的 feed 文档（saved_at 在当天）"""
    print(f"📡 拉取 {date_str} 的 Reader feed...")

    next_day = (datetime.date.fromisoformat(date_str) + datetime.timedelta(days=1)).isoformat()
    url = f"https://readwise.io/api/v3/list/?location=feed&updatedAfter={date_str}T00:00:00Z&pageCursor="

    docs = []
    cursor = ""
    while True:
        req = urllib.request.Request(
            f"https://readwise.io/api/v3/list/?location=feed&updatedAfter={date_str}T00:00:00Z&pageCursor={cursor}",
            headers={"Authorization": f"Token {READWISE_TOKEN}"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        for doc in data.get("results", []):
            saved = doc.get("saved_at", "")[:10]
            if saved == date_str:
                docs.append(doc)

        cursor = data.get("nextPageCursor") or ""
        if not cursor or not data.get("results"):
            break

    print(f"  找到 {len(docs)} 条 feed")
    return docs


# ── 获取文档完整全文 ──────────────────────────────────────────────────
def fetch_doc_full(doc_id):
    req = urllib.request.Request(
        f"https://readwise.io/api/v3/list/?id={doc_id}",
        headers={"Authorization": f"Token {READWISE_TOKEN}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    results = data.get("results", [])
    return results[0] if results else {}


# ── 组合所有内容为文本 ────────────────────────────────────────────────
def build_content(docs, date_str):
    parts = []
    for doc in docs:
        doc_id   = doc.get("id", "")
        title    = doc.get("title", "（无标题）")
        url      = doc.get("source_url") or doc.get("url", "")
        category = doc.get("category", "")
        author   = doc.get("author", "")

        # 用 CLI 拿完整内容
        full = fetch_doc_full(doc_id)
        content = full.get("content", "") or doc.get("content", "") or doc.get("summary", "")

        body = content[:5000] if len(content) > 5000 else content

        parts.append(
            f"### [{title}]({url})\n"
            f"类型: {category} | 作者: {author}\n\n"
            f"{body}\n"
        )
        print(f"  ✓ {title[:40]} ({len(content)} chars)")

    return f"## {date_str} 的 Reader Feed 内容\n\n" + "\n---\n".join(parts)


# ── Claude 总结 ───────────────────────────────────────────────────────
def summarize(raw_content, date_str):
    print("🤖 Claude 生成总结...")
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": f"{SUMMARY_PROMPT}\n\n{raw_content}"}]
    }).encode()
    req = urllib.request.Request(
        "https://yunwu.ai/v1/messages",
        data=payload,
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


# ── 写回 Readwise ─────────────────────────────────────────────────────
def save_to_readwise(summary, date_str):
    print("📥 写入 Readwise Reader...")
    payload = json.dumps({
        "url":            f"https://readwise-feed-summary.local/{date_str}",
        "title":          f"{date_str} Feed 总结",
        "author":         "Feed Summary",
        "category":       "article",
        "tags":           ["feed-summary"],
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
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        url = f"https://read.readwise.io/read/{data['id']}"
        print(f"✅ 已保存：{url}")
        return url


# ── 主流程 ────────────────────────────────────────────────────────────
def main():
    import sys
    if "--today" in sys.argv:
        target = datetime.date.today()
    else:
        target = datetime.date.today() - datetime.timedelta(days=1)

    date_str = target.isoformat()
    print(f"\n🗓  生成 {date_str} 的 Reader Feed 总结\n")

    docs = fetch_feed_docs(date_str)
    if not docs:
        print("⚠️  当日无 feed 内容")
        return

    raw = build_content(docs, date_str)
    summary = summarize(raw, date_str)

    print("\n" + "─" * 60)
    print(summary)
    print("─" * 60 + "\n")

    save_to_readwise(summary, date_str)


if __name__ == "__main__":
    main()
