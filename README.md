# 每日 AI 日报 · Daily AI Digest

> 一套自动化信息流工具，把 AI 前线动态、你的 Readwise 订阅、Claude Code 社区动态，每天整理好送进你的 Reader。

---

## 这个项目解决什么问题

信息太多，时间太少。

你订阅了很多 RSS，关注了很多人，每天有几十条新内容进来——但真正坐下来读的时候，根本不知道从哪里开始，很多重要的东西就这么错过了。

另一面是：AI 这个领域每天都在发生真实的变化。新模型、新工具、新的工程思路，不跟上就会慢慢掉队。

这个项目的逻辑很简单：**让机器替你做信息筛选，你只需要每天早上花 3 分钟读一份总结。**

---

## 包含哪些工具

| 工具 | 脚本 | 运行频率 | 说明 |
|---|---|---|---|
| AI 日报 | `daily_summary.py` | 每天 07:00 | 抓取 5 个 AI RSS 源，Claude 总结后写入 Reader |
| Feed 总结 | `readwise_feed_summary.py` | 每天 07:30 | 总结你昨天 Reader feed 里的所有内容 |
| Claude Code 周刊 | `claude_code_weekly.py` | 每周一 08:00 | 聚合社区文章、Reddit、GitHub，生成周刊 |
| Agent 追踪 | `agents/run_agent.py` | 手动 / 按需 | 持续追踪某个公司或项目，有变化时写入 Reader |

---

## 它是怎么工作的

```
每天 07:00（AI 日报）
    ↓
自动抓取 5 个 AI 信息源的最新内容
    ↓
Claude 阅读全部内容，按主题聚类，提炼要点，附上原文链接
    ↓
生成一篇结构清晰的日报，写入你的 Readwise Reader
    ↓
你打开 Reader，3 分钟读完，感兴趣的点进原文

每天 07:30（Feed 总结）
    ↓
拉取你昨天 Reader feed 里的所有文章
    ↓
Claude 按主题聚类，标出值得细读的内容
    ↓
写回 Reader，标签 feed-summary

每周一 08:00（Claude Code 周刊）
    ↓
抓取 dev.to、Medium、Reddit、GitHub 的 Claude Code 相关内容
    ↓
Claude 整理成"本周最酷 / 别人在用 CC 做什么 / 小技巧 / 新版本"
    ↓
写入 Reader，标签 claude-code-weekly
```

