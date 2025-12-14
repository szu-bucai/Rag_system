from fastapi import APIRouter, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
import shutil
import os
from typing import List, Optional

# 导入文档服务
from app.services.document_service import DocumentService

# 实例化文档服务
document_service = DocumentService()

# 创建APIRouter
router = APIRouter(
    prefix="/api",
    tags=["文档处理"]
)

# 配置上传目录
UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_document_background(save_path: str):
    """
    后台任务：处理文档并加载到向量数据库
    """
    try:
        n_chunks = document_service.add_document(save_path)
        print(f"文档 {save_path} 处理完成，共生成 {n_chunks} 个文档块")
    except Exception as e:
        print(f"文档 {save_path} 处理失败: {str(e)}")

@router.post("/upload_doc/")
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
