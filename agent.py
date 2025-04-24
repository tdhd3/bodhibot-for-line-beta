from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from cbeta_tool import CBETASearcher
import os

# 載入 CBETA 工具
cbeta_searcher = CBETASearcher()

def cbeta_tool_func(query: str) -> str:
    results = cbeta_searcher.search(query, return_full_paragraph=True)
    if not results:
        return "未找到相關經文。"
    
    formatted_results = []
    for doc in results:
        # 原文完整段落
        full_paragraph = doc['content']
        # 引用信息
        reference = cbeta_searcher.format_cbeta_reference(doc)
        formatted_results.append(f"【原文】\n{full_paragraph}\n\n【來源】\n{reference}")
    
    return "\n\n---\n\n".join(formatted_results)

cbeta_tool = Tool(
    name="CBETA經文檢索",
    func=cbeta_tool_func,
    description="根據用戶問題檢索CBETA佛教經典，返回經文與標準引用。"
)

# System Prompt
SYSTEM_PROMPT = """
你是「菩薩小老師」，一位融合佛教唯識學與菩薩道智慧的慈悲導師。你的目標是協助使用者透過觀照習氣、認識因果、發菩提心，逐步建立出離心、悲願心，進而實踐佛法於生活中。並基於用戶的需求使用工具來回答問題和執行任務。
--
History:
{history}
CBETA DATA:
{cbeta_context}
--
引用經典原則：
1. 引用經典時，必須以完整段落呈現，不可斷章取義或片段裁剪
2. 引用時必須標明經典出處
3. 不可改變經文原意或用自己的話重新詮釋經文

請根據以下的內容使用以下原則與任務進行回應與引導：
（這裡可插入你給的所有規則與結構）
"""

def get_agent(openai_api_key: str, user_id: str):
    memory = ConversationBufferMemory(memory_key="history", return_messages=True)
    llm = ChatOpenAI(temperature=0.3, openai_api_key=openai_api_key)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
    ])
    agent = initialize_agent(
        tools=[cbeta_tool],
        llm=llm,
        agent="chat-conversational-react-description",
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={"system_message": SYSTEM_PROMPT}
    )
    return agent
