#!/bin/bash
# 每日 AI 总结 — 由 crontab 调用

export PATH="/Users/myandong/.nvm/versions/node/v20.20.2/bin:/usr/bin:/bin"

LOG="/Users/myandong/Projects/Readwise/logs/daily_summary.log"
mkdir -p "$(dirname "$LOG")"

echo "────────────────────────────" >> "$LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') 开始运行" >> "$LOG"

/usr/bin/python3 /Users/myandong/Projects/Readwise/daily_summary.py >> "$LOG" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') 运行完成" >> "$LOG"
