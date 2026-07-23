import os
import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

async def send_telegram_media(
    chat_id: str,
    file_path: str,
    message_thread_id: Optional[str] = None,
    caption: Optional[str] = "",
    file_id: Optional[str] = None
) -> str:
    """
    Sends media back to Telegram.
    Supports both local file paths and direct Telegram file_id (from Telegram cloud).
    If local file was deleted by 14-day cleanup, automatically falls back to Telegram cloud file_id!
    """
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return "Ошибка: TELEGRAM_BOT_TOKEN не настроен на сервере."

    target_id = file_id or file_path

    # Check if target_id is a local file
    real_path = target_id.replace('/app/data/', '/openclaw_data/')
    is_local_file = os.path.exists(real_path) and os.path.isfile(real_path)

    data = {"chat_id": chat_id}
    if message_thread_id:
        data["message_thread_id"] = message_thread_id
    if caption:
        data["caption"] = caption

    if is_local_file:
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
        try:
            with open(real_path, 'rb') as f:
                files = {file_field: f}
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=data, files=files, timeout=30.0)
                    res_json = response.json()
                    if res_json.get("ok"):
                        return f"Файл успешно отправлен из локального кэша в чат {chat_id}."
                    logger.error(f"Telegram API error sending local file: {res_json}")
                    return f"Ошибка Telegram API: {res_json.get('description')}"
        except Exception as e:
            logger.error(f"Failed to send local telegram media: {e}")
            return f"Ошибка при отправке локального файла: {str(e)}"
    else:
        # Local file removed by cleanup — try sending directly via Telegram Cloud file_id!
        logger.info(f"Local file not found ({real_path}). Attempting send via Telegram cloud file_id: {target_id}")
        endpoints = [
            ("sendPhoto", "photo"),
            ("sendDocument", "document"),
            ("sendVideo", "video"),
            ("sendVoice", "voice")
        ]
        
        async with httpx.AsyncClient() as client:
            for ep, param_name in endpoints:
                payload = {**data, param_name: target_id}
                url = f"https://api.telegram.org/bot{token}/{ep}"
                try:
                    response = await client.post(url, json=payload, timeout=30.0)
                    res_json = response.json()
                    if res_json.get("ok"):
                        return f"Файл успешно восстановлен и отправлен напрямую из облака Telegram (file_id: {target_id})."
                except Exception as e:
                    logger.error(f"Error calling {ep}: {e}")

        return f"Не удалось отправить файл: локальный кэш {file_path} очищен, а file_id ('{target_id}') не найден в облаке Telegram."
