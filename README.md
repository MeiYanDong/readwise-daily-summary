# 每日 AI 日报 · Daily AI Digest

> 每天早上 7 点，自动抓取 AI 前线信息，用 Claude 整理成一份总结，送进你的 Readwise Reader。

---

## 这个项目解决什么问题

信息太多，时间太少。

你订阅了很多 RSS，关注了很多人，每天有几十条新内容进来——但真正坐下来读的时候，根本不知道从哪里开始，很多重要的东西就这么错过了。

另一面是：AI 这个领域每天都在发生真实的变化。新模型、新工具、新的工程思路，不跟上就会慢慢掉队。

这个项目的逻辑很简单：**让机器替你做信息筛选，你只需要每天早上花 3 分钟读一份总结。**

---

## 它是怎么工作的

```
每天 7:00
    ↓
自动抓取 5 个 AI 信息源的最新内容
    ↓
Claude 阅读全部内容，按主题聚类，提炼要点，附上原文链接
    ↓
生成一篇结构清晰的日报，写入你的 Readwise Reader
    ↓
你打开 Reader，3 分钟读完，感兴趣的点进原文
```

**信息源（默认）：**
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
# 2026-04-03 AI 日报

## 📌 今日值得细读
- **Gemma 4 发布** — Google 一次放出 4 款开源多模态模型，31B 排名开源第三 → [链接]

## 🚀 模型发布
- Gemma 4：支持文本/视觉/音频，256K 上下文，Apache 2.0 → [链接]
- Cursor 3 发布，HN 403 分，社区热议 → [链接]

## 🛠️ 工程工具
- llm-gemini 0.30：新增 Gemma 4 支持 → [链接]

## 🔒 安全
- Claude Code 源码泄露事件后续分析 → [链接]

---
> 来源：5 个 RSS 源 | 共 24 条内容
```

---

## 使用前提

你需要有：
- [Readwise Reader](https://readwise.io/read) 账号（用来接收每日日报）
- 一个 Claude 兼容的 API Key（用来做总结，国内可用 [云雾API](https://yunwu.ai) 中转）
- macOS 电脑（用 crontab 定时运行）

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
pip3 install anthropic
```

### 第五步：测试运行

```bash
python3 daily_summary.py --today
```

看到 `✅ 已保存：https://read.readwise.io/read/...` 就成功了。

### 第六步：设置每日自动运行

```bash
chmod +x run_daily_summary.sh

# 添加到 crontab（每天早上 7:00 自动运行）
(crontab -l 2>/dev/null; echo "0 7 * * * $(pwd)/run_daily_summary.sh") | crontab -
```

**注意：** 需要电脑在早上 7:00 开着。如果经常关机，建议改成开机时检查并补跑。

---

## 自定义信息源

打开 `daily_summary.py`，找到 `RSS_SOURCES` 部分，按格式添加或删除：

```python
RSS_SOURCES = [
    ("显示名称",  "RSS链接",  抓取条数),
    ...
]
```

---

## 日志

运行日志保存在 `logs/daily_summary.log`，可以用来排查问题：

```bash
tail -f logs/daily_summary.log
```

---

## 常见问题

**Q：每天花多少 API 费用？**
A：极少。每次调用约 5000-8000 tokens，云雾 API 的 Claude 3.5 Sonnet 约 ¥0.05/次，一个月不到 ¥2。

**Q：能加中文信息源吗？**
A：可以，任何有 RSS 的信息源都能加。比如少数派、即刻、微信公众号（通过 RSSHub）等。

**Q：总结质量不满意怎么办？**
A：修改 `daily_summary.py` 里的 `SUMMARY_PROMPT` 部分，调整输出风格和结构。

---

## License

MIT
