"""
文件：polish_service.py
功能：文本润色服务
"""

from app.core.llm.base import BaseLLM
from app.utils.logger import get_logger
from app.utils.config import config

logger = get_logger(__name__)


class PolishService:
    """文本润色服务"""
    
    def __init__(self, llm: BaseLLM):
        """
        初始化润色服务
        
        参数:
            llm (BaseLLM): LLM 实例
        """
        self.llm = llm
    
    async def polish(self, text: str) -> str:
        """
        润色口语化文本为书面语
        
        参数:
            text (str): 原始口语化文本
        
        返回:
            str: 润色后的书面语文本
        """
        logger.info(
            "开始文本润色",
            original_length=len(text)
        )
        
        # 构建润色 Prompt
        prompt = f"""将以下口语化文本润色为书面语，去除停顿词（如"嗯"、"那个"）、重复词、语气词，以及考虑可能有部分识别错误、同音字等原因，保留原意：

{text}

润色后的文本："""
        
        try:
            # 调用 LLM 润色
            polished_text = self.llm.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # 低温度，保证稳定性
                max_tokens=500
            )
            
            # 清理结果（去除可能的引号等）
            polished_text = polished_text.strip().strip('"""').strip("'''").strip()
            
            logger.info(
                "文本润色成功",
                original_length=len(text),
                polished_length=len(polished_text)
            )
            
            return polished_text
        
        except Exception as e:
            logger.error(
                "文本润色失败",
                error=str(e)
            )
            # 润色失败时返回原文
            return text
    
    def polish_sync(self, text: str) -> str:
        """
        润色口语化文本（同步版本）
        
        参数:
            text (str): 原始口语化文本
        
        返回:
            str: 润色后的书面语文本
        """
        import asyncio
        return asyncio.run(self.polish(text))
