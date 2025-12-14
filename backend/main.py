# 导入配置好的FastAPI应用
from app.events.system import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
