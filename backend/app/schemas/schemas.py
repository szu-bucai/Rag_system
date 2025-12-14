from pydantic import BaseModel, EmailStr, Field

# 用户注册请求模型
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    confirm_password: str = Field(..., description="确认密码")

# 用户登录请求模型
class UserLogin(BaseModel):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

# 用户响应模型
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True

# 通用响应模型
class Response(BaseModel):
    code: int = Field(..., description="状态码，0表示成功，1表示失败")
    msg: str = Field(..., description="消息")
    data: dict = Field(default={}, description="数据")
