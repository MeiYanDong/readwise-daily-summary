#!/bin/bash
# 每日 Feed 总结 + Virtuals Protocol 追踪 — 由 crontab 调用

export PATH="/Users/myandong/.nvm/versions/node/v20.20.2/bin:/usr/bin:/bin"

LOG="/Users/myandong/Projects/Readwise/logs/feed_summary.log"
mkdir -p "$(dirname "$LOG")"

echo "────────────────────────────" >> "$LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') 开始运行" >> "$LOG"

cd /Users/myandong/Projects/Readwise
unset ANTHROPIC_API_KEY
/usr/bin/python3 readwise_feed_summary.py >> "$LOG" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') 运行完成" >> "$LOG"
