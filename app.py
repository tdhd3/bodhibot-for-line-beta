import os
import time
import re
import json
import logging
import traceback
import threading
import queue
import uuid
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, abort, jsonify
from functools import wraps
from typing import Dict, Any, Optional, List, Tuple, Union
from threading import Lock

# 使用LINE Bot SDK v3
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
    QuickReply,
    PushMessageRequest
)

from agent import get_agent
from quick_replies import (
    generate_quick_replies,
    handle_quick_reply_request,
    QUICK_REPLY_COMMANDS
)
from user_context import (
    get_user_context,
    add_user_question,
    analyze_practice_history,
    extract_mentions_from_text,
    save_user_feedback,
    update_user_context,
    add_to_chat_history,
    get_chat_history,
    get_recent_messages_for_context
)
from news_module import handle_news_command
from meditation_module import handle_meditation_command
from news_retrieval import get_news
from meditation_guide import get_meditation_guidance

# 加載 .env 文件
load_dotenv()

# 用戶上下文、畫像與速率限制
user_agents = {}
user_last_request_time = {}
user_profiles = {}
user_last_topics = {}  # 用於儲存用戶最近的對話主題
user_chat_histories = {}  # 用於存儲每個用戶的聊天歷史
user_processing_status = {}  # 用於追蹤用戶消息處理狀態
message_queues = {}  # 為每個用戶維護一個消息隊列
processing_locks = {}  # 用户处理锁
last_processing_time = {}  # 用户上次处理消息的时间

# 限制同一用户消息处理频率的最小间隔（秒）
MIN_PROCESSING_INTERVAL = 10

# 初始化线程池
message_processing_thread = None

# 載入 LINE Bot 憑證
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 初始化LINE API客户端
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)

app = Flask(__name__)

