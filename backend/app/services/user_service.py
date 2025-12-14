from sqlalchemy.orm import Session
from datetime import timedelta

from app.models.models import User
from app.services.auth_service import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.schemas import UserCreate, UserLogin

class UserService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, user_create: UserCreate):
        """
        处理用户注册逻辑
        """
        # 检查密码是否一致
        if user_create.password != user_create.confirm_password:
            return {"code": 1, "msg": "两次输入的密码不一致"}

        # 检查用户名是否已存在
        db_user = self.db.query(User).filter(User.username == user_create.username).first()
        if db_user:
            return {"code": 1, "msg": "用户名已存在"}

        # 检查邮箱是否已存在
        db_user = self.db.query(User).filter(User.email == user_create.email).first()
        if db_user:
            return {"code": 1, "msg": "邮箱已存在"}

        # 创建新用户
        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return {"code": 0, "msg": "注册成功", "data": {"user_id": db_user.id}}

    def login(self, user_login: UserLogin):
        """
        处理用户登录逻辑
        """
        # 查找用户（支持用户名或邮箱登录）
        db_user = self.db.query(User).filter(
            (User.username == user_login.username) | (User.email == user_login.username)
        ).first()
        if not db_user:
            return {"code": 1, "msg": "用户名或密码错误"}

        # 验证密码
        if not verify_password(user_login.password, db_user.hashed_password):
            return {"code": 1, "msg": "用户名或密码错误"}

        # 检查用户是否激活
        if not db_user.is_active:
            return {"code": 1, "msg": "用户已被禁用"}

        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username},
            expires_delta=access_token_expires
        )

        return {
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
        }

    def get_user_by_username(self, username: str):
        """
        根据用户名获取用户信息
        """
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str):
        """
        根据邮箱获取用户信息
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int):
        """
        根据用户ID获取用户信息
        """
        return self.db.query(User).filter(User.id == user_id).first()
