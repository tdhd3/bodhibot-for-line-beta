import random
from typing import Dict, Optional, List
from agent import get_agent

# 六妙門原文出處
SIX_WONDERFUL_GATES_SOURCE = "《六妙法門》為天台宗智者大師所著，提出了數息、隨息、止、觀、還、淨六種修行方法。"

# 六妙門基本修行方法
SIX_GATES = {
    "數息": {
        "description": "專注於呼吸的數數，從一到十，再從一開始，是攝心的基本方法。",
        "instructions": [
            "端身正坐，放鬆身心",
            "自然呼吸，不要刻意控制",
            "吸氣呼氣為一息，心中默數「一」",
            "再一次吸氣呼氣，心中默數「二」",
            "如此繼續到「十」，然後再從「一」開始",
            "如果數錯或忘記數到幾，就從「一」重新開始",
            "保持正念，不要被妄想所轉"
        ],
        "quote": "息有四相：風相、喘相、氣相、息相。息相為微，從麤至細，攝心調息。",
        "level": "初學者",
        "benefits": "安定心神，減少妄想，為後續修行打下基礎"
    },
    "隨息": {
        "description": "不數數，只是單純地覺知呼吸，隨著呼吸的出入，讓心安住在呼吸上。",
        "instructions": [
            "在數息練習有了基礎後進行",
            "放下數數，只是單純地覺知每一次呼吸",
            "覺察呼吸的整個過程：入、住、出",
            "呼吸進入時，知道呼吸進入",
            "呼吸呼出時，知道呼吸呼出",
            "不要控制呼吸，只是觀察它",
            "心隨著呼吸，如水中的倒影隨波而動"
        ],
        "quote": "隨息者，捨數息之法，一心依隨息之出入，攝心緣息，知息入知息出，心住息緣，無分散意。",
        "level": "初中級",
        "benefits": "增長定力，培養覺知，減少散亂"
    },
    "止": {
        "description": "安止其心於一處，不隨外境所轉，達到心的寧靜與專注。",
        "instructions": [
            "基於隨息，進一步安住其心",
            "專注於鼻端或腹部等一處",
            "心若散亂，溫和地將注意力帶回",
            "保持清醒與警覺，避免昏沉",
            "感受呼吸帶來的平靜與安定",
            "不分析不評判，只是安住",
            "逐漸延長定心的時間"
        ],
        "quote": "止者，並息諸緣，不念數隨，凝靜其心，止於息境。",
        "level": "中級",
        "benefits": "止息煩惱，安住現在，為觀慧打下基礎"
    },
    "觀": {
        "description": "觀察呼吸及其引起的身心變化，透視諸法實相。",
        "instructions": [
            "在止的基礎上發展觀慧",
            "觀察呼吸的無常變化",
            "覺察呼吸與身體的關係",
            "觀察念頭如何生起又消失",
            "了知呼吸、身體與心識的空性本質",
            "不執著於任何境界或體驗",
            "保持覺知而不分析或概念化"
        ],
        "quote": "觀者，分別推析，觀察息性，悟其實相。息從何來？息從何去？誰有此息？息屬於誰？推之了不可得，入實相智慧。",
        "level": "中高級",
        "benefits": "開發智慧，破除我執，體悟無常、苦、空、無我"
    },
    "還": {
        "description": "返觀自心，心返照心，了知心的本性。",
        "instructions": [
            "從觀外境轉而觀照能觀之心",
            "覺察心念如何生起、住留、消失",
            "了知能觀之心與所觀之境不二",
            "返觀「誰在觀察」，追尋心的來源",
            "不被任何境界所轉",
            "安住於純粹的覺知",
            "體會心的本性"
        ],
        "quote": "還者，轉心返照，反觀自心。若觀息長短，誰為能知？推尋能所，知息者誰也？",
        "level": "高級",
        "benefits": "破除能所對立，返歸心源，體悟本性"
    },
    "淨": {
        "description": "心得清淨，無有染著，達到究竟解脫。",
        "instructions": [
            "安住於清淨無雜的覺知中",
            "不執著於任何境界或體驗",
            "捨離一切分別妄想",
            "不住在「淨」上，連「淨」的概念也不執著",
            "超越所有對立與概念",
            "任運自在，隨緣不變",
            "體悟心的本來面目"
        ],
        "quote": "淨者，若能反觀能觀之心，則能所俱忘，心無所依，妄想不生，心源清淨。",
        "level": "最高級",
        "benefits": "究竟解脫，清淨無染，證悟菩提"
    }
}

# 不同修行階段的用戶
USER_LEVELS = {
    "beginner": ["數息", "隨息"],
    "intermediate": ["數息", "隨息", "止"],
    "advanced": ["隨息", "止", "觀"],
    "very_advanced": ["止", "觀", "還"],
    "master": ["觀", "還", "淨"]
}

