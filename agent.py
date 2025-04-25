import os
import json
import logging
import sys
import time
import traceback
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.tools import BaseTool, Tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from cbeta_tool import CBETASearcher
from cbeta_retrieval import CBETARetriever
from user_context import get_user_context, get_recent_messages_for_context

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("agent")

# 載入 CBETA 工具
cbeta_searcher = CBETASearcher()

# 用户聊天历史
user_memories = {}

def cbeta_tool_func(query: str) -> str:
    try:
        logger.info(f"CBETA搜索: {query}")
        results = cbeta_searcher.search(query, return_full_paragraph=True)
        if not results:
            logger.info("CBETA搜索: 未找到相關經文")
            return "未找到相關經文。"
        
        formatted_results = []
        for doc in results:
            # 原文完整段落
            full_paragraph = doc['content']
            # 引用信息
            reference = cbeta_searcher.format_cbeta_reference(doc)
            formatted_results.append(f"【原文】\n{full_paragraph}\n\n【來源】\n{reference}")
        
        logger.info(f"CBETA搜索: 找到 {len(results)} 條結果")
        return "\n\n---\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"CBETA搜索錯誤: {str(e)}", exc_info=True)
        return f"檢索經文時發生錯誤: {str(e)}"

cbeta_tool = Tool(
    name="CBETA經文檢索",
    func=cbeta_tool_func,
    description="根據用戶問題檢索CBETA佛教經典，返回經文與標準引用。"
)

def get_agent(openai_api_key: str, user_id: Optional[str] = None):
    """创建一个配置好的LangChain代理，使用CBETA工具"""
    # 系统提示词基本模板
    system_message_template = """你是"菩薩小老師"，一位博学的佛法顧問，遵循以下原則：

1. 清晰易懂：用簡單的現代語言解釋佛法概念，避免晦澀的專業術語。
2. 慈悲為懷：以平等之心對待所有問題，不帶評判。
3. 實用建議：提供具體、可行的建議，而非抽象理論。
4. 歷史準確：確保所有引用的經文和歷史信息準確無誤。
5. 避免宣揚迷信：不傳播未經證實的迷信或神秘說法。
6. 使用台灣繁體中文：所有回覆必須使用台灣繁體中文，包括詞彙選擇和表達方式都要符合台灣用語習慣。

你的回應應該簡潔明瞭、貼近生活實際，並在適當時引用經典原文佐證。避免使用過於學術化的語言，確保一般大眾能夠理解。

你可以使用CBETA工具來查詢佛教經典中的內容，幫助提供更準確的回答。
"""

    # 添加用户上下文（如果有用户ID）
    if user_id:
        user_context = get_user_context(user_id)
        if user_context:
            # 格式化上下文信息
            context_info = f"""
用户信息：
- 修行经验：{user_context.get('practice_history', '未知')}
- 兴趣领域：{', '.join(user_context.get('interests', ['一般佛法']))}
- 提及过的主题：{', '.join(user_context.get('mentions', []))}

最近对话历史：
{get_recent_messages_for_context(user_id)}
"""
            system_message_template += context_info

    # 初始化语言模型
    llm = ChatOpenAI(
        model="gpt-4-turbo", 
        temperature=0.7,
        openai_api_key=openai_api_key
    )
    
    # 初始化CBETA检索工具
    cbeta_retriever = CBETARetriever()
    tools = [cbeta_retriever]
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message_template),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}")
    ])
    
    # 创建代理
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # 创建代理执行器
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        # 禁用内存组件，我们将手动管理聊天历史
        handle_parsing_errors=True
    )
    
    # 包装函数，处理聊天历史
    def agent_with_chat_history(user_input, chat_history=None):
        try:
            # 准备输入
            inputs = {"input": user_input}
            
            # 如果有聊天历史，添加到输入
            if chat_history:
                inputs["chat_history"] = chat_history
                
            # 执行代理
            result = agent_executor.invoke(inputs)
            return result.get("output", "我现在无法回答，请稍后再试。")
        except Exception as e:
            logger.error(f"Agent执行错误: {e}", exc_info=True)
            return "抱歉，我目前遇到了一些技术问题。请稍后再试。"
    
    return agent_with_chat_history
