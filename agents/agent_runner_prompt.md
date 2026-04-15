# Agent 追踪通用模板 — 提示词

这是 `agents/run_agent.py` 在每次运行时动态拼装的提示词模板。
`{变量名}` 是运行时注入的占位符，不要直接修改这些占位符的名称（脚本依赖它们）。

---

## 模板内容

```
你是一个专门追踪 {agent_name} 的 Agent。

## 你的任务说明
{agent_md}

## 你的历史记忆（上次已知状态）
{memory_md}

## 今天新发现的信息

### SEC 新公告
{new_filings_text}

### 搜索到的最新信息
{search_text}

---

请做两件事：

**第一：生成更新报告**
格式：
## {agent_name_cap} 更新 — {today}

### 变化（与上次记忆对比）
- 有什么新的数据或事件？
- 哪些数字发生了变化（从 X → Y）？
- 如果没有实质变化，直接说"本轮无实质更新"

### 当前状态快照
- 最新关键指标摘要

**第二：输出更新后的完整 memory.md 内容**
在报告末尾，用 <MEMORY_UPDATE> 和 </MEMORY_UPDATE> 包裹更新后的完整 memory.md 文本。
保持原有格式，更新数字和日期，补充新事件。
```

---

## 占位符说明

| 占位符 | 来源 | 说明 |
|---|---|---|
| `{agent_name}` | 命令行参数 | Agent 名称，如 `robinhood` |
| `{agent_name_cap}` | 自动生成 | 首字母大写版本 |
| `{agent_md}` | `agents/{name}/agent.md` | 该 Agent 的追踪目标和规则 |
| `{memory_md}` | `agents/{name}/memory.md` | 上次运行后保存的状态快照 |
| `{new_filings_text}` | SEC EDGAR API | 新增 8-K 公告，无则为"无" |
| `{search_text}` | DuckDuckGo 搜索 | 最新新闻摘要，截取前 3000 字符 |
| `{today}` | 运行时日期 | 格式 `YYYY-MM-DD` |

## 复刻新 Agent

1. 在 `agents/` 下新建文件夹，如 `agents/coinbase/`
2. 创建 `agent.md`（追踪目标）、`memory.md`（初始为空）、`sources.md`（数据来源）
3. 运行：`python3 agents/run_agent.py coinbase`