**AI 日报信息源（默认）：**
| 来源 | 定位 |
|---|---|
| [AINews (smol.ai)](https://news.smol.ai) | 最全面的每日 AI 技术速报 |
| [Simon Willison's Weblog](https://simonwillison.net) | 顶级工程师的实测与深度观察 |
| [Ben's Bites](https://www.bensbites.com) | AI 产品与商业视角 |
| [Hacker News Best](https://news.ycombinator.com/best) | 技术社区当日最热 |
| [arXiv cs.AI](https://arxiv.org/list/cs.AI/recent) | 每日最新 AI 论文 |

---

## 输出样例

```
# 2026-04-14 AI 日报

## 📌 今日值得细读
- **Gemma 4 发布** — Google 一次放出 4 款开源多模态模型，31B 排名开源第三 → [链接]

## 🚀 模型发布
- Gemma 4：支持文本/视觉/音频，256K 上下文，Apache 2.0 → [链接]
- Cursor 3 发布，HN 403 分，社区热议 → [链接]

## 🛠️ 工程工具
- llm-gemini 0.30：新增 Gemma 4 支持 → [链接]

---
> 来源：5 个 RSS 源 | 共 24 条内容
```

---

## 使用前提

你需要有：
- [Readwise Reader](https://readwise.io/read) 账号（用来接收每日日报）
- 一个 Claude 兼容的 API Key（用来做总结，国内可用 [云雾API](https://yunwu.ai) 中转）
- macOS 电脑（用 crontab 定时运行）或 GitHub 账号（用 Actions 自动运行）

不需要懂编程。按照下面的步骤操作就行。

---

## 安装步骤

### 第一步：安装 Node.js 和 Readwise CLI

```bash
# 安装 nvm（Node 版本管理器）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.zshrc

# 安装 Node.js
nvm install --lts

# 安装 Readwise CLI
npm install -g @readwise/cli

# 登录 Readwise（用 token，在 readwise.io/access_token 获取）
readwise login-with-token 你的TOKEN
```

### 第二步：下载这个项目

```bash
git clone https://github.com/myandong/readwise-daily-summary.git
cd readwise-daily-summary
```

### 第三步：配置 API Key

复制配置模板，填入你的 key：

```bash
cp .env.example .env
```

用任意文本编辑器打开 `.env`，填写：

```
READWISE_TOKEN=你的Readwise Token
ANTHROPIC_API_KEY=你的API Key
ANTHROPIC_BASE_URL=https://yunwu.ai   # 国内用这个，官方用 https://api.anthropic.com
```

### 第四步：安装 Python 依赖

```bash
pip3 install anthropic markdown
```

### 第五步：测试运行

```bash
# 测试 AI 日报
python3 daily_summary.py --today

# 测试 Feed 总结
python3 readwise_feed_summary.py --today

# 测试 Claude Code 周刊
python3 claude_code_weekly.py
```

看到 `✅ 已保存：https://read.readwise.io/read/...` 就成功了。

### 第六步：设置每日自动运行

**方式一：GitHub Actions（推荐，不需要电脑一直开着）**

把仓库 fork 到你自己的 GitHub，然后在仓库的 Settings → Secrets and variables → Actions 里添加三个 Secret：

| Secret 名称 | 值 |
|---|---|
| `READWISE_TOKEN` | 你的 Readwise Token |
| `ANTHROPIC_API_KEY` | 你的 API Key |
| `ANTHROPIC_BASE_URL` | `https://yunwu.ai`（或官方地址） |

Actions 会自动按时运行，无需其他操作。

**方式二：本地 crontab（需要电脑在对应时间开着）**

```bash
chmod +x run_daily_summary.sh run_feed_summary.sh

# 添加到 crontab
(crontab -l 2>/dev/null; echo "0 7 * * * $(pwd)/run_daily_summary.sh") | crontab -
(crontab -l 2>/dev/null; echo "30 7 * * * $(pwd)/run_feed_summary.sh") | crontab -
```

---

## 自定义信息源（AI 日报）

打开 `daily_summary.py`，找到 `RSS_SOURCES` 部分，按格式添加或删除：

```python
RSS_SOURCES = [
    ("显示名称",  "RSS链接",  抓取条数),
    ...
]
```

---

## 修改总结风格

所有提示词都以 Markdown 文件的形式存放在项目根目录，直接用文本编辑器打开修改即可，不需要改 Python 代码：

| 文件 | 对应功能 |
|---|---|
| `daily_summary_prompt.md` | AI 日报的总结风格 |
| `daily_feed_summary_prompt.md` | Feed 总结的风格 |
| `claude_code_weekly_prompt.md` | Claude Code 周刊的风格 |
| `virtuals_prompt.md` | Virtuals Protocol 专项总结 |

---

## Agent 追踪（进阶）

Agent 追踪框架可以持续监控某个公司或项目，有实质变化时自动写入 Reader。

**内置示例：Robinhood（$HOOD）**

```bash
python3 agents/run_agent.py robinhood
```

**添加新的追踪目标**

在 `agents/` 下新建文件夹，创建三个文件：

```
agents/
└── coinbase/
    ├── agent.md    # 追踪目标和关注维度
    ├── memory.md   # 初始为空，Agent 会自动维护
    └── sources.md  # 数据来源说明
```

`agent.md` 示例：

```markdown
# Coinbase Agent

## 追踪目标
Coinbase Global, Inc.（$COIN）

## 关注维度
- 月度交易量数据
- 季度财报
- 监管动态
- 新产品上线
```

然后运行：

```bash
python3 agents/run_agent.py coinbase
```

---

## 日志

运行日志保存在 `logs/` 目录，可以用来排查问题：

```bash
tail -f logs/daily_summary.log
```

---

## 常见问题

**Q：每天花多少 API 费用？**
A：极少。AI 日报每次约 5000-8000 tokens，云雾 API 的 Claude 3.5 Sonnet 约 ¥0.05/次；Feed 总结视内容量而定，通常 ¥0.1 以内。一个月全部加起来不到 ¥10。

**Q：能加中文信息源吗？**
A：可以，任何有 RSS 的信息源都能加。比如少数派、即刻、微信公众号（通过 RSSHub）等。

**Q：总结质量不满意怎么办？**
A：直接修改对应的 `*_prompt.md` 文件，调整输出风格和结构，不需要改代码。

**Q：Feed 总结拉不到内容怎么办？**
A：确认 Readwise Reader 里有 feed 订阅，且昨天有新内容进来。可以用 `--today` 参数测试当天内容。

---

## License

MIT
