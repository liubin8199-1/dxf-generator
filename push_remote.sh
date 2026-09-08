#!/usr/bin/env bash
# 用法（仓库建好后执行）：
#   bash push_remote.sh <仓库URL>
# 例：bash push_remote.sh https://github.com/liubin8199-1/dxf-generator.git
set -e
URL="$1"
if [ -z "$URL" ]; then echo "用法: bash push_remote.sh <仓库URL>"; exit 1; fi
cd "C:/Users/binliu8199/.workbuddy/skills/dxf-generator"
git remote remove origin 2>/dev/null || true
git remote add origin "$URL"
git branch -M main
git push -u origin main
echo "推送完成: $URL"
