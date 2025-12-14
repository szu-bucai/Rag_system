from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

# -------- FastAPI 应用初始化 -------------
app = FastAPI()

# 配置静态文件服务
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# -------- 导入并注册所有路由 -------------
from app.routers.document import router as document_router
from app.routers.qa import router as qa_router
from app.routers.auth import router as auth_router

# 注册带/api前缀的路由
app.include_router(document_router)
app.include_router(qa_router)
app.include_router(auth_router)

# 为了保持向后兼容，同时注册不带/api前缀的路由
# 文档上传路由
app.include_router(document_router, prefix="", include_in_schema=False)
# 问答路由
app.include_router(qa_router, prefix="", include_in_schema=False)
# 认证路由
app.include_router(auth_router, prefix="", include_in_schema=False)

# --- 首页路由，返回完整的前端页面 ---
@app.get("/", response_class=HTMLResponse)
def index():
    with open("../frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
