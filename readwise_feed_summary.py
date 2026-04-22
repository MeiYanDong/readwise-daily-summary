#!/usr/bin/env python3
"""
Readwise Reader Feed 每日总结
拉取昨日 feed 内容 → Claude 总结 → 写回 Reader
"""

import os
import json
import re
import datetime
import socket
import urllib.request
import urllib.error
import markdown as md
from pathlib import Path

READWISE_TOKEN     = os.environ.get("READWISE_TOKEN")     or "KdNIlPZ2Tus2qVqsOUpNP5PXcS1vHRfHZ97eM5h5sAWUU4HgnO"
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")  or "sk-ba2c4b97b557cdd63857ae31ccb37e3ae30c4e7f8c1b93dd0ed65e14486be255"
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL") or "https://xuedingtoken.com"
YUNWU_API_KEY      = os.environ.get("YUNWU_API_KEY")      or "sk-9vj9M2U8pZEuWNTiiE6NARw8prlNkmx14DSO7aRc0veqsXWH"
YUNWU_BASE_URL     = os.environ.get("YUNWU_BASE_URL")     or "https://yunwu.ai"

API_TIMEOUT = 120

SUMMARY_PROMPT = (Path(__file__).parent / "daily_feed_summary_prompt.md").read_text(encoding="utf-8")

# Virtuals Protocol 专属 list ID
VIRTUALS_LIST_ID = "2019389311423246562"

VIRTUALS_PROMPT = (Path(__file__).parent / "virtuals_prompt.md").read_text(encoding="utf-8")


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


# ── 按 Twitter List 分组 ──────────────────────────────────────────────
def group_by_twitter_list(docs):
    """
    返回 { list_id: {"name": str, "docs": [...]} }
    非 Twitter List 的 feed 归入 key=None
    """
    groups = {}
    for doc in docs:
        src = doc.get("source_url", "")
        m = re.search(r"lists/(\d+)", src)
        if m:
            lid = m.group(1)
            if lid not in groups:
                # 从 title 提取 list 名，格式: "{name} Twitter List: ..."
                raw_title = doc.get("title", "")
                name = re.sub(r"\s*Twitter List:.*", "", raw_title).strip() or lid
                groups[lid] = {"name": name, "docs": []}
            groups[lid]["docs"].append(doc)
        else:
            if None not in groups:
                groups[None] = {"name": "其他 Feed", "docs": []}
            groups[None]["docs"].append(doc)
    return groups


# ── 获取文档完整全文 ──────────────────────────────────────────────────
def fetch_doc_full(doc_id):
    req = urllib.request.Request(
        f"https://readwise.io/api/v3/list/?id={doc_id}&withHtmlContent=true",
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
        content = full.get("html_content", "") or full.get("content", "") or doc.get("content", "") or doc.get("summary", "")

        body = content[:15000] if len(content) > 15000 else content

        parts.append(
            f"### [{title}]({url})\n"
            f"类型: {category} | 作者: {author}\n\n"
            f"{body}\n"
        )
        print(f"  ✓ {title[:40]} ({len(content)} chars)")

    return f"## {date_str} 的 Reader Feed 内容\n\n" + "\n---\n".join(parts)


# ── Claude 总结 ───────────────────────────────────────────────────────
def _call_claude(api_key, base_url, payload):
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/messages",
        data=payload,
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type":      "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]


def summarize(raw_content, date_str, prompt=None):
    print("🤖 Claude 生成总结...")
    prompt = prompt or SUMMARY_PROMPT
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": f"{prompt}\n\n{raw_content}"}]
    }).encode()

    try:
        return _call_claude(ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, payload)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as e:
        print(f"⚠️  xueding 请求失败，切换云雾重试: {e}")
        return _call_claude(YUNWU_API_KEY, YUNWU_BASE_URL, payload)


# ── 写回 Readwise ─────────────────────────────────────────────────────
def save_to_readwise(summary, date_str, list_name=None, list_id=None):
    print("📥 写入 Readwise Reader...")
    slug = list_id or "all"
    title = f"{date_str} {list_name} 总结" if list_name else f"{date_str} Feed 总结"
    payload = json.dumps({
        "url":            f"https://readwise-feed-summary.local/{date_str}/{slug}",
        "title":          title,
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
    tz_bj = datetime.timezone(datetime.timedelta(hours=8))
    today_bj = datetime.datetime.now(tz_bj).date()

    if "--today" in sys.argv:
        target = today_bj
    else:
        target = today_bj - datetime.timedelta(days=1)

    date_str = target.isoformat()
    print(f"\n🗓  生成 {date_str} 的 Reader Feed 总结\n")

    docs = fetch_feed_docs(date_str)
    if not docs:
        print("⚠️  当日无 feed 内容")
        return

    # 1. 全量 feed 通用总结
    print("\n── 全量 Feed 总结 ──")
    raw = build_content(docs, date_str)
    summary = summarize(raw, date_str)
    save_to_readwise(summary, date_str)

    # 2. Virtuals Protocol 专属总结
    virtuals_docs = [
        d for d in docs
        if VIRTUALS_LIST_ID in (d.get("source_url") or "")
    ]
    if virtuals_docs:
        print(f"\n── Virtuals Protocol 专属总结（{len(virtuals_docs)} 条）──")
        try:
            raw_v = build_content(virtuals_docs, date_str)
            summary_v = summarize(raw_v, date_str, prompt=VIRTUALS_PROMPT)
            save_to_readwise(summary_v, date_str, list_name="Virtuals Protocol", list_id=VIRTUALS_LIST_ID)
        except Exception as e:
            print(f"⚠️  Virtuals 总结失败（不影响主流程）: {e}")
    else:
        print("\n⚠️  当日无 Virtuals Protocol feed")


if __name__ == "__main__":
    main()
