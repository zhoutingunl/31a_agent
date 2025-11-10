"""
文件：stt_service.py
功能：语音识别服务（Speech-to-Text）
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Optional

import httpx

from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class STTService:
    """语音识别服务"""
    
    def __init__(self):
        """初始化STT服务"""
        # 百度千帆配置
        self.api_key = config.get("llm.providers.qianfan.api_key", "")
        self.secret_key = config.get("llm.providers.qianfan.secret_key", "")
        self.base_url = "https://aip.baidubce.com"
        
        if not self.api_key or not self.secret_key:
            logger.warning("未配置百度千帆API密钥，STT功能将无法使用")
    
    def _get_access_token(self) -> str:
        """
        获取百度API访问令牌
        
        返回:
            str: 访问令牌
        """
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        response = httpx.post(url, params=params)
        result = response.json()
        
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"获取访问令牌失败: {result}")
    
    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        format: str = "wav",
        rate: int = 16000
    ) -> str:
        """
        语音转文字
        
        参数:
            audio_data (bytes): 音频数据
            filename (str): 文件名
            format (str): 音频格式（wav, mp3, m4a, flac）
            rate (int): 采样率
        
        返回:
            str: 识别的文字
        """
        logger.info(
            "开始语音识别",
            filename=filename,
            format=format,
            audio_size=len(audio_data)
        )
        
        try:
            # 获取访问令牌
            access_token = self._get_access_token()
            
            # 准备请求
            url = f"https://vop.baidu.com/server_api"
            
            # 将音频转为base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 构建请求体
            payload = {
                "format": format,
                "rate": rate,
                "channel": 1,  # 单声道
                "cuid": "agent_stt",
                "len": len(audio_data),
                "speech": audio_base64,
                "dev_pid": 80001  # 中文普通话
            }
            
            # 发送请求
            headers = {
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url}?access_token={access_token}",
                    json=payload,
                    headers=headers
                )
                
                result = response.json()
                
                if result.get("err_no") == 0:
                    text = result.get("result", [""])[0]
                    logger.info(
                        "语音识别成功",
                        text_length=len(text)
                    )
                    return text
                else:
                    error_msg = result.get("err_msg", "未知错误")
                    raise Exception(f"语音识别失败: {error_msg}")
        
        except Exception as e:
            logger.error(
                "语音识别失败",
                error=str(e)
            )
            raise
    
    def transcribe_sync(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        format: str = "wav",
        rate: int = 16000
    ) -> str:
        """
        语音转文字（同步版本）
        
        参数:
            audio_data (bytes): 音频数据
            filename (str): 文件名
            format (str): 音频格式
            rate (int): 采样率
        
        返回:
            str: 识别的文字
        """
        import asyncio
        return asyncio.run(self.transcribe(audio_data, filename, format, rate))
