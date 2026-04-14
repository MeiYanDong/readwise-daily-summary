#!/usr/bin/env python3
"""
Readwise Reader Feed 每日总结
拉取昨日 feed 内容 → Claude 总结 → 写回 Reader
"""

import os
import json
import re
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

# Virtuals Protocol 专属 list ID
VIRTUALS_LIST_ID = "2019389311423246562"

VIRTUALS_PROMPT = """
## 角色
你是 Virtuals Protocol 的生态观察者，为关注但不深入跟踪这个项目的大众读者写每日动态。
你的读者画像：知道 Virtuals 是什么，可能持有 $VIRTUAL，但不会每天刷推特。他们需要你帮他们回答一个问题：**"今天 Virtuals 有什么值得知道的事？"**

## 项目背景（不要在输出中重复，仅作为你的分析基础）
- Virtuals Protocol：Base 链上最大的 AI Agent 经济基础设施，18000+ agents
- 核心协议：ACP（Agent Commerce Protocol），让 AI Agent 之间可以自主交易
- 代币：$VIRTUAL，2025年初高点 $5+，目前约 $0.67
- 最新战略：Eastworlds（具身 AI / 机器人加速器）
- 竞品：ai16z 等 AI Agent 平台

## 任务
基于推文内容，写一份让普通关注者 3 分钟读完、读完能跟别人聊的动态简报。

## 核心原则

### 排序逻辑（按决策价值从高到低）
1. **"这件事改变了 Virtuals 的故事"** — 新赛道、重大合作、协议级变化
2. **"这件事证明 Virtuals 在往前走"** — 可量化的进展、里程碑达成
3. **"这件事值得留意但还没定论"** — 有潜力但需要后续验证的信号
4. **背景补充** — 丰富理解但不紧急的信息

### 写作要求
- **一件事说三句话就够**：发生了什么 → 为什么重要 → 一句判断
- **说人话**：避免 "alpha"、"thesis"、"narrative" 这类圈内黑话，用普通人能懂的表达
- **有观点但不武断**：给判断，但标注你不确定的地方
- **识别重复叙事**：如果官方连续多天推同一件事，直接说"这件事上周已经公布，今天没有新进展"
- **引用原文金句**：保留推文中最有力的原话
- **噪音直接跳过**：meme、无意义数字、纯互动不出现在输出中

## 输出结构

# [日期] Virtuals Protocol 动态

> **一句话总结**：（读完整篇后能跟朋友说的一句话）

## 今日重点（最多 3 条，按重要性排序）

### 1. [标题]
[发生了什么] → [为什么重要] → [你的判断]
→ [链接](https://twitter.com/xxx/status/xxx)

## 生态动态
- [标签] 一句话 → [链接]
（标签：🛠产品 / 📊数据 / 🤝合作 / 📋合规）

---
> 信号强度：🟢 平静 / 🟡 有动作 / 🔴 重要变化

---
> 加入 Virtuals 生态：[https://app.virtuals.io/referral?code=LFfW5x](https://app.virtuals.io/referral?code=LFfW5x)

## 注意事项
- 长文推文串：完整阅读，提炼核心论点
- 官方周报：挑 2-3 条最重要的展开，其余放生态动态
- 内容不足时直接说"今天没什么大事"
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
def summarize(raw_content, date_str, prompt=None):
    print("🤖 Claude 生成总结...")
    prompt = prompt or SUMMARY_PROMPT
    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": f"{prompt}\n\n{raw_content}"}]
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
        raw_v = build_content(virtuals_docs, date_str)
        summary_v = summarize(raw_v, date_str, prompt=VIRTUALS_PROMPT)
        save_to_readwise(summary_v, date_str, list_name="Virtuals Protocol", list_id=VIRTUALS_LIST_ID)
    else:
        print("\n⚠️  当日无 Virtuals Protocol feed")


if __name__ == "__main__":
    main()
