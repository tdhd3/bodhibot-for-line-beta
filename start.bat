@echo off
setlocal

echo 菩薩小老師啟動腳本

REM 檢查虛擬環境
if not exist ".venv" (
    echo 創建虛擬環境...
    python -m venv .venv
)

REM 激活虛擬環境
call .venv\Scripts\activate

REM 安裝依賴
echo 安裝/更新依賴...
pip install -r requirements.txt

REM 檢查.env文件
if not exist ".env" (
    echo 未找到.env文件，請從.env.example創建...
    if exist ".env.example" (
        copy .env.example .env
        echo 已創建.env文件，請編輯它添加必要的API密鑰
    ) else (
        echo 警告：.env.example文件不存在
    )
)

REM 啟動Flask應用
echo 正在启动应用...
start "Flask App" cmd /k python app.py
echo 获取ngrok URL后，请在LINE Developers控制台中设置Webhook URL: https://[ngrok-domain]/webhook

REM 等待Flask啟動
echo 等待Flask啟動...
timeout /t 3 /nobreak > nul

REM 啟動ngrok（如果安裝了）
where ngrok > nul 2>&1
if %ERRORLEVEL% == 0 (
    echo 正在启动ngrok...
    ngrok http 8080
) else (
    echo 未找到ngrok，請安裝後手動啟動: ngrok http 8080
    REM 保持窗口打開
    pause
)

endlocal 