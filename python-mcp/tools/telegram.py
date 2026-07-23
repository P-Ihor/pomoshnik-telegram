import os
import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

async def send_telegram_media(chat_id: str, file_path: str, message_thread_id: Optional[str] = None, caption: Optional[str] = "") -> str:
    """Sends a local media file back to a Telegram chat."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return "Ошибка: TELEGRAM_BOT_TOKEN не настроен на сервере."

    # Convert the agent's internal path to the MCP's mounted path
    # Agent knows it as /app/data/media/inbound/...
    # MCP knows it as /openclaw_data/media/inbound/...
    real_path = file_path.replace('/app/data/', '/openclaw_data/')

    if not os.path.exists(real_path):
        return f"Ошибка: Файл {file_path} уже удален из временной памяти сервера."

    # Determine file type
    ext = os.path.splitext(real_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.heif']:
        endpoint = "sendPhoto"
        file_field = "photo"
    elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
        endpoint = "sendVideo"
        file_field = "video"
    elif ext in ['.ogg', '.mp3', '.wav', '.m4a']:
        endpoint = "sendVoice"
        file_field = "voice"
    else:
        endpoint = "sendDocument"
        file_field = "document"

    url = f"https://api.telegram.org/bot{token}/{endpoint}"
    
    data = {"chat_id": chat_id}
    if message_thread_id:
        data["message_thread_id"] = message_thread_id
    if caption:
        data["caption"] = caption

    try:
        with open(real_path, 'rb') as f:
            files = {file_field: f}
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data, files=files, timeout=30.0)
                result = response.json()
                if result.get("ok"):
                    return f"Файл успешно отправлен в чат {chat_id}."
                else:
                    logger.error(f"Telegram API error: {result}")
                    return f"Ошибка API Telegram: {result.get('description')}"
    except Exception as e:
        logger.error(f"Failed to send telegram media: {e}")
        return f"Внутренняя ошибка при отправке файла: {str(e)}"
