import os
import random
from linebot.models import QuickReply, QuickReplyButton, MessageAction, URIAction
from typing import Dict, List, Optional, Union

# 導入新的模塊
from news_module import handle_news_command
from meditation_module import handle_meditation_command
from user_context import get_user_context, add_user_question

# 快速回應選項
QUICK_REPLY_COMMANDS = {
    "請給我今日時事佛教省思": "NEWS_OPTIONS",
    "請提供禪修引導": "MEDITATION_GUIDE",
    "請提供禪修法門列表": "MEDITATION_OPTIONS",
    "台灣政治新聞": "NEWS_TW_POLITICS",
    "國際經濟新聞": "NEWS_INTL_ECONOMICS",
    "文化新聞": "NEWS_CULTURE"
}

# 用戶回饋表單URL
FEEDBACK_FORM_URL = 'https://docs.google.com/forms/d/17B148aK3REfbUEtmi3isQQEkQwvvIlaKgte00Yde_zE/edit'

def generate_related_question(topic: str, openai_api_key: str) -> Optional[str]:
    """根據主題生成相關問題"""
    if not openai_api_key:
        return None
    
    try:
        from agent import get_agent
        agent = get_agent(openai_api_key, 'quick_reply_generator')
        prompt = f"根據用戶提問「{topic}」，生成一個相關的follow-up問題，簡短20字以內，不要說明，直接給出問題"
        related_question = agent.run(prompt)
        
        if len(related_question) <= 20:
            return related_question
        return related_question[:20]  # 如果太長，截斷到20字
    except Exception as e:
        print(f"生成相關問題失敗: {e}")
        return None

def generate_quick_replies(user_id: str, recent_message: str = "", user_last_topics: Dict = None, openai_api_key: str = None) -> QuickReply:
    """生成快速回覆按鈕"""
    quick_replies = []
    
    # 取得用戶上下文
    user_context = get_user_context(user_id)
    
    # 記錄用戶問題
    if recent_message:
        add_user_question(user_id, recent_message)
    
    # 基本功能按鈕
    quick_replies.append(QuickReplyButton(
        action=MessageAction(label="📰 時事省思", text="請給我今日時事佛教省思")
    ))
    
    quick_replies.append(QuickReplyButton(
        action=MessageAction(label="🧘 禪修引導", text="請提供禪修引導")
    ))
    
    # 用戶回饋按鈕
    quick_replies.append(QuickReplyButton(
        action=URIAction(label="📝 用戶回饋", uri=FEEDBACK_FORM_URL)
    ))
    
    # 如果有最近的對話主題，生成相關問題
    if user_last_topics and user_id in user_last_topics and user_last_topics[user_id]:
        topic = user_last_topics[user_id]
        
        related_question = generate_related_question(topic, openai_api_key)
        if related_question:
            quick_replies.append(QuickReplyButton(
                action=MessageAction(label="❓ " + related_question, text=related_question)
            ))
    
    return QuickReply(items=quick_replies[:4])  # LINE限制最多13個按鈕，但我們只使用4個避免介面擁擠

def handle_quick_reply_request(command: str, user_id: str, openai_api_key: str) -> Union[str, Dict]:
    """處理快速回覆請求，返回文本或Flex消息"""
    # 檢查是否為新聞相關命令
    if command.startswith("NEWS_") or "新聞" in command or "時事" in command:
        return handle_news_command(user_id, openai_api_key, command)
    
    # 檢查是否為禪修相關命令
    elif command.startswith("MEDITATION_") or "禪修" in command:
        return handle_meditation_command(user_id, openai_api_key, command)
    
    # 根據命令轉發到具體處理函數
    if command in QUICK_REPLY_COMMANDS:
        command_code = QUICK_REPLY_COMMANDS[command]
        
        if command_code == "NEWS_OPTIONS":
            return handle_news_command(user_id, openai_api_key)
        elif command_code == "MEDITATION_GUIDE":
            return handle_meditation_command(user_id, openai_api_key)
        elif command_code == "MEDITATION_OPTIONS":
            return handle_meditation_command(user_id, openai_api_key, "列表")
        elif command_code == "NEWS_TW_POLITICS":
            return handle_news_command(user_id, openai_api_key, "台灣政治新聞")
        elif command_code == "NEWS_INTL_ECONOMICS":
            return handle_news_command(user_id, openai_api_key, "國際經濟新聞")
        elif command_code == "NEWS_CULTURE":
            return handle_news_command(user_id, openai_api_key, "文化新聞")
    
    return "未識別的命令。請嘗試其他選項。"

# 擴展功能可以在這裡添加新的功能塊
# 例如:
"""
def get_buddhist_holiday_info():
    # 獲取佛教節日信息
    pass

def get_daily_sutra():
    # 獲取每日經文
    pass
""" 