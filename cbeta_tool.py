import os
import json
import re
from typing import List, Dict, Optional

CBETA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'cbeta')

class CBETASearcher:
    def __init__(self, cbeta_dir: str = CBETA_DIR):
        self.cbeta_dir = cbeta_dir
        self.docs = self._load_all_jsons()
        # 預處理文檔分段
        self.paragraphs = self._preprocess_paragraphs()
        # 嘗試設置 embedding 搜索
        self.has_embedding = False
        try:
            self.has_embedding = self.setup_embedding_search()
        except Exception as e:
            print(f"無法設置 embedding 搜索: {e}")
            print("將使用關鍵詞搜索作為備選")

    def _load_all_jsons(self) -> List[Dict]:
        docs = []
        for fname in os.listdir(self.cbeta_dir):
            if fname.endswith('.json'):
                with open(os.path.join(self.cbeta_dir, fname), 'r', encoding='utf-8') as f:
                    try:
                        doc = json.load(f)
                        docs.append(doc)
                    except Exception as e:
                        print(f"Error loading {fname}: {e}")
        return docs

    def _preprocess_paragraphs(self) -> List[Dict]:
        """將經文預處理為段落列表"""
        all_paragraphs = []
        for doc in self.docs:
            # 按自然段落分割內容
            content = doc.get('content', '')
            para_splits = self._split_to_paragraphs(content)
            
            for i, para in enumerate(para_splits):
                if not para.strip():
                    continue
                all_paragraphs.append({
                    'id': f"{doc.get('id', '')}_p{i}",
                    'doc_id': doc.get('id', ''),
                    'title': doc.get('title', ''),
                    'content': para.strip(),
                    'paragraph_index': i
                })
        return all_paragraphs
    
    def _split_to_paragraphs(self, text: str) -> List[str]:
        """將長文本分割為自然段落"""
        # 可以根據排版特點分段，這裡使用空行或特定標點作為分隔
        # 初步實現可以用兩個換行符分割
        paragraphs = re.split(r'\n\s*\n', text)
        # 對於沒有明確分段的，可以嘗試按句號等標點分段
        if len(paragraphs) <= 1:
            paragraphs = re.split(r'。(?:\s*\n|$)', text)
            # 將句號添加回句子末尾
            paragraphs = [p + '。' if not p.endswith('。') and i < len(paragraphs)-1 else p for i, p in enumerate(paragraphs)]
        
        # 過濾空段落
        paragraphs = [p for p in paragraphs if p.strip()]
        
        return paragraphs

    def setup_embedding_search(self) -> bool:
        """設置 embedding 檢索"""
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
            
            # 載入預訓練中文模型
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            # 為所有段落生成 embeddings
            contents = [p['content'] for p in self.paragraphs]
            self.embeddings = self.model.encode(contents)
            
            return True
        except ImportError:
            print("未安裝 sentence-transformers，僅使用關鍵詞檢索")
            return False

    def search_by_embedding(self, query: str, top_k: int = 3) -> List[Dict]:
        """使用 embedding 相似度檢索"""
        import numpy as np
        
        # 將查詢轉為 embedding
        query_embedding = self.model.encode([query])[0]
        
        # 計算相似度
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # 取得 top_k 相似段落
        top_indices = np.argsort(-similarities)[:top_k]
        results = [self.paragraphs[i] for i in top_indices]
        
        return results

    def search(self, query: str, top_k: int = 3, return_full_paragraph: bool = True) -> List[Dict]:
        """檢索相關段落，返回完整段落內容"""
        # 嘗試使用 embedding 搜索
        if self.has_embedding:
            try:
                return self.search_by_embedding(query, top_k)
            except Exception as e:
                print(f"Embedding 搜索失敗: {e}")
                print("回退到關鍵詞搜索")
        
        # 關鍵詞搜索
        results = []
        # 先在段落中搜索
        for para in self.paragraphs:
            if query in para['content']:
                results.append(para)
        
        # 若找不到完全匹配，則用部分匹配
        if not results:
            for para in self.paragraphs:
                if any(q in para['content'] for q in query.split()):
                    results.append(para)
        
        # 如果段落搜索沒有結果，則搜索整個文檔
        if not results:
            for doc in self.docs:
                if query in doc.get('content', ''):
                    # 找到匹配文檔後，返回包含查詢詞的段落
                    content = doc.get('content', '')
                    para_splits = self._split_to_paragraphs(content)
                    
                    # 找到包含查詢詞的段落
                    for i, para in enumerate(para_splits):
                        if query in para:
                            results.append({
                                'id': f"{doc.get('id', '')}_p{i}",
                                'doc_id': doc.get('id', ''),
                                'title': doc.get('title', ''),
                                'content': para.strip(),
                                'paragraph_index': i
                            })
        
        return results[:top_k]

    def format_cbeta_reference(self, doc: Dict) -> str:
        """產生標準 CBETA 引用格式"""
        doc_id = doc.get('doc_id', doc.get('id', ''))
        title = doc.get('title', '')
        
        # 如果標題為空，嘗試從原始文檔獲取
        if not title and doc_id:
            for original_doc in self.docs:
                if original_doc.get('id', '') == doc_id:
                    title = original_doc.get('title', '')
                    break
        
        url = f'https://cbetaonline.dila.edu.tw/zh/{doc_id}'
        return f"{title}（CBETA編號：{doc_id}）\n{url}"

# 用法示例
if __name__ == "__main__":
    searcher = CBETASearcher()
    query = "菩薩"
    results = searcher.search(query, return_full_paragraph=True)
    for doc in results:
        print(searcher.format_cbeta_reference(doc))
        print(doc['content'])
        print('---')