def determine_user_level(user_context: Dict = None) -> str:
    """根據用戶上下文確定修行級別"""
    if not user_context:
        return "beginner"
    
    # 從用戶上下文中獲取線索
    mentions = user_context.get('mentions', [])
    questions = user_context.get('questions', [])
    practice_history = user_context.get('practice_history', '')
    
    # 檢查高級修行概念的提及
    advanced_concepts = ["無我", "空性", "實相", "涅槃", "般若", "中道", "如來藏"]
    intermediate_concepts = ["止觀", "定慧", "禪定", "三學", "七覺支", "八正道"]
    
    # 計算提及高級概念的數量
    advanced_count = sum(1 for concept in advanced_concepts if any(concept in m for m in mentions))
    intermediate_count = sum(1 for concept in intermediate_concepts if any(concept in m for m in mentions))
    
    # 檢查實踐歷史中的關鍵詞
    years_match = None
    import re
    if practice_history:
        years_pattern = re.compile(r'(\d+)\s*年')
        years_match = years_pattern.search(practice_history)
    
    practice_years = 0
    if years_match:
        try:
            practice_years = int(years_match.group(1))
        except:
            pass
    
    # 基於各種因素確定級別
    if practice_years > 10 or advanced_count >= 3:
        return "master"
    elif practice_years > 5 or advanced_count >= 1 or intermediate_count >= 3:
        return "very_advanced"
    elif practice_years > 2 or intermediate_count >= 1:
        return "advanced"
    elif practice_years > 0:
        return "intermediate"
    else:
        return "beginner"

def get_suitable_practices(user_level: str) -> List[str]:
    """獲取適合用戶級別的修行方法"""
    return USER_LEVELS.get(user_level, USER_LEVELS["beginner"])

def generate_meditation_guide(user_id: str, openai_api_key: str, user_context: Dict = None, specific_gate: str = None) -> str:
    """生成禪修引導"""
    # 確定用戶級別
    user_level = determine_user_level(user_context)
    
    # 選擇適合的修行方法
    suitable_practices = get_suitable_practices(user_level)
    
    # 如果指定了特定的修行方法
    if specific_gate and specific_gate in SIX_GATES:
        selected_gate = specific_gate
    else:
        # 從適合的方法中隨機選擇一個
        selected_gate = random.choice(suitable_practices)
    
    practice_info = SIX_GATES[selected_gate]
    
    # 基本引導內容
    basic_guide = (f"【{selected_gate}禪修引導】\n\n"
                   f"{practice_info['description']}\n\n"
                   f"修行方法：\n" + 
                   "\n".join([f"{i+1}. {step}" for i, step in enumerate(practice_info['instructions'])]) +
                   f"\n\n引自六妙門：「{practice_info['quote']}」")
    
    # 如果有 API 密鑰，使用 AI 生成個性化引導
    if openai_api_key:
        try:
            agent = get_agent(openai_api_key, 'meditation_guide')
            
            # 準備用戶背景信息
            user_background = ""
            if user_context:
                if 'background' in user_context:
                    user_background += f"\n用戶背景: {user_context['background']}"
                if 'practice_history' in user_context:
                    user_background += f"\n修行經驗: {user_context['practice_history']}"
                if 'questions' in user_context:
                    recent_questions = user_context['questions'][-3:] if len(user_context['questions']) > 0 else []
                    if recent_questions:
                        user_background += f"\n最近提問: {', '.join(recent_questions)}"
            
            # 生成個性化引導
            prompt = (f"請根據六妙門中的「{selected_gate}」法門，為用戶創建一個個性化的禪修引導。\n\n"
                      f"六妙門原文描述：{practice_info['quote']}\n"
                      f"修行目的：{practice_info['benefits']}\n"
                      f"用戶水平：{user_level}{user_background}\n\n"
                      f"請提供：\n"
                      f"1. 簡短的理論背景\n"
                      f"2. 詳細的步驟指導\n"
                      f"3. 可能遇到的困難和解決方法\n"
                      f"4. 一個相關的佛教故事或經文引用\n"
                      f"5. 如何將此修行融入日常生活\n\n"
                      f"整體內容簡潔明了，易於理解和實踐。")
            
            personalized_guide = agent.run(prompt)
            return f"【{selected_gate}禪修引導】\n\n{personalized_guide}\n\n參考出處：{SIX_WONDERFUL_GATES_SOURCE}"
        except Exception as e:
            print(f"生成個性化禪修引導失敗: {e}")
            # 如果 AI 生成失敗，返回基本引導
            return basic_guide
    
    return basic_guide

def list_meditation_options() -> str:
    """列出所有禪修選項"""
    options = ["六妙門禪修法門："]
    
    for gate, info in SIX_GATES.items():
        options.append(f"【{gate}】- {info['description'][:30]}... (適合{info['level']})")
    
    options.append("\n請輸入「禪修指導：數息」等命令來獲取特定引導。")
    
    return "\n\n".join(options)

def handle_meditation_command(user_id: str, openai_api_key: str, command: str = None, user_context: Dict = None) -> str:
    """處理禪修相關的用戶命令"""
    # 檢查是否請求列出所有選項
    if command and ("列表" in command or "選項" in command or "所有" in command):
        return list_meditation_options()
    
    # 檢查是否請求特定的禪修方法
    specific_gate = None
    for gate in SIX_GATES.keys():
        if command and gate in command:
            specific_gate = gate
            break
    
    # 生成禪修引導
    return generate_meditation_guide(user_id, openai_api_key, user_context, specific_gate) 