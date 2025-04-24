#!/bin/bash

# 确保在正确目录
cd "$(dirname "$0")"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖
echo "安装/更新依赖..."
pip install -r requirements.txt

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "未找到.env文件，请从.env.example创建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "已创建.env文件，请编辑它添加必要的API密钥"
    else
        echo "警告：.env.example文件不存在"
    fi
fi

# 启动Flask应用
echo "启动Flask应用..."
python app.py &
APP_PID=$!

# 等待Flask启动
echo "等待Flask启动..."
sleep 3

# 启动ngrok (如果安装了)
if command -v ngrok &> /dev/null; then
    echo "启动ngrok..."
    echo "获取ngrok URL后，请在LINE Developers控制台中设置Webhook URL: https://[ngrok-domain]/webhook"
    ngrok http 8080
else
    echo "未找到ngrok，请安装后手动启动: ngrok http 8080"
    echo "获取ngrok URL后，请在LINE Developers控制台中设置Webhook URL: https://[ngrok-domain]/webhook"
fi

# 当ngrok停止时，关闭Flask应用
kill $APP_PID
echo "已关闭应用程序" 