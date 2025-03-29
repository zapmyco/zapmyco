#!/bin/bash
# 简化版启动脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 启动uvicorn服务器（开发模式，支持热更新）
echo "启动后端服务器（开发模式）..."
exec poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
