"""
文件：audio.py
功能：语音处理 API（STT/TTS）
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import json

from app.api.deps import get_database, get_llm_instance
from app.schemas.base import SuccessResponse
from app.schemas.message import VoiceTextRequest
from app.utils.logger import get_logger
from app.core.audio.stt_service import STTService
from app.core.audio.tts_service import TTSService
from app.core.text.polish_service import PolishService

logger = get_logger(__name__)

# 创建路由
router = APIRouter(prefix="/audio", tags=["语音"])

# 初始化服务
stt_service = STTService()
tts_service = TTSService()


@router.post("/stt", summary="语音转文字")
async def speech_to_text(
    file: UploadFile = File(...),
    db: Session = Depends(get_database)
):
    """
    语音转文字接口
    
    参数:
        file (UploadFile): 音频文件（支持 wav, mp3, m4a, flac 等格式）
        db (Session): 数据库会话
    
    返回:
        SuccessResponse: 转换后的文字内容
    """
    logger.info(
        "收到语音转文字请求",
        filename=file.filename,
        content_type=file.content_type
    )
    
    try:
        # 读取音频文件
        audio_data = await file.read()
        
        # 执行语音识别
        text = await stt_service.transcribe(
            audio_data=audio_data,
            filename=file.filename
        )
        
        logger.info(
            "语音转文字成功",
            filename=file.filename,
            text_length=len(text)
        )
        
        return SuccessResponse.create(
            data={"text": text},
            message="语音识别成功"
        )
        
    except Exception as e:
        logger.error(
            "语音转文字失败",
            filename=file.filename,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


@router.post("/tts", summary="文字转语音")
async def text_to_speech(
    text: str,
    voice: str = "zh_female_shuangkuaisisi_moon_bigtts"  # 默认女声
):
    """
    文字转语音接口
    
    参数:
        text (str): 要转换的文字内容
        voice (str): 语音类型（可选）
    
    返回:
        StreamingResponse: 音频流
    """
    logger.info(
        "收到文字转语音请求",
        text_length=len(text),
        voice=voice
    )
    
    try:
        # 执行语音合成
        audio_data = await tts_service.synthesize(
            text=text,
            voice=voice
        )
        
        logger.info(
            "文字转语音成功",
            text_length=len(text),
            audio_size=len(audio_data)
        )
        
        # 返回音频流
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
        
    except Exception as e:
        logger.error(
            "文字转语音失败",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.post("/voice-to-text", summary="接收前端语音识别文本（润色后处理）")
async def voice_to_text(
    request: VoiceTextRequest,
    db: Session = Depends(get_database),
    llm = Depends(get_llm_instance)
):
    """
    接收前端语音识别文本接口
    
    1. 接收前端 Web Speech API 识别的口语化文本
    2. LLM 润色为书面语
    3. 调用 Agent 处理
    4. 返回结果
    
    参数:
        text (str): 前端识别的口语化文本
        conversation_id (int): 会话ID
        db (Session): 数据库会话
        llm: LLM 实例
    
    返回:
        包含润色文本、Agent 回复的响应
    """
    logger.info(
        "收到语音识别文本",
        conversation_id=request.conversation_id,
        text_length=len(request.text)
    )
    
    try:
        # 1. 润色文本
        polish_service = PolishService(llm)
        polished_text = await polish_service.polish(request.text)
        
        logger.info(
            "文本润色完成",
            original=request.text[:50],
            polished=polished_text[:50]
        )
        
        # 2. 调用 Agent 处理
        from app.services.conversation_service import ConversationService
        from app.services.message_service import MessageService
        from app.core.agent.tool_agent import ToolAgent
        from app.tools.manager import tool_manager
        
        conv_service = ConversationService(db)
        msg_service = MessageService(db)
        
        # 验证会话是否存在
        conversation = conv_service.get_conversation(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息（润色后的文本）
        user_message = msg_service.create_message(
            conversation_id=request.conversation_id,
            role="user",
            content=polished_text  # 保存润色后的文本到历史记录
        )
        
        # 构建对话历史
        recent_messages = msg_service.get_recent_messages(request.conversation_id, limit=20)
        llm_messages = []
        for msg in recent_messages:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # 调用 Agent
        agent = ToolAgent(llm, tool_manager)
        assistant_text = agent.run(llm_messages, stream=False)
        
        # 保存回复
        assistant_message = msg_service.create_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=assistant_text,
            model_provider=llm.get_model_info()["provider"],
            model_name=llm.model_name
        )
        
        logger.info(
            "语音处理成功",
            conversation_id=request.conversation_id,
            polished_text_length=len(polished_text),
            assistant_text_length=len(assistant_text)
        )
        
        # 返回结果
        return SuccessResponse.create(
            data={
                "conversation_id": request.conversation_id,
                "original_text": request.text,  # 原始口语化文本
                "polished_text": polished_text,  # 润色后的文本
                "assistant_text": assistant_text,  # Agent 回复
                "user_message": {
                    "id": user_message.id,
                    "content": user_message.content,
                    "role": user_message.role
                },
                "assistant_message": {
                    "id": assistant_message.id,
                    "content": assistant_message.content,
                    "role": assistant_message.role
                }
            },
            message="语音处理成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "语音处理失败",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"语音处理失败: {str(e)}")
