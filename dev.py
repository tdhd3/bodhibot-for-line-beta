import os
from app import app
from dotenv import load_dotenv
import logging
import multiprocessing

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加載環境變量
load_dotenv()

if __name__ == "__main__":
    # 獲取環境變量
    port = int(os.getenv('PORT', 8080))
    workers = int(os.getenv('WORKERS', multiprocessing.cpu_count()))
    
    logger.info(f"啟動開發服務器，端口: {port}，工作進程數: {workers}")
    logger.info("自動重載已啟用，修改代碼後服務器將自動重啟")
    
    # 使用Flask內置的開發服務器，啟用調試模式和自動重載
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True,  # 啟用調試模式
        use_reloader=True,  # 啟用代碼修改自動重載
        threaded=True  # 啟用線程支持，允許並發處理請求
    ) 