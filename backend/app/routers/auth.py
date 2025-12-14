from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 导入认证和数据库相关模块
from app.models.models import get_db
from app.schemas.schemas import UserCreate, UserLogin
from app.services.user_service import UserService

# 创建APIRouter
router = APIRouter(
    prefix="/api",
    tags=["用户认证"]
)

# 注册接口
@router.post("/register/")
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    try:
        user_service = UserService(db)
        result = user_service.register(user_create)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"注册失败：{str(e)}"})

# 登录接口
@router.post("/login/")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    try:
        user_service = UserService(db)
        result = user_service.login(user_login)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"code": 1, "msg": f"登录失败：{str(e)}"})
