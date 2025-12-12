from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
import shutil
import os
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter


from llm import DocumentQAService
# --------- 核心服务类 DocumentQAService ------------


# ------- 实例化QA服务对象，传递llm -----------
from llm import get_chat_llm_instance  # 你需提供此函数或直接传入llm实例
llm = get_chat_llm_instance()  # 返回已设置好dashscope的ChatOpenAI对象
qa_service = DocumentQAService(llm=llm)

# -------- FastAPI 接口实现部分 -------------
app = FastAPI()
UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload_doc/")
def upload_doc(file: UploadFile = File(...)):
    try:
        file_ext = os.path.splitext(file.filename)[-1]
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        n_chunks = qa_service.add_document(save_path)
        return JSONResponse(content={"code": 0, "msg": "文档入库成功", "doc_chunks": n_chunks})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": str(e)})

@app.post("/qa/")
def qa(query: str = Form(...)):
    try:
        res = qa_service.answer(query)
        return JSONResponse(content={"code": 0, "answer": res["answer"], "source": res["source"]})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": str(e)})

# --- 首页简单页面（可选） ---
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang='zh-CN'>
    <head>
        <meta charset='utf-8'><title>文档智能问答系统</title>
    </head>
    <body>
        <h2>上传文档（PDF/DOCX）：</h2>
        <form id='upload_form' enctype='multipart/form-data'>
        <input type='file' name='file' />
        <button type='button' onclick='uploadDoc()'>上传</button>
        </form>
        <h2>提问：</h2>
        <input type='text' id='question' placeholder='请输入您的问题...' style='width:400px' />
        <button onclick='submitQa()'>提交</button>
        <h3>答案：</h3>
        <pre id='answer'></pre>
        <h3>参考片段：</h3>
        <pre id='source'></pre>
        <script>
        function uploadDoc() {
            const form = document.getElementById('upload_form');
            const formData = new FormData(form);
            fetch('/upload_doc/', {method: 'POST', body: formData}).then(r=>r.json()).then(dat=>{
            alert(dat.msg)
            })
        }
        function submitQa(){
            const q=document.getElementById('question').value;
            const fd=new FormData();fd.append('query',q)
            fetch('/qa/', {method:'POST',body:fd}).then(r=>r.json()).then(dat=>{
            document.getElementById('answer').innerText=dat.answer||dat.msg;
            document.getElementById('source').innerText=(dat.source||[]).join("\n-----\n")
            })
        }
        </script>
    </body>
    </html>
    """)
