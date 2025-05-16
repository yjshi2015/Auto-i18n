#!/bin/bash

# 切换到项目目录
cd /Users/gavin/vsc_workspace/Auto-i18n

# 激活虚拟环境
source .venv/bin/activate

# 创建日志目录（如果不存在）
mkdir -p logs

# 获取当前时间作为日志文件名
LOG_FILE="logs/translation_$(date +%Y%m%d_%H%M%S).log"

# 执行翻译脚本并记录日志
python3 auto-translater-course.py zh ja ko 2>&1 | tee "$LOG_FILE"

# 记录执行完成时间
echo "Translation completed at $(date)" >> "$LOG_FILE" 