#!/bin/bash

# 確保在正確目錄
cd "$(dirname "$0")"

# 停止現有進程
echo "檢查並停止現有的應用進程..."
pkill -f "python dev.py" || true
pkill -f "python app.py" || true
sleep 2

# 檢查虛擬環境
if [ ! -d ".venv" ]; then
    echo "創建虛擬環境..."
    python3 -m venv .venv
fi

# 激活虛擬環境
source .venv/bin/activate

# 檢查依賴
echo "安裝/更新依賴..."
pip install -r requirements.txt

# 檢查.env文件
if [ ! -f ".env" ]; then
    echo "未找到.env文件，請從.env.example創建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "已創建.env文件，請編輯它添加必要的API密鑰"
    else
        echo "警告：.env.example文件不存在"
    fi
fi

# 清理日誌文件
echo "清理舊的日誌文件..."
truncate -s 0 app.log || true
truncate -s 0 agent.log || true

# 啟動開發服務器（自動重載）
echo "啟動開發服務器（自動重載模式）..."
python dev.py &
DEV_PID=$!

# 等待服務器啟動
echo "等待服務器啟動..."
sleep 3

# 輸出日誌狀態
echo "應用程序已啟動，日誌將存儲在 app.log 和 agent.log 文件中"
echo "按 Ctrl+C 停止應用程序"

# 啟動ngrok (如果安裝了)
if command -v ngrok &> /dev/null; then
    echo "啟動ngrok..."
    echo "獲取ngrok URL後，請在LINE Developers控制台中設置Webhook URL: https://[ngrok-domain]/webhook"
    ngrok http 8080
else
    echo "未找到ngrok，請安裝後手動啟動: ngrok http 8080"
    echo "獲取ngrok URL後，請在LINE Developers控制台中設置Webhook URL: https://[ngrok-domain]/webhook"
    # 保持前臺運行開發服務器
    wait $DEV_PID
fi

# 當ngrok停止時，關閉開發服務器
kill $DEV_PID
echo "已關閉開發服務器" 