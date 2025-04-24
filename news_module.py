import os
import requests
import feedparser
import json
from datetime import datetime
from typing import List, Dict, Optional, Union
from agent import get_agent

# 只保留GNews API
GNEWS_API_URL = "https://gnews.io/api/v4/top-headlines"
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')

# 台灣主要新聞源的RSS訂閱
TAIWAN_RSS_FEEDS = {
    "politics": [
        {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/politics.xml"},
        {"name": "中央社", "url": "https://www.cna.com.tw/RSS/Politics.aspx"},
        {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/6638?ch=news"}
    ],
    "economics": [
        {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/business.xml"},
        {"name": "中央社", "url": "https://www.cna.com.tw/RSS/Economy.aspx"},
        {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/6644?ch=news"}
    ],
    "international": [
        {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/world.xml"},
        {"name": "中央社", "url": "https://www.cna.com.tw/RSS/International.aspx"},
        {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/7225?ch=news"}
    ],
    "culture": [
        {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/culture.xml"},
        {"name": "中央社", "url": "https://www.cna.com.tw/RSS/Culture.aspx"},
        {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/6649?ch=news"}
    ],
    "taiwan": [
        {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/local.xml"},
        {"name": "中央社", "url": "https://www.cna.com.tw/RSS/Local.aspx"},
        {"name": "聯合新聞網", "url": "https://udn.com/rssfeed/news/2/6641?ch=news"}
    ]
}

# 可靠的台灣新聞源列表
TAIWAN_NEWS_SOURCES = [
    "ltn.com.tw",        # 自由時報
    "udn.com",           # 聯合報
    "cna.com.tw",        # 中央社
    "taiwannews.com.tw", # 台灣英文新聞
    "taipeitimes.com"    # 台北時報
]

# 新聞類別
NEWS_CATEGORIES = {
    "politics": "政治",
    "economics": "經濟",
    "culture": "文化",
    "international": "國際",
    "taiwan": "台灣"
}

# 新聞源圖標映射
NEWS_SOURCE_ICONS = {
    "自由時報": "https://www.ltn.com.tw/assets/images/logo.png",
    "中央社": "https://www.cna.com.tw/project/20161116-civil/img/logo.png",
    "聯合新聞網": "https://udn.com/static/img/logo-mobile.svg"
}

# 新聞分類圖標映射
NEWS_CATEGORY_ICONS = {
    "politics": "https://cdn-icons-png.flaticon.com/512/3759/3759933.png",
    "economics": "https://cdn-icons-png.flaticon.com/512/2529/2529518.png",
    "culture": "https://cdn-icons-png.flaticon.com/512/3100/3100063.png",
    "international": "https://cdn-icons-png.flaticon.com/512/3113/3113416.png",
    "taiwan": "https://cdn-icons-png.flaticon.com/512/164/164877.png"
}

def get_news_by_rss(category: str = None, count: int = 10) -> List[Dict]:
    """使用台灣新聞源的RSS獲取最新新聞"""
    articles = []
    
    # 確定要獲取的類別
    feeds_to_fetch = []
    if category and category.lower() in TAIWAN_RSS_FEEDS:
        feeds_to_fetch = TAIWAN_RSS_FEEDS[category.lower()]
    else:
        # 如果沒指定類別或類別不存在，從所有類別中各取一個源
        for cat in TAIWAN_RSS_FEEDS:
            if TAIWAN_RSS_FEEDS[cat]:
                feeds_to_fetch.append(TAIWAN_RSS_FEEDS[cat][0])
    
    # 從選定的RSS源獲取新聞
    for feed_info in feeds_to_fetch:
        try:
            feed = feedparser.parse(feed_info["url"])
            source_name = feed_info["name"]
            
            for entry in feed.entries[:5]:  # 每個源取5條
                # 檢查是否有必要欄位
                if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                    continue
                
                # 提取發布時間
                published_at = ""
                if hasattr(entry, 'published'):
                    published_at = entry.published
                elif hasattr(entry, 'pubDate'):
                    published_at = entry.pubDate
                
                # 提取描述
                description = ""
                if hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'summary'):
                    description = entry.summary
                
                # 去除HTML標籤
                import re
                description = re.sub(r'<.*?>', '', description)
                
                # 嘗試獲取封面圖片
                image_url = None
                if hasattr(entry, 'media_content'):
                    for media in entry.media_content:
                        if 'url' in media:
                            image_url = media['url']
                            break
                
                # 添加到文章列表
                articles.append({
                    'title': entry.title,
                    'url': entry.link,
                    'description': description,
                    'source': source_name,
                    'domain': extract_domain(entry.link),
                    'publishedAt': published_at,
                    'image': image_url
                })
                
                # 如果已經達到需要的數量，提前返回
                if len(articles) >= count:
                    return articles
                
        except Exception as e:
            print(f"從RSS源獲取新聞失敗 ({feed_info['name']}): {e}")
    
    return articles

def get_news_by_gnews(category: str = None, country: str = 'tw', count: int = 10) -> List[Dict]:
    """使用 GNews API 獲取最新新聞"""
    try:
        params = {
            'token': GNEWS_API_KEY,
            'max': count,
            'lang': 'zh-tw',
        }
        
        # 根據分類調整請求參數
        if category:
            params['topic'] = category.lower()
            
        # 決定國際或台灣新聞
        if country and country.lower() in ['tw', 'taiwan']:
            params['country'] = 'tw'
            
        response = requests.get(
            GNEWS_API_URL,
            params=params
        )
        
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            # 轉換為標準格式
            return [{
                'title': a.get('title', ''),
                'url': a.get('url', ''),
                'description': a.get('description', ''),
                'source': a.get('source', {}).get('name', ''),
                'publishedAt': a.get('publishedAt', '')
            } for a in articles]
        return []
    except Exception as e:
        print(f"獲取新聞失敗 (GNews): {e}")
        return []

def filter_news_articles(articles: List[Dict]) -> List[Dict]:
    """過濾和清理新聞文章"""
    filtered_articles = []
    
    for article in articles:
        # 過濾無效的文章
        if not article.get('title') or not article.get('url'):
            continue
            
        # 過濾重複的標題
        if any(a.get('title') == article.get('title') for a in filtered_articles):
            continue
            
        # 確保來源可靠
        source_name = article.get('source', {}).get('name', '')
        source_domain = extract_domain(article.get('url', ''))
        
        filtered_articles.append({
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'description': article.get('description', ''),
            'source': source_name,
            'domain': source_domain,
            'publishedAt': article.get('publishedAt', '')
        })
    
    return filtered_articles

def extract_domain(url: str) -> str:
    """從 URL 提取域名"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return ""

def get_news_options(category: str = None, country: str = None) -> List[Dict]:
    """獲取新聞選項供用戶選擇"""
    # 首先嘗試從RSS源獲取新聞
    articles = get_news_by_rss(category)
    
    # 如果RSS源獲取失敗或數量不足，嘗試 GNews
    if len(articles) < 3:
        gnews_articles = get_news_by_gnews(category, country)
        # 合併並去重
        seen_titles = {a.get('title') for a in articles}
        for article in gnews_articles:
            if article.get('title') not in seen_titles:
                articles.append(article)
                seen_titles.add(article.get('title'))
    
    # 僅返回前10項作為選項
    return articles[:10]

def generate_buddhist_reflection(news_article: Dict, openai_api_key: str, user_context: Dict = None) -> str:
    """根據佛教觀點生成對新聞的分析和反思"""
    if not news_article or not openai_api_key:
        return "無法生成分析，缺少新聞資料或API密鑰。"
    
    title = news_article.get('title', '')
    url = news_article.get('url', '')
    description = news_article.get('description', '')
    source = news_article.get('source', '')
    
    # 獲取用戶背景信息
    user_background = ""
    if user_context and 'background' in user_context:
        user_background = f"\n考慮以下用戶背景: {user_context['background']}"
    
    # 使用 agent 生成佛教反思
    agent = get_agent(openai_api_key, 'news_reflection')
    
    prompt = (f"請基於佛教智慧，特別是因果、無常、緣起等觀點，分析以下新聞：\n\n"
              f"標題：{title}\n"
              f"內容摘要：{description}\n"
              f"來源：{source}\n"
              f"{user_background}\n\n"
              f"請提供：\n"
              f"1. 從佛法角度看這則新聞反映的現象\n"
              f"2. 這個事件如何體現佛教中的因果、無常或緣起法則\n"
              f"3. 如何將這個新聞中的啟示應用到日常修行中\n"
              f"4. 一個相關的佛經教導或故事（如有）")
    
    try:
        reflection = agent.run(prompt)
    except Exception as e:
        reflection = f"無法生成反思：{e}"
    
    # 格式化輸出
    formatted_reflection = (f"📰 **{title}**\n"
                           f"🔗 {url}\n\n"
                           f"🙏 **佛教省思**:\n{reflection}")
    
    return formatted_reflection

def create_news_flex_message(article: Dict) -> Dict:
    """為單個新聞創建Flex消息"""
    title = article.get('title', '')
    url = article.get('url', '')
    description = article.get('description', '')
    source = article.get('source', '')
    image = article.get('image')
    
    # 獲取新聞源圖標
    source_icon = NEWS_SOURCE_ICONS.get(source, "https://cdn-icons-png.flaticon.com/512/2965/2965879.png")
    
    # 處理描述，限制長度
    if description and len(description) > 100:
        description = description[:97] + "..."
    
    # 創建Flex消息
    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": image if image else "https://cdn-icons-png.flaticon.com/512/2965/2965879.png",
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "md",
                    "wrap": True,
                    "maxLines": 2
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "icon",
                            "url": source_icon,
                            "size": "xs"
                        },
                        {
                            "type": "text",
                            "text": source,
                            "size": "xs",
                            "color": "#8c8c8c",
                            "margin": "md"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": description if description else "點擊查看詳情",
                    "size": "xs",
                    "color": "#8c8c8c",
                    "wrap": True,
                    "margin": "md",
                    "maxLines": 3
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "查看新聞",
                        "uri": url
                    },
                    "style": "primary",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "佛教反思",
                        "text": f"請提供新聞佛教反思：{title}"
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm"
                }
            ]
        }
    }
    
    return flex_message

def create_news_carousel(articles: List[Dict]) -> Dict:
    """創建新聞輪播Flex消息"""
    if not articles:
        return None
    
    bubbles = []
    
    # 最多顯示10個項目
    for article in articles[:10]:
        bubble = create_news_flex_message(article)
        bubbles.append(bubble)
    
    carousel = {
        "type": "carousel",
        "contents": bubbles
    }
    
    return carousel

def format_news_selection_flex(articles: List[Dict]) -> Dict:
    """使用Flex消息格式化新聞選項供用戶選擇"""
    if not articles:
        return {
            "type": "text",
            "text": "抱歉，目前沒有找到相關新聞。"
        }
    
    return create_news_carousel(articles)

def handle_news_command(user_id: str, openai_api_key: str, command: str = None, selection: str = None, user_context: Dict = None) -> Union[str, Dict]:
    """處理新聞相關的用戶命令，返回文字或Flex消息"""
    # 解析命令以獲取類別和地區
    category = None
    country = None
    
    if command:
        if "政治" in command:
            category = "politics"
        elif "經濟" in command:
            category = "economics"
        elif "文化" in command:
            category = "culture"
            
        if "國際" in command:
            country = "international"
        elif "台灣" in command:
            country = "taiwan"
    
    # 如果用戶提供了選擇
    if selection and selection.isdigit():
        selection_idx = int(selection) - 1
        
        # 獲取新聞選項
        articles = get_news_options(category, country)
        
        if 0 <= selection_idx < len(articles):
            selected_article = articles[selection_idx]
            return generate_buddhist_reflection(selected_article, openai_api_key, user_context)
        else:
            return "選擇無效，請提供有效的選項編號。"
    
    # 特殊處理：如果命令中包含特定新聞標題，找到這個新聞並生成反思
    if command and command.startswith("請提供新聞佛教反思："):
        title = command.replace("請提供新聞佛教反思：", "").strip()
        articles = get_news_options(category, country)
        for article in articles:
            if article.get('title') == title:
                return generate_buddhist_reflection(article, openai_api_key, user_context)
        return "找不到指定的新聞，請重新選擇。"
    
    # 如果用戶沒有提供選擇，返回新聞選項
    articles = get_news_options(category, country)
    
    # 返回Flex消息
    return format_news_selection_flex(articles) 