"""
文件名: config.py
功能: 配置管理 API 路由
提供配置的读取、更新、重载、提示词管理、角色管理等接口
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.schemas.config import (
    ConfigResponse, ConfigUpdateRequest, ConfigReloadResponse,
    PromptListResponse, PromptUpdateRequest, RoleListResponse,
    ReloadRequirementSchema
)
from app.services.config_service import ConfigService
from app.utils.logger import get_logger
from app.utils.exceptions import ConfigError

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/config", tags=["配置管理"])

# 创建服务实例
config_service = ConfigService()


@router.get("", response_model=ConfigResponse, summary="获取完整配置")
async def get_config():
    """
    获取完整的系统配置
    
    返回:
        ConfigResponse: 完整配置信息
    """
    try:
        config = config_service.get_config()
        logger.info("API: 获取配置成功")
        return config
    except ConfigError as e:
        logger.error("API: 获取配置失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("API: 获取配置异常", error=str(e))
        raise HTTPException(status_code=500, detail="获取配置失败")


@router.put("", response_model=ConfigResponse, summary="更新配置")
async def update_config(update_request: ConfigUpdateRequest):
    """
    更新系统配置
    
    参数:
        update_request (ConfigUpdateRequest): 配置更新请求
        
    返回:
        ConfigResponse: 更新后的配置信息
    """
    try:
        # 验证配置
        if not config_service.validate_config(update_request.dict(exclude_unset=True)):
            raise HTTPException(status_code=400, detail="配置验证失败")
        
        # 更新配置
        updated_config = config_service.update_config(update_request)
        
        logger.info("API: 更新配置成功")
        return updated_config
        
    except ConfigError as e:
        logger.error("API: 更新配置失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API: 更新配置异常", error=str(e))
        raise HTTPException(status_code=500, detail="更新配置失败")


@router.post("/reload", response_model=ConfigReloadResponse, summary="热重载配置")
async def reload_config():
    """
    尝试热重载配置
    
    返回:
        ConfigReloadResponse: 重载结果
    """
    try:
        result = config_service.reload_config()
        
        logger.info("API: 配置重载完成", 
                   success=result.success,
                   reloaded_sections=len(result.reloaded_sections),
                   restart_required=len(result.requires_restart))
        
        return result
        
    except ConfigError as e:
        logger.error("API: 配置重载失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("API: 配置重载异常", error=str(e))
        raise HTTPException(status_code=500, detail="配置重载失败")


@router.get("/prompts", response_model=PromptListResponse, summary="获取提示词列表")
async def get_prompts():
    """
    获取所有提示词文件
    
    返回:
        PromptListResponse: 提示词文件列表
    """
    try:
        prompts = config_service.get_prompts()
        
        logger.info("API: 获取提示词列表成功", count=len(prompts.prompts))
        return prompts
        
    except ConfigError as e:
        logger.error("API: 获取提示词列表失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("API: 获取提示词列表异常", error=str(e))
        raise HTTPException(status_code=500, detail="获取提示词列表失败")


@router.put("/prompts/{filename}", summary="更新提示词文件")
async def update_prompt(filename: str, update_request: PromptUpdateRequest):
    """
    更新指定的提示词文件
    
    参数:
        filename (str): 文件名
        update_request (PromptUpdateRequest): 更新请求
        
    返回:
        dict: 操作结果
    """
    try:
        # 验证文件名
        if not filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="提示词文件必须是 .txt 格式")
        
        # 更新提示词
        config_service.update_prompt(filename, update_request)
        
        logger.info("API: 更新提示词文件成功", filename=filename)
        return {"success": True, "message": f"提示词文件 {filename} 更新成功"}
        
    except ConfigError as e:
        logger.error("API: 更新提示词文件失败", filename=filename, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API: 更新提示词文件异常", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail="更新提示词文件失败")


@router.get("/roles", response_model=RoleListResponse, summary="获取角色配置列表")
async def get_roles():
    """
    获取所有角色配置
    
    返回:
        RoleListResponse: 角色配置列表
    """
    try:
        roles = config_service.get_roles()
        
        logger.info("API: 获取角色配置列表成功", count=len(roles.roles))
        return roles
        
    except ConfigError as e:
        logger.error("API: 获取角色配置列表失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("API: 获取角色配置列表异常", error=str(e))
        raise HTTPException(status_code=500, detail="获取角色配置列表失败")


@router.get("/reload-requirements", response_model=List[ReloadRequirementSchema], summary="获取重载需求")
async def get_reload_requirements():
    """
    获取配置项的重载需求信息
    
    返回:
        List[ReloadRequirementSchema]: 重载需求列表
    """
    try:
        requirements = config_service.get_reload_requirements()
        
        logger.info("API: 获取重载需求成功", count=len(requirements))
        return requirements
        
    except Exception as e:
        logger.error("API: 获取重载需求异常", error=str(e))
        raise HTTPException(status_code=500, detail="获取重载需求失败")


@router.get("/validate", summary="验证配置")
async def validate_config():
    """
    验证当前配置的有效性
    
    返回:
        dict: 验证结果
    """
    try:
        config = config_service.get_config()
        is_valid = config_service.validate_config(config.dict())
        
        result = {
            "valid": is_valid,
            "message": "配置验证通过" if is_valid else "配置验证失败"
        }
        
        logger.info("API: 配置验证完成", valid=is_valid)
        return result
        
    except ConfigError as e:
        logger.error("API: 配置验证失败", error=str(e))
        return {
            "valid": False,
            "message": f"配置验证失败: {str(e)}"
        }
    except Exception as e:
        logger.error("API: 配置验证异常", error=str(e))
        raise HTTPException(status_code=500, detail="配置验证失败")


@router.get("/backup", summary="备份配置")
async def backup_config():
    """
    备份当前配置文件
    
    返回:
        dict: 备份结果
    """
    try:
        backup_path = config_service.dao.backup_config()
        
        result = {
            "success": True,
            "message": "配置备份成功",
            "backup_path": backup_path
        }
        
        logger.info("API: 配置备份成功", backup_path=backup_path)
        return result
        
    except ConfigError as e:
        logger.error("API: 配置备份失败", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("API: 配置备份异常", error=str(e))
        raise HTTPException(status_code=500, detail="配置备份失败")


@router.get("/health", summary="配置服务健康检查")
async def config_health():
    """
    配置服务健康检查
    
    返回:
        dict: 健康状态
    """
    try:
        # 尝试读取配置
        config = config_service.get_config()
        
        # 检查关键配置项
        health_status = {
            "status": "healthy",
            "config_loaded": True,
            "app_name": config.app.name,
            "app_version": config.app.version,
            "llm_provider": config.llm.default_provider,
            "database_configured": bool(config.database.mysql),
            "message": "配置服务运行正常"
        }
        
        logger.info("API: 配置服务健康检查通过")
        return health_status
        
    except Exception as e:
        logger.error("API: 配置服务健康检查失败", error=str(e))
        return {
            "status": "unhealthy",
            "config_loaded": False,
            "message": f"配置服务异常: {str(e)}"
        }
