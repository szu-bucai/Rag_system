import os
import dotenv
import base64
import json
import re
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_community.vectorstores import Chroma
from pdf2image import convert_from_path
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
dotenv.load_dotenv()
os.environ["DASHSCOPE_API_KEY"]=os.getenv("DASHSCOPE_API_KEY")

class DocumentQAService:
    def __init__(self, embedding_model="nomic-embed-text", llm=None, vectorstore_path="./chroma_db"):
        self.embedding_model = embedding_model
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vectorstore_path = vectorstore_path
        self.llm = llm  # llm实例需传入如ChatOpenAI

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
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.split_documents(raw_docs)  # 这里 docs 是小chunk

        # 为每个小chunk加上其parent_content，parent_content为其窗口滑动拼接的大chunk
        new_docs = []
        n = len(docs)
        for i in range(n):
            # 设置窗口区间
            start = max(0, i - (window_size // 2))
            end = min(n, start + window_size)
            start = max(0, end - window_size)  # 位置矫正，保证窗口足够
            # 拼接窗口内的chunk内容
            parent_content = "\n".join([docs[j].page_content for j in range(start, end)])
            # 拷贝并加父窗口内容为元数据
            doc = docs[i]
            doc.metadata = doc.metadata or {}
            doc.metadata["parent_content"] = parent_content
            new_docs.append(doc)
        return new_docs

    def add_document(self, file_path: str, window_size=3, chunk_size=500, chunk_overlap=50):
        """
        文档向量入库，并自动生成parent_content元信息。
        """
        docs = self.load_and_split(file_path, chunk_size=chunk_size, chunk_overlap=chunk_overlap, window_size=window_size)
        vectorstore = Chroma.from_documents(docs, self.embeddings, persist_directory=self.vectorstore_path)
        vectorstore.persist()
        return len(docs)

    def get_vectorstore(self):
        return Chroma(persist_directory=self.vectorstore_path, embedding_function=self.embeddings)

    def retrieve(self, query: str, k=5):
        vectorstore = self.get_vectorstore()
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        return retriever.get_relevant_documents(query)

    def keyword_search(self, query: str):
      """ 
      遍历所有chunk，返回内容包含query关键词的小块（不区分大小写，若需更精细可正则匹配）。
      """
      vectorstore = self.get_vectorstore()
      # 获取全部document对象（适配Chroma，若用其他库这里需要变通，重点是获取所有chunk）
      all_docs = vectorstore.get()["documents"]  # 或vectorstore._collection.get()["documents"]
      # all_docs是dict，需要转为SimpleDocument对象形式
      results = []
      for d in all_docs:
          # d为dict，包含page_content和metadata属性
          page_content = d.get("page_content", "")
          metadata = d.get("metadata", {})
          if query.lower() in page_content.lower():
              # 还原为langchain文档对象（可根据你向量入库的数据结构调整）
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
        return {"answer": answer, "source": parent_chunks}

def get_chat_llm_instance():
    """
    返回配置好的 Qwen3-Plus 阿里云 DashScope ChatOpenAI 对象。
    """
    llm = ChatOpenAI(
        model="qwen3-4B-Instruct-2507",  # 阿里云 Qwen 模型，可替换为自己的模型名称
        api_key=os.environ.get("DASHSCOPE_API_KEY", ""),
        temperature=0.3,
        base_url="https://localhost:8080/v1",
    )
    return llm
