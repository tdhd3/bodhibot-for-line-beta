import os
import multiprocessing
from dotenv import load_dotenv
import subprocess
import signal
import sys
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加載環境變量
load_dotenv()

def run_server():
    # 獲取環境變量
    port = int(os.getenv('PORT', 8080))
    workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))  # Gunicorn推薦的工作進程數
    
    logger.info(f"啟動生產服務器，端口: {port}，工作進程數: {workers}")
    
    # 檢查是否已安裝Gunicorn
    try:
        import gunicorn
    except ImportError:
        logger.error("未安裝Gunicorn，請運行: pip install gunicorn")
        sys.exit(1)
    
    # 構建Gunicorn命令
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", str(workers),
        "--worker-class", "sync",  # 同步工作進程
        "--timeout", "120",  # 請求超時時間
        "--reload",  # 開發環境中使用，生產環境可以移除
        "--access-logfile", "-",  # 將訪問日誌輸出到標準輸出
        "--error-logfile", "-",  # 將錯誤日誌輸出到標準輸出
        "app:app"  # 指定應用模塊
    ]
    
    # 啟動Gunicorn
    process = subprocess.Popen(cmd)
    
    # 處理信號以正常關閉服務器
    def signal_handler(sig, frame):
        logger.info("正在關閉服務器...")
        process.terminate()
        process.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        process.wait()
    except KeyboardInterrupt:
        logger.info("接收到鍵盤中斷，正在關閉服務器...")
        process.terminate()
        process.wait()
        sys.exit(0)

if __name__ == "__main__":
    run_server() 