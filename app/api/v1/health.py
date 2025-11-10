"""
文件名: health.py
功能: 健康检查接口
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_database
from app.schemas.base import SuccessResponse
from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建路由
router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="健康检查")
async def health_check():
    """
    基础健康检查
    
    返回服务基本信息和运行状态。
    """
    return SuccessResponse.create(
        data={
            "status": "healthy",
            "service": config.get("app.name", "Agent"),
            "version": config.get("app.version", "0.1.0"),
            "timestamp": datetime.now().isoformat()
        },
        message="服务运行正常"
    )


@router.get("/ready", summary="就绪检查")
async def readiness_check(db: Session = Depends(get_database)):
    """
    就绪检查
    
    检查服务是否就绪（包括数据库连接等）。
    
    参数:
        db (Session): 数据库会话
    
    返回:
        JSON: 就绪状态
    """
    checks = {
        "database": False,
        "llm": False
    }
    
    # 检查数据库连接
    try:
        result = db.execute(text("SELECT 1"))
        result.fetchone()  # 获取结果
        checks["database"] = True
    except Exception as e:
        logger.error("数据库连接检查失败", error=str(e))
    
    # 检查 LLM 配置
    try:
        api_key = config.get("llm.providers.deepseek.api_key")
        if api_key:
            checks["llm"] = True
    except Exception as e:
        logger.error("LLM 配置检查失败", error=str(e))
    
    # 判断整体就绪状态
    all_ready = all(checks.values())
    
    return SuccessResponse.create(
        data={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        },
        message="服务就绪" if all_ready else "服务未就绪"
    )


@router.get("/stats", summary="系统统计")
async def system_stats(db: Session = Depends(get_database)):
    """
    获取系统运行统计信息
    
    包括反思功能的统计信息，但不暴露反思的内部实现细节。
    
    参数:
        db (Session): 数据库会话
    
    返回:
        JSON: 系统统计信息
    """
    try:
        # 基础统计信息
        stats = {
            "service": config.get("app.name", "Agent"),
            "version": config.get("app.version", "0.1.0"),
            "uptime": "运行中",
            "timestamp": datetime.now().isoformat()
        }
        
        # 数据库统计
        try:
            # 获取会话数量
            conversation_count = db.execute(text("SELECT COUNT(*) FROM conversations")).scalar()
            # 获取消息数量
            message_count = db.execute(text("SELECT COUNT(*) FROM messages")).scalar()
            
            stats["database"] = {
                "conversations": conversation_count or 0,
                "messages": message_count or 0,
                "status": "connected"
            }
        except Exception as e:
            logger.error("获取数据库统计失败", error=str(e))
            stats["database"] = {"status": "error", "error": str(e)}
        
        # 执行模式统计（从日志或缓存中获取，这里简化处理）
        stats["execution_modes"] = {
            "simple": "基础对话模式",
            "planning": "任务规划模式", 
            "reflection": "高质量输出模式（自动启用）"
        }
        
        return SuccessResponse.create(
            data=stats,
            message="系统统计获取成功"
        )
        
    except Exception as e:
        logger.error("获取系统统计失败", error=str(e))
        return SuccessResponse.create(
            data={"error": str(e)},
            message="系统统计获取失败",
            success=False
        )
