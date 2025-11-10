"""
文件：tts_service.py
功能：语音合成服务（Text-to-Speech）
"""

import base64
import json
from typing import Optional

import httpx

from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TTSService:
    """语音合成服务"""
    
    def __init__(self):
        """初始化TTS服务"""
        # 百度千帆配置
        self.api_key = config.get("llm.providers.qianfan.api_key", "")
        self.secret_key = config.get("llm.providers.qianfan.secret_key", "")
        
        if not self.api_key or not self.secret_key:
            logger.warning("未配置百度千帆API密钥，TTS功能将无法使用")
    
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
    
    async def synthesize(
        self,
        text: str,
        voice: str = "zh_female_shuangkuaisisi_moon_bigtts",
        speed: int = 5,
        pitch: int = 5,
        volume: int = 5
    ) -> bytes:
        """
        文字转语音
        
        参数:
            text (str): 要转换的文字
            voice (str): 语音类型
            speed (int): 语速（0-15，默认5）
            pitch (int): 音调（0-15，默认5）
            volume (int): 音量（0-15，默认5）
        
        返回:
            bytes: 音频数据
        """
        logger.info(
            "开始语音合成",
            text_length=len(text),
            voice=voice
        )
        
        try:
            # 获取访问令牌
            access_token = self._get_access_token()
            
            # 准备请求
            url = f"https://tsn.baidu.com/text2audio"
            
            # 构建参数
            params = {
                "tex": text,
                "per": voice,  # 发音人
                "spd": speed,  # 语速
                "pit": pitch,  # 音调
                "vol": volume,  # 音量
                "cuid": "agent_tts",
                "tok": access_token,
                "lan": "zh",  # 语言
                "ctp": 1  # 客户端类型
            }
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params)
                
                # 检查响应
                if response.headers.get("content-type", "").startswith("audio/"):
                    # 成功，返回音频数据
                    audio_data = response.content
                    logger.info(
                        "语音合成成功",
                        audio_size=len(audio_data)
                    )
                    return audio_data
                else:
                    # 失败，返回错误信息
                    error_msg = response.text
                    logger.error(
                        "语音合成失败",
                        error=error_msg
                    )
                    raise Exception(f"语音合成失败: {error_msg}")
        
        except Exception as e:
            logger.error(
                "语音合成失败",
                error=str(e)
            )
            raise
    
    def synthesize_sync(
        self,
        text: str,
        voice: str = "zh_female_shuangkuaisisi_moon_bigtts",
        speed: int = 5,
        pitch: int = 5,
        volume: int = 5
    ) -> bytes:
        """
        文字转语音（同步版本）
        
        参数:
            text (str): 要转换的文字
            voice (str): 语音类型
            speed (int): 语速
            pitch (int): 音调
            volume (int): 音量
        
        返回:
            bytes: 音频数据
        """
        import asyncio
        return asyncio.run(self.synthesize(text, voice, speed, pitch, volume))
    
    def get_available_voices(self) -> list:
        """
        获取可用的语音列表
        
        返回:
            list: 语音列表
        """
        return [
            {
                "value": "zh_female_shuangkuaisisi_moon_bigtts",
                "label": "女声-活泼"
            },
            {
                "value": "zh_male_zhipeng_moon_bigtts",
                "label": "男声-温和"
            },
            {
                "value": "zh_female_qianxi_moon_bigtts",
                "label": "女声-甜美"
            }
        ]
