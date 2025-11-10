"""
文件名: main.py
功能: FastAPI 应用入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.v1 import health, conversation, chat, message, general, customer_service, audio
from app.api.v1 import config as config_api
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_handler import global_exception_handler
from app.models.database import close_database
from app.utils.config import config
from app.utils.logger import get_logger
from app.utils.exceptions import AgentException

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在应用启动和关闭时执行特定操作。
    
    参数:
        app (FastAPI): FastAPI 应用实例
    """
    # 应用启动时
    logger.info(
        "应用启动",
        name=config.get("app.name", "Agent"),
        version=config.get("app.version", "0.1.0"),
        host=config.get("app.host", "0.0.0.0"),
        port=config.get("app.port", 8000)
    )
    
    yield  # 应用运行中
    
    # 应用关闭时
    logger.info("应用正在关闭...")
    close_database()  # 关闭数据库连接
    logger.info("应用已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=config.get("app.name", "Agent"),
    version=config.get("app.version", "0.1.0"),
    description="基于 LangChain 和 LangGraph 的智能 Agent 系统",
    docs_url="/docs",  # Swagger 文档地址
    redoc_url="/redoc",  # ReDoc 文档地址
    lifespan=lifespan  # 生命周期管理
)

# 添加 CORS 中间件（允许跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应限制）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

# 添加请求日志中间件
app.add_middleware(LoggingMiddleware)

# 注册全局异常处理器
app.add_exception_handler(AgentException, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册路由
# 健康检查接口（直接挂在根路径）
app.include_router(health.router, prefix="")

# API v1 路由
app.include_router(conversation.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(message.router, prefix="/api/v1")
app.include_router(audio.router, prefix="/api/v1")

# 角色专属API路由
app.include_router(general.router, prefix="/api/v1")
app.include_router(customer_service.router, prefix="/api/v1")

# 配置管理API路由
app.include_router(config_api.router, prefix="/api/v1")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/", summary="首页", include_in_schema=False)
async def root():
    """
    首页 - 返回聊天界面
    """
    return FileResponse("web/templates/chat.html")


@app.get("/api", summary="API信息")
async def api_info():
    """
    API 信息接口
    
    返回服务基本信息。
    """
    return {
        "service": config.get("app.name", "Agent"),
        "version": config.get("app.version", "0.1.0"),
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready"
    }


if __name__ == "__main__":
    import uvicorn
    
    # 从配置中获取服务器参数
    host = config.get("app.host", "0.0.0.0")
    port = config.get("app.port", 8000)
    debug = config.get("app.debug", True)
    
    logger.info(
        "启动服务器",
        host=host,
        port=port,
        debug=debug
    )
    
    # 启动服务器
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,  # 开发模式下自动重载
        log_level="info"
    )

