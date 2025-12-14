from fastapi import FastAPI, File, UploadFile, Form, Request, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer
import shutil
import os
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import timedelta

from llm import DocumentQAService
# --------- 核心服务类 DocumentQAService ------------


# ------- 实例化QA服务对象，传递llm -----------
from llm import get_chat_llm_instance  # 你需提供此函数或直接传入llm实例
llm = get_chat_llm_instance()  # 返回已设置好dashscope的ChatOpenAI对象
qa_service = DocumentQAService(llm=llm)

# -------- 导入认证和数据库相关模块 -------------
from models import User, get_db
from schemas import UserCreate, UserLogin, UserResponse, Response
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# -------- FastAPI 接口实现部分 -------------
from fastapi.staticfiles import StaticFiles

app = FastAPI()
UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# OAuth2密码Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 配置静态文件服务
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

def process_document_background(save_path: str):
    """
    后台任务：处理文档并加载到向量数据库
    """
    try:
        n_chunks = qa_service.add_document(save_path)
        print(f"文档 {save_path} 处理完成，共生成 {n_chunks} 个文档块")
    except Exception as e:
        print(f"文档 {save_path} 处理失败: {str(e)}")

@app.post("/upload_doc/")
def upload_doc(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    try:
        file_ext = os.path.splitext(file.filename)[-1]
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # 将文档向量化任务添加到后台任务队列
        background_tasks.add_task(process_document_background, save_path)
        return JSONResponse(content={
            "code": 0, 
            "msg": "文档上传成功，正在后台处理中，请稍候...", 
            "filename": file.filename
        })
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": str(e)})

@app.post("/qa/")
def qa(query: str = Form(...)):
    try:
        res = qa_service.answer(query)
        return JSONResponse(content={"code": 0, "answer": res["answer"], "source": res["source"]})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": str(e)})

# -------- 用户认证接口 --------

# 注册接口
@app.post("/register/")
def register(user_create: UserCreate = Depends(UserCreate), db: Session = Depends(get_db)):
    try:
        # 检查密码是否一致
        if user_create.password != user_create.confirm_password:
            return JSONResponse(content={"code": 1, "msg": "两次输入的密码不一致"})

        # 检查用户名是否已存在
        db_user = db.query(User).filter(User.username == user_create.username).first()
        if db_user:
            return JSONResponse(content={"code": 1, "msg": "用户名已存在"})

        # 检查邮箱是否已存在
        db_user = db.query(User).filter(User.email == user_create.email).first()
        if db_user:
            return JSONResponse(content={"code": 1, "msg": "邮箱已存在"})

        # 创建新用户
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return JSONResponse(content={"code": 0, "msg": "注册成功", "data": {"user_id": db_user.id}})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"注册失败：{str(e)}"})

# 登录接口
@app.post("/login/")
def login(user_login: UserLogin = Depends(UserLogin), db: Session = Depends(get_db)):
    try:
        # 查找用户（支持用户名或邮箱登录）
        db_user = db.query(User).filter(
            (User.username == user_login.username) | (User.email == user_login.username)
        ).first()
        if not db_user:
            return JSONResponse(content={"code": 1, "msg": "用户名或密码错误"})

        # 验证密码
        if not verify_password(user_login.password, db_user.hashed_password):
            return JSONResponse(content={"code": 1, "msg": "用户名或密码错误"})

        # 检查用户是否激活
        if not db_user.is_active:
            return JSONResponse(content={"code": 1, "msg": "用户已被禁用"})

        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username},
            expires_delta=access_token_expires
        )

        return JSONResponse(content={
            "code": 0, 
            "msg": "登录成功", 
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": db_user.id,
                    "username": db_user.username,
                    "email": db_user.email
                }
            }
        })
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"登录失败：{str(e)}"})

# --- 首页路由，返回完整的前端页面 ---
@app.get("/", response_class=HTMLResponse)
def index():
    with open("../frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
