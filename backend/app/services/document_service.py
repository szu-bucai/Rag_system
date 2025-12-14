import os
import dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
import jieba

dotenv.load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")

# 使用官方 API 进行向量化
embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-small",
)

class DocumentService:
    def __init__(self, embedding_model=None, vectorstore_path="./chroma_db"):
        self.embedding_model = embedding_model or embeddings_model
        self.vectorstore_path = vectorstore_path

    def load_and_split(self, file_path: str, chunk_size=500, chunk_overlap=50, window_size=3):
        """
        文档分割，并为每个小Chunk生成其父窗口（聚合窗口）内容，窗口大小可调，默认3。
        返回带parent_content（父窗口内容）的doc列表。
        """
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
            raw_docs = loader.load()
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
            raw_docs = loader.load()
        else:
            raise ValueError("仅支持PDF或DOCX文档")
        
        # 清理和验证原始文档内容，确保都是字符串类型
        cleaned_docs = []
        for doc in raw_docs:
            if doc.page_content:
                # 确保 page_content 是字符串类型
                content = str(doc.page_content).strip()
                if content:  # 只保留非空内容
                    doc.page_content = content
                    cleaned_docs.append(doc)
        
        if not cleaned_docs:
            raise ValueError(f"文档 {file_path} 加载后没有有效内容")
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.split_documents(cleaned_docs)  # 这里 docs 是小chunk

        # 再次验证分割后的文档，确保所有内容都是有效的字符串
        valid_docs = []
        for doc in docs:
            if doc.page_content:
                content = str(doc.page_content).strip()
                if content:  # 只保留非空内容
                    doc.page_content = content
                    valid_docs.append(doc)
        
        if not valid_docs:
            raise ValueError(f"文档 {file_path} 分割后没有有效内容块")
        
        # 为每个小chunk加上其parent_content，parent_content为其窗口滑动拼接的大chunk
        new_docs = []
        n = len(valid_docs)
        for i in range(n):
            # 设置窗口区间
            start = max(0, i - (window_size // 2))
            end = min(n, start + window_size)
            start = max(0, end - window_size)  # 位置矫正，保证窗口足够
            # 拼接窗口内的chunk内容，确保都是字符串
            parent_content_parts = []
            for j in range(start, end):
                content = str(valid_docs[j].page_content).strip()
                if content:
                    parent_content_parts.append(content)
            parent_content = "\n".join(parent_content_parts)
            
            # 拷贝并加父窗口内容为元数据
            doc = valid_docs[i]
            doc.metadata = doc.metadata or {}
            doc.metadata["parent_content"] = parent_content if parent_content else str(doc.page_content)
            new_docs.append(doc)
        
        return new_docs

    def add_document(self, file_path: str, window_size=3, chunk_size=500, chunk_overlap=50):
        docs = self.load_and_split(
            file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            window_size=window_size
        )

        # 可选：限制长度，防止单条文本过长
        for d in docs:
            if len(d.page_content) > 3000:
                d.page_content = d.page_content[:3000]

        # 判断数据库是否存在
        db_exists = os.path.exists(self.vectorstore_path) and os.listdir(self.vectorstore_path)

        try:
            if db_exists:
                vectorstore = Chroma(
                    persist_directory=self.vectorstore_path,
                    embedding_function=self.embedding_model
                )
                vectorstore.add_documents(docs)
            else:
                vectorstore = Chroma.from_documents(
                    documents=docs,
                    embedding=self.embedding_model,
                    persist_directory=self.vectorstore_path
                )
        except Exception as e:
            raise Exception(f"向量化失败: {str(e)}")
        
        return len(docs)

    def get_vectorstore(self):
        return Chroma(persist_directory=self.vectorstore_path, embedding_function=self.embedding_model)

    def retrieve(self, query: str, k=5):
        vectorstore = self.get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)

    def keyword_search(self, query: str, top_k=5):
        """ 
        使用BM25算法检索包含关键词的文档块，支持中英文。
        """
        vectorstore = self.get_vectorstore()
        result = vectorstore.get()
        documents = result["documents"]
        metadatas = result["metadatas"]
        
        # 确保所有文档内容都是字符串类型
        documents = [str(doc) for doc in documents]
        
        # 文本预处理：中文分词
        def tokenize(text):
            return list(jieba.cut(text.lower()))
        
        # 构建BM25索引
        tokenized_docs = [tokenize(doc) for doc in documents]
        bm25 = BM25Okapi(tokenized_docs)
        
        # 检索与排序
        tokenized_query = tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        # 获取top_k结果的索引
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # 过滤无匹配结果
                from langchain_core.documents import Document
                results.append(Document(page_content=documents[idx], metadata=metadatas[idx]))
        return results
