import os
import dotenv
import base64
import json
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_chroma import Chroma
from pdf2image import convert_from_path
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
dotenv.load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")

# 使用官方 API 进行向量化
embeddings_model = OpenAIEmbeddings(
    model="text-embedding-3-small",

)

def get_chat_llm_instance():
    """
    返回配置好的 Qwen3-Plus 阿里云 DashScope ChatOpenAI 对象。
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",  
        temperature=0.3,
    )
    return llm

class DocumentQAService:
    def __init__(self, embedding_model=None, llm=None, vectorstore_path="./chroma_db"):
        self.embedding_model = embedding_model or "text-embedding-3-small"
        # 使用官方 API 的 embeddings 模型
        if embedding_model is not None and not isinstance(embedding_model, str):
            self.embeddings = embedding_model
        else:
            self.embeddings = embeddings_model
        self.vectorstore_path = vectorstore_path
        self.llm = llm

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
                    embedding_function=self.embeddings
                )
                vectorstore.add_documents(docs)
            else:
                vectorstore = Chroma.from_documents(
                    documents=docs,
                    embedding=self.embeddings,
                    persist_directory=self.vectorstore_path
                )
        except Exception as e:
            raise Exception(f"向量化失败: {str(e)}")
        
        return len(docs)



    def get_vectorstore(self):
        return Chroma(persist_directory=self.vectorstore_path, embedding_function=self.embeddings)

    def retrieve(self, query: str, k=5):
        vectorstore = self.get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)

    def keyword_search(self, query: str):
      """ 
      遍历所有chunk，返回内容包含query关键词的小块（不区分大小写，若需更精细可正则匹配）。
      """
      vectorstore = self.get_vectorstore()
      # 获取全部document对象（适配Chroma，若用其他库这里需要变通，重点是获取所有chunk）
      result = vectorstore.get()
      # 获取所有文档内容和元数据
      documents = result["documents"]
      metadatas = result["metadatas"]
      
      results = []
      for page_content, metadata in zip(documents, metadatas):
          # 确保page_content是字符串类型
          page_content = str(page_content)
          if query.lower() in page_content.lower():
              # 还原为langchain文档对象
              from langchain_core.documents import Document
              results.append(Document(page_content=page_content, metadata=metadata))
      return results

    def answer(self, query: str, prompt_template=None, k=5):
        # 向量检索
        vec_docs = self.retrieve(query, k)
        # 关键词检索
        kw_docs = self.keyword_search(query)

        # 合并，取所有的父窗口内容（去重，无内容也降级为本chunk）
        parent_chunks = list({
            doc.metadata.get("parent_content", doc.page_content)
            for doc in (vec_docs + kw_docs)
        })
        
        if prompt_template is None:
            prompt_template = """
            请你严格按照检索到的知识片段内容进行回答，不要编造知识，不要添加任何知识片段中未出现的内容。
            如果知识片段无法直接回答，请直接回复“未检索到相关答案”。

            知识片段：
            {text}

            用户问题：
            {question}
            """
        retrieved_text = "\n".join(parent_chunks)
        prompt = prompt_template.format(text=retrieved_text, question=query)
        if not self.llm:
            raise Exception("LLM未初始化")
        answer = self.llm.invoke(prompt)
        # 从AIMessage对象中提取文本内容
        answer_content = answer.content if hasattr(answer, 'content') else str(answer)
        return {"answer": answer_content, "source": parent_chunks}


