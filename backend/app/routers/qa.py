from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

# 导入QA服务
from app.services.qa_service import QAService

# 实例化QA服务
qa_service = QAService()

# 创建APIRouter
router = APIRouter(
    prefix="/api",
    tags=["问答服务"]
)

@router.post("/qa/")
def qa(query: str = Form(...)):
    try:
        res = qa_service.answer(query)
        return JSONResponse(content={"code": 0, "answer": res["answer"], "source": res["source"]})
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": str(e)})
