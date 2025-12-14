import dotenv
import os
from langchain_openai import ChatOpenAI
from app.services.document_service import DocumentService

dotenv.load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_BASE_URL")

class QAService:
    def __init__(self, llm=None):
        self.document_service = DocumentService()
        self.llm = llm or self._get_default_llm()

    def _get_default_llm(self):
        """
        返回配置好的 ChatOpenAI 对象。
        """
        return ChatOpenAI(
            model="gpt-4o-mini",  
            temperature=0.3,
        )

    def answer(self, query: str, prompt_template=None, k=5):
        # 向量检索
        vec_docs = self.document_service.retrieve(query, k)
        # 关键词检索
        kw_docs = self.document_service.keyword_search(query)

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
