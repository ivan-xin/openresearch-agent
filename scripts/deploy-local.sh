#!/bin/bash

# AI Agent 启动脚本
echo "Starting AI Agent..."
echo "Working directory: $(pwd)"

# 检查虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠ Virtual environment not found at venv/bin/activate"
fi

# 检查.env文件
if [ -f ".env" ]; then
    echo "✓ Found .env file"
else
    echo "⚠ .env file not found"
fi

# 启动应用
echo "Starting AI Agent server..."
python ai-agent/main.py
