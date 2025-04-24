import os
import json
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict

# 用戶上下文數據結構
USER_CONTEXT_TEMPLATE = {
    "user_id": "",
    "created_at": 0,
    "last_updated": 0,
    "background": "",
    "practice_history": "",
    "interests": [],
    "questions": [],
    "mentions": [],
    "interactions_count": 0,
    "preferred_gates": []
}

# 內存中的用戶上下文緩存
user_contexts = {}

# 用戶上下文持久化路徑
USER_CONTEXT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'user_contexts')

# 確保目錄存在
os.makedirs(USER_CONTEXT_DIR, exist_ok=True)

def get_user_context(user_id: str) -> Dict:
    """獲取用戶上下文，如果不存在則創建新的"""
    global user_contexts
    
    # 檢查內存緩存
    if user_id in user_contexts:
        return user_contexts[user_id]
    
    # 嘗試從文件加載
    context_path = os.path.join(USER_CONTEXT_DIR, f"{user_id}.json")
    if os.path.exists(context_path):
        try:
            with open(context_path, 'r', encoding='utf-8') as f:
                context = json.load(f)
                user_contexts[user_id] = context
                return context
        except Exception as e:
            print(f"加載用戶上下文失敗: {e}")
    
    # 創建新的上下文
    now = int(time.time())
    new_context = USER_CONTEXT_TEMPLATE.copy()
    new_context.update({
        "user_id": user_id,
        "created_at": now,
        "last_updated": now
    })
    
    user_contexts[user_id] = new_context
    save_user_context(user_id)
    return new_context

def save_user_context(user_id: str) -> bool:
    """將用戶上下文保存到文件"""
    if user_id not in user_contexts:
        return False
    
    context_path = os.path.join(USER_CONTEXT_DIR, f"{user_id}.json")
    try:
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(user_contexts[user_id], f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存用戶上下文失敗: {e}")
        return False

def update_user_context(user_id: str, updates: Dict) -> Dict:
    """更新用戶上下文"""
    context = get_user_context(user_id)
    
    # 更新基本字段
    for key, value in updates.items():
        if key in context:
            context[key] = value
    
    # 更新時間戳
    context["last_updated"] = int(time.time())
    
    # 增加互動計數
    context["interactions_count"] += 1
    
    # 保存更新
    save_user_context(user_id)
    
    return context

def add_user_question(user_id: str, question: str) -> Dict:
    """添加用戶問題到上下文"""
    context = get_user_context(user_id)
    
    # 添加到問題列表
    if "questions" not in context:
        context["questions"] = []
    
    context["questions"].append(question)
    
    # 保留最近的20個問題
    if len(context["questions"]) > 20:
        context["questions"] = context["questions"][-20:]
    
    # 分析問題中的關鍵詞
    extract_mentions_from_text(user_id, question)
    
    # 更新時間戳
    context["last_updated"] = int(time.time())
    
    # 保存更新
    save_user_context(user_id)
    
    return context

def extract_mentions_from_text(user_id: str, text: str) -> List[str]:
    """從文本中提取提及的關鍵詞"""
    context = get_user_context(user_id)
    
    # 佛教相關關鍵詞
    buddhist_keywords = [
        "佛陀", "菩薩", "阿羅漢", "四聖諦", "八正道", "中道", "禪修", "冥想",
        "六妙門", "數息", "隨息", "止", "觀", "還", "淨", "無常", "無我",
        "空性", "涅槃", "慈悲", "般若", "菩提", "輪迴", "因果", "緣起"
    ]
    
    # 初始化提及列表
    if "mentions" not in context:
        context["mentions"] = []
    
    # 提取關鍵詞
    found_mentions = []
    for keyword in buddhist_keywords:
        if keyword in text:
            found_mentions.append(keyword)
            if keyword not in context["mentions"]:
                context["mentions"].append(keyword)
    
    # 保留最近的50個提及
    if len(context["mentions"]) > 50:
        context["mentions"] = context["mentions"][-50:]
    
    # 保存更新
    save_user_context(user_id)
    
    return found_mentions

def analyze_practice_history(user_id: str, text: str) -> str:
    """分析並更新用戶的修行歷史"""
    context = get_user_context(user_id)
    
    # 保存原始修行歷史文本
    context["practice_history"] = text
    
    # 提取關鍵詞
    extract_mentions_from_text(user_id, text)
    
    # 分析偏好的修行方法
    preferred_gates = []
    gates = ["數息", "隨息", "止", "觀", "還", "淨"]
    for gate in gates:
        if gate in text:
            preferred_gates.append(gate)
    
    if preferred_gates:
        context["preferred_gates"] = preferred_gates
    
    # 保存更新
    save_user_context(user_id)
    
    return context["practice_history"]

def get_user_interests(user_id: str) -> List[str]:
    """獲取用戶感興趣的主題"""
    context = get_user_context(user_id)
    return context.get("interests", [])

def add_user_interest(user_id: str, interest: str) -> List[str]:
    """添加用戶興趣"""
    context = get_user_context(user_id)
    
    if "interests" not in context:
        context["interests"] = []
    
    if interest not in context["interests"]:
        context["interests"].append(interest)
    
    # 保存更新
    save_user_context(user_id)
    
    return context["interests"]

def get_user_background(user_id: str) -> str:
    """獲取用戶背景信息"""
    context = get_user_context(user_id)
    return context.get("background", "")

def get_preferred_gates(user_id: str) -> List[str]:
    """獲取用戶偏好的修行方法"""
    context = get_user_context(user_id)
    return context.get("preferred_gates", []) 