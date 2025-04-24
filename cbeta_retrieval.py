import os
import logging
import json
import re
from typing import List, Dict, Optional, Union, Tuple, Any
import numpy as np
from tqdm import tqdm
from langchain.tools import BaseTool, Tool
from langchain.tools.base import ToolException
from pydantic import BaseModel, Field

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CBETA 数据目录
CBETA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'cbeta')

class CBETARetriever(BaseTool):
    """用于从CBETA佛教经典数据中检索相关段落的工具，支持高效的语义搜索。"""
    
    name = "CBETA经文检索"
    description = "根据用户问题检索CBETA佛教经典数据库，返回最相关的经文段落与引用信息。"
    
    def __init__(self):
        """初始化CBETA检索工具。"""
        super().__init__()
        # 加载CBETA数据
        self.cbeta_dir = CBETA_DIR
        self.docs = self._load_documents()
        
        # 预处理段落
        self.paragraphs = self._preprocess_paragraphs()
        logger.info(f"已加载 {len(self.paragraphs)} 个经文段落")
        
        # 初始化语义搜索
        self.embeddings = None
        self.model = None
        self.has_embedding = self._setup_embedding_search()
        
        if self.has_embedding:
            logger.info("语义搜索模型加载成功")
        else:
            logger.warning("仅使用关键词搜索")
    
    def _load_documents(self) -> List[Dict]:
        """加载所有CBETA JSON文档。"""
        docs = []
        
        try:
            for filename in os.listdir(self.cbeta_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(self.cbeta_dir, filename), 'r', encoding='utf-8') as f:
                        try:
                            doc = json.load(f)
                            docs.append(doc)
                        except Exception as e:
                            logger.error(f"加载文件 {filename} 时出错: {e}")
            
            logger.info(f"成功加载 {len(docs)} 个CBETA文档")
            return docs
        except Exception as e:
            logger.error(f"加载CBETA文档时出错: {e}")
            return []
    
    def _preprocess_paragraphs(self) -> List[Dict]:
        """将经文分割成段落，方便更精准的检索。"""
        all_paragraphs = []
        
        for doc in self.docs:
            content = doc.get('content', '')
            
            # 分割段落
            paragraphs = self._split_text_to_paragraphs(content)
            
            # 创建段落记录
            for idx, para in enumerate(paragraphs):
                if not para.strip():
                    continue
                
                all_paragraphs.append({
                    'id': f"{doc.get('id', '')}_p{idx}",
                    'doc_id': doc.get('id', ''),
                    'title': doc.get('title', ''),
                    'content': para.strip(),
                    'paragraph_index': idx
                })
        
        return all_paragraphs
    
    def _split_text_to_paragraphs(self, text: str) -> List[str]:
        """智能分割文本为自然段落。"""
        # 首先尝试按照空行分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        # 如果只有一个段落，尝试按照句号等标点符号分割
        if len(paragraphs) <= 1:
            # 以句号、问号或感叹号后跟换行或空格为分隔点
            paragraphs = re.split(r'([。？！][\s\n]+)', text)
            
            # 合并标点与内容
            processed_paragraphs = []
            for i in range(0, len(paragraphs), 2):
                if i+1 < len(paragraphs):
                    processed_paragraphs.append(paragraphs[i] + paragraphs[i+1])
                else:
                    processed_paragraphs.append(paragraphs[i])
            
            paragraphs = processed_paragraphs
        
        # 过滤空段落
        paragraphs = [p for p in paragraphs if p.strip()]
        
        return paragraphs
    
    def _setup_embedding_search(self) -> bool:
        """设置语义搜索功能。"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # 使用多语言模型，支持中文
            model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
            self.model = SentenceTransformer(model_name)
            
            # 为所有段落生成嵌入向量
            logger.info("开始生成段落嵌入向量...")
            
            # 使用批处理生成嵌入向量，提高效率
            contents = [p['content'] for p in self.paragraphs]
            self.embeddings = self.model.encode(
                contents, 
                show_progress_bar=True, 
                batch_size=32, 
                convert_to_numpy=True
            )
            
            logger.info(f"成功生成 {len(self.embeddings)} 个嵌入向量")
            return True
            
        except ImportError as e:
            logger.warning(f"无法导入sentence-transformers: {e}")
            return False
        except Exception as e:
            logger.error(f"设置嵌入搜索时出错: {e}")
            return False
    
    def search_by_embedding(self, query: str, top_k: int = 5) -> List[Dict]:
        """使用语义搜索查找与查询最相关的段落。"""
        # 生成查询的嵌入向量
        query_embedding = self.model.encode([query])[0]
        
        # 计算查询与所有段落的余弦相似度
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # 获取相似度最高的前 top_k 个段落
        top_indices = np.argsort(-similarities)[:top_k]
        
        # 返回结果，并添加相似度分数
        results = []
        for i in top_indices:
            para = self.paragraphs[i].copy()
            para['similarity'] = float(similarities[i])
            results.append(para)
        
        return results
    
    def search_by_keywords(self, query: str, top_k: int = 5) -> List[Dict]:
        """使用关键词搜索查找包含查询词的段落。"""
        results = []
        
        # 分词
        query_words = query.split()
        
        # 完全匹配搜索
        for para in self.paragraphs:
            if query in para['content']:
                para_copy = para.copy()
                para_copy['match_type'] = 'full'
                results.append(para_copy)
        
        # 如果完全匹配结果太少，添加部分匹配
        if len(results) < top_k:
            for para in self.paragraphs:
                # 避免重复添加
                if any(para['id'] == r['id'] for r in results):
                    continue
                
                # 检查是否有足够的查询词匹配
                matched_words = sum(1 for word in query_words if word in para['content'])
                if matched_words >= max(1, len(query_words) // 2):
                    para_copy = para.copy()
                    para_copy['match_type'] = 'partial'
                    para_copy['matched_words'] = matched_words
                    results.append(para_copy)
                    
                    if len(results) >= top_k:
                        break
        
        # 按匹配类型和匹配词数排序
        results.sort(key=lambda x: (
            0 if x.get('match_type') == 'full' else 1,
            -x.get('matched_words', 0)
        ))
        
        return results[:top_k]
    
    def _run(self, query: str) -> str:
        """执行工具，返回检索结果。"""
        try:
            # 设置检索参数
            top_k = 3  # 返回的最相关结果数量
            
            # 根据可用的搜索方法进行检索
            if self.has_embedding:
                results = self.search_by_embedding(query, top_k)
                search_method = "语义搜索"
            else:
                results = self.search_by_keywords(query, top_k)
                search_method = "关键词搜索"
            
            # 如果没有找到结果
            if not results:
                return "未找到相关经文。请尝试使用不同的关键词或更通用的描述。"
            
            # 格式化结果
            formatted_results = []
            for i, result in enumerate(results):
                # 获取完整段落内容
                content = result['content']
                
                # 生成标准引用
                reference = self.format_reference(result)
                
                # 添加格式化后的结果
                formatted_results.append(
                    f"【经文 {i+1}】\n{content}\n\n【出处】\n{reference}"
                )
            
            # 组合所有结果
            combined_result = "\n\n---\n\n".join(formatted_results)
            return combined_result
            
        except Exception as e:
            logger.error(f"执行CBETA检索时发生错误: {e}", exc_info=True)
            raise ToolException(f"检索经文时出错: {str(e)}")
    
    def format_reference(self, doc: Dict) -> str:
        """生成标准的CBETA引用格式。"""
        doc_id = doc.get('doc_id', doc.get('id', ''))
        title = doc.get('title', '')
        
        # 如果标题为空，查找原始文档获取
        if not title and doc_id:
            for original_doc in self.docs:
                if original_doc.get('id', '') == doc_id:
                    title = original_doc.get('title', '')
                    break
        
        # 生成CBETA在线链接
        url = f'https://cbetaonline.dila.edu.tw/zh/{doc_id}'
        
        # 格式化引用
        reference = f"{title}（CBETA编号：{doc_id}）\n{url}"
        return reference

# 测试代码
if __name__ == "__main__":
    retriever = CBETARetriever()
    query = "佛陀如何解释苦的本质"
    result = retriever._run(query)
    print(result)
