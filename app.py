import os
import time
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    PostbackEvent, FlexSendMessage
)
from linebot.exceptions import InvalidSignatureError
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
    extract_mentions_from_text
)
from news_module import handle_news_command
from meditation_module import handle_meditation_command

# 加載 .env 文件
load_dotenv()

# 用戶上下文、畫像與速率限制
user_agents = {}
user_last_request_time = {}
user_profiles = {}
user_last_topics = {}  # 用於儲存用戶最近的對話主題

# 載入 LINE Bot 憑證
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = Flask(__name__)

# 指令模式匹配
NEWS_PATTERN = re.compile(r'(新聞|時事|政治|經濟|文化|國際|台灣)')
MEDITATION_PATTERN = re.compile(r'(禪修|六妙門|數息|隨息|止|觀|還|淨)')
PRACTICE_HISTORY_PATTERN = re.compile(r'(我的修行經驗|我修行了|我學佛|我的佛法背景)')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    now = time.time()
    user_message = event.message.text
    
    # 速率限制：3秒內只允許一次
    if user_id in user_last_request_time and now - user_last_request_time[user_id] < 3:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text="請稍候再提問，避免過度頻繁。",
            quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
        ))
        return
    user_last_request_time[user_id] = now
    
    # 存儲當前主題用於生成相關問題
    user_last_topics[user_id] = user_message
    
    # 處理修行歷史記錄
    if PRACTICE_HISTORY_PATTERN.search(user_message):
        analyze_practice_history(user_id, user_message)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text="感謝分享您的修行經驗，我會根據您的背景提供更適合的指導。",
            quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
        ))
        return
    
    # 處理新聞相關命令
    if NEWS_PATTERN.search(user_message):
        response = handle_news_command(user_id, OPENAI_API_KEY, user_message)
        
        # 如果是字典格式，則是Flex消息
        if isinstance(response, dict):
            line_bot_api.reply_message(
                event.reply_token, 
                FlexSendMessage(
                    alt_text="新聞摘要",
                    contents=response,
                    quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
                )
            )
        else:
            # 否則是普通文本消息
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(
                    text=response,
                    quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
                )
            )
        return
    
    # 處理禪修相關命令
    if MEDITATION_PATTERN.search(user_message):
        response = handle_meditation_command(user_id, OPENAI_API_KEY, user_message)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=response,
            quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
        ))
        return
    
    # 處理快速回復命令
    if user_message in QUICK_REPLY_COMMANDS:
        response = handle_quick_reply_request(user_message, user_id, OPENAI_API_KEY)
        
        # 檢查是否是新聞相關的回覆，可能是Flex消息
        if user_message.startswith("請給我今日時事佛教省思") or "新聞" in user_message:
            if isinstance(response, dict):
                line_bot_api.reply_message(
                    event.reply_token, 
                    FlexSendMessage(
                        alt_text="新聞摘要",
                        contents=response,
                        quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
                    )
                )
                return
        
        # 普通文本回覆
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=response,
            quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
        ))
        return
    
    # 處理新聞選擇 (例如 "1", "2", "3")
    if user_message.isdigit() and 1 <= int(user_message) <= 5:
        # 查看上一個消息是否是新聞選項列表
        previous_topic = user_last_topics.get(user_id, "")
        if "請選擇您想要了解的新聞" in previous_topic:
            response = handle_news_command(user_id, OPENAI_API_KEY, None, user_message)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=response,
                quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
            ))
            return
    
    # 檢查是否是新聞反思請求
    if user_message.startswith("請提供新聞佛教反思："):
        response = handle_news_command(user_id, OPENAI_API_KEY, user_message)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text=response,
            quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
        ))
        return
    
    # 添加用戶問題到上下文
    add_user_question(user_id, user_message)
    # 提取關鍵詞
    extract_mentions_from_text(user_id, user_message)
    
    # 一般問答處理
    # 初始化 agent
    if user_id not in user_agents:
        user_agents[user_id] = get_agent(OPENAI_API_KEY, user_id)
    agent = user_agents[user_id]

    try:
        response = agent.run(user_message)
    except Exception as e:
        response = f"抱歉，AI 回答時發生錯誤：{e}"
    
    # 回覆訊息並附帶快速回覆按鈕
    line_bot_api.reply_message(event.reply_token, TextSendMessage(
        text=response,
        quick_reply=generate_quick_replies(user_id, user_message, user_last_topics, OPENAI_API_KEY)
    ))

# 處理 Postback 事件
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    data = event.postback.data
    
    response = handle_quick_reply_request(data, user_id, OPENAI_API_KEY)
    
    # 檢查是否是新聞相關的回覆，可能是Flex消息
    if data.startswith("NEWS_") or "新聞" in data:
        if isinstance(response, dict):
            line_bot_api.reply_message(
                event.reply_token, 
                FlexSendMessage(
                    alt_text="新聞摘要",
                    contents=response,
                    quick_reply=generate_quick_replies(user_id, "", user_last_topics, OPENAI_API_KEY)
                )
            )
            return
    
    # 普通文本回覆
    line_bot_api.reply_message(event.reply_token, TextSendMessage(
        text=response,
        quick_reply=generate_quick_replies(user_id, "", user_last_topics, OPENAI_API_KEY)
    ))

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