# 指令模式匹配
NEWS_PATTERN = re.compile(r'(新聞|時事|政治|經濟|文化|國際|台灣)')
MEDITATION_PATTERN = re.compile(r'(禪修|六妙門|數息|隨息|止|觀|還|淨)')
PRACTICE_HISTORY_PATTERN = re.compile(r'(我的修行經驗|我修行了|我學佛|我的佛法背景)')

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 添加重試裝飾器
def retry(max_tries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    logger.warning(f"函數 {func.__name__} 執行失敗 (嘗試 {tries}/{max_tries}): {str(e)}")
                    if tries == max_tries:
                        logger.error(f"函數 {func.__name__} 最終失敗: {str(e)}", exc_info=True)
                        raise
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@app.route("/webhook", methods=['POST'])
def webhook():
    # 获取HTTP请求头中的X-Line-Signature字段值
    signature = request.headers['X-Line-Signature']

    # 获取请求内容
    body = request.get_data(as_text=True)
    app.logger.info("Request body: %s", body)

    # 验证签名
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """处理用户发送的文本消息"""
    user_id = event.source.user_id
    text = event.message.text
    reply_token = event.reply_token
    
    # 确保用户有一个消息队列
    if user_id not in message_queues:
        message_queues[user_id] = queue.Queue()
        processing_locks[user_id] = Lock()
    
    # 检查用户是否已经有正在处理的消息
    is_processing = user_processing_status.get(user_id, False)
    
    # 检查是否需要限制处理频率
    current_time = time.time()
    last_time = last_processing_time.get(user_id, 0)
    time_since_last = current_time - last_time
    
    # 准备队列消息
    message_id = str(uuid.uuid4())
    queue_item = (text, reply_token, message_id)
    
    # 将消息加入用户队列
    message_queues[user_id].put(queue_item)
    
    # 如果没有正在处理的消息且时间间隔足够，立即回复并开始处理
    if not is_processing and time_since_last >= MIN_PROCESSING_INTERVAL:
        # 发送即时回复表示消息已收到
        send_response_to_user("我已收到您的訊息，正在處理中...", reply_token)
        
        # 设置用户状态为正在处理
        user_processing_status[user_id] = True
        
        # 启动异步处理
        threading.Thread(target=process_user_messages, args=(user_id,)).start()
    else:
        # 已有消息正在处理，告知用户消息已加入队列
        if is_processing:
            send_response_to_user("您的上一條訊息還在處理中，新的訊息已加入隊列，請稍候...", reply_token)
        else:
            send_response_to_user("您發送訊息的頻率過快，消息已加入隊列，請稍候...", reply_token)
            
            # 检查是否需要启动新的处理线程
            if not is_processing:
                user_processing_status[user_id] = True
                threading.Thread(target=process_user_messages, args=(user_id,)).start()

def process_user_messages(user_id):
    """处理用户消息队列"""
    try:
        while not message_queues[user_id].empty():
            # 获取队列中的下一条消息
            with processing_locks[user_id]:
                if message_queues[user_id].empty():
                    break
                
                text, reply_token, message_id = message_queues[user_id].get()
                
                # 更新最后处理时间
                last_processing_time[user_id] = time.time()
                
                # 处理消息
                app.logger.info(f"处理用户 {user_id} 的消息: {text}")
                
                try:
                    # 使用代理处理消息
                    response = process_user_message(user_id, text)
                    
                    # 发送处理结果给用户
                    push_message_to_user(user_id, response)
                    
                except Exception as e:
                    app.logger.error(f"处理消息时出错: {str(e)}", exc_info=True)
                    # 发送错误消息
                    push_message_to_user(user_id, "很抱歉，處理您的訊息時發生錯誤，請稍後再試。")
                
                # 等待限制时间，避免消息处理过快
                time.sleep(MIN_PROCESSING_INTERVAL)
    finally:
        # 处理完成，重置状态
        user_processing_status[user_id] = False

def process_user_message(user_id, text):
    """处理用户消息并返回响应"""
    try:
        # 處理修行歷史記錄
        if PRACTICE_HISTORY_PATTERN.search(text):
            analyze_practice_history(user_id, text)
            return "感謝分享您的修行經驗，我會根據您的背景提供更適合的指導。"
        
        # 處理新聞相關命令
        if NEWS_PATTERN.search(text):
            response = handle_news_command(user_id, OPENAI_API_KEY, text)
            
            # 如果是字典格式，轉換為JSON字符串
            if isinstance(response, dict):
                return json.dumps(response, ensure_ascii=False)
            
            # 添加到聊天历史
            add_to_chat_history(user_id, text, response)
            return response
        
        # 處理禪修相關命令
        if MEDITATION_PATTERN.search(text):
            response = handle_meditation_command(user_id, OPENAI_API_KEY, text)
            # 添加到聊天历史
            add_to_chat_history(user_id, text, response)
            return response
        
        # 處理快速回復命令
        if text in QUICK_REPLY_COMMANDS:
            response = handle_quick_reply_request(text, user_id, OPENAI_API_KEY)
            
            # 檢查是否是新聞相關的回覆，可能是字典格式
            if text.startswith("請給我今日時事佛教省思") or "新聞" in text:
                if isinstance(response, dict):
                    return json.dumps(response, ensure_ascii=False)
            
            # 添加到聊天历史
            add_to_chat_history(user_id, text, response)
            return response
        
        # 處理新聞選擇 (例如 "1", "2", "3")
        if text.isdigit() and 1 <= int(text) <= 5:
            # 查看上一個消息是否是新聞選項列表
            previous_topic = user_last_topics.get(user_id, "")
            if "請選擇您想要了解的新聞" in previous_topic:
                response = handle_news_command(user_id, OPENAI_API_KEY, None, text)
                # 添加到聊天历史
                add_to_chat_history(user_id, text, response)
                return response
        
        # 檢查是否是新聞反思請求
        if text.startswith("請提供新聞佛教反思："):
            response = handle_news_command(user_id, OPENAI_API_KEY, text)
            # 添加到聊天历史
            add_to_chat_history(user_id, text, response)
            return response
        
        # 將問題添加到用戶上下文
        add_user_question(user_id, text)
        
        # 提取文本中提及的關鍵詞
        extract_mentions_from_text(user_id, text)
        
        # 記錄用戶最近的對話主題
        user_last_topics[user_id] = text
        
        # 獲取或初始化用戶的代理
        if user_id not in user_agents:
            user_agents[user_id] = get_agent(OPENAI_API_KEY, user_id)
        
        # 使用代理處理消息
        agent = user_agents[user_id]
        
        # 获取聊天历史记录
        chat_history = get_chat_history(user_id)
        
        # 如果没有聊天历史记录，直接使用代理处理
        if not chat_history:
            response = agent(text)
        else:
            # 将聊天历史记录转换为LangChain消息格式
            langchain_chat_history = []
            for chat in chat_history:
                langchain_chat_history.append({"type": "human", "content": chat["user_message"]})
                langchain_chat_history.append({"type": "ai", "content": chat["bot_response"]})
            
            # 使用带有聊天历史的代理处理
            response = agent(text, langchain_chat_history)
        
        # 添加到聊天历史
        add_to_chat_history(user_id, text, response)
        
        # 返回回答
        return response
            
    except Exception as e:
        app.logger.error(f"處理用戶消息異常: {str(e)}", exc_info=True)
        return "很抱歉，處理您的請求時發生錯誤。請稍後再試。"

def send_response_to_user(text, reply_token):
    """使用reply API发送消息回复用户"""
    try:
        # 檢查回覆類型
        if text.startswith("{") and text.endswith("}"):
            # 嘗試解析為JSON (Flex消息)
            try:
                flex_data = json.loads(text)
                flex_container = FlexContainer.from_dict(flex_data)
                message = FlexMessage(alt_text="回覆內容", contents=flex_container)
            except:
                # 如果解析失敗，作為普通文本發送
                message = TextMessage(text=text)
        else:
            # 普通文本消息
            message = TextMessage(text=text)
            
        # 通過LINE Reply API發送消息
        reply_request = ReplyMessageRequest(
            reply_token=reply_token,
            messages=[message]
        )
        line_bot_api.reply_message(reply_request)
        app.logger.info(f"已發送回覆給用戶 {reply_token}")
        
    except Exception as e:
        app.logger.error(f"發送回覆給用戶失敗: {str(e)}", exc_info=True)

def push_message_to_user(user_id, text):
    """使用push API发送消息给用户"""
    try:
        # 檢查回覆類型
        if text.startswith("{") and text.endswith("}"):
            # 嘗試解析為JSON (Flex消息)
            try:
                flex_data = json.loads(text)
                flex_container = FlexContainer.from_dict(flex_data)
                message = FlexMessage(alt_text="回覆內容", contents=flex_container)
            except:
                # 如果解析失敗，作為普通文本發送
                message = TextMessage(text=text)
        else:
            # 普通文本消息
            message = TextMessage(text=text)
            
        # 通過LINE Push API發送消息
        push_request = PushMessageRequest(
            to=user_id,
            messages=[message]
        )
        line_bot_api.push_message(push_request)
        app.logger.info(f"已發送回覆給用戶 {user_id}")
        
    except Exception as e:
        app.logger.error(f"發送回覆給用戶失敗: {str(e)}", exc_info=True)

@handler.add(FollowEvent)
def handle_follow(event):
    """处理用户关注事件"""
    user_id = event.source.user_id
    welcome_message = "感恩您的關注！我是「菩薩小老師」，一位融合佛教智慧的數位助手。我能協助您理解佛法在日常生活中的應用，提供心靈平靜與智慧的指導。請隨時向我提問，我將盡力以佛法智慧為您解答。祝願您身心安康，福慧增長！🙏"
    
    reply_token = event.reply_token
    send_response_to_user(welcome_message, reply_token)

@app.route("/health", methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    try:
        app.logger.info(f"啟動應用服務器，端口: {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        app.logger.critical(f"應用啟動失敗: {str(e)}", exc_info=True)
