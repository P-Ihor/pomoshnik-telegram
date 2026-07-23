import base64
import io
import logging
import re
from pathlib import Path
from pyzbar.pyzbar import decode
from PIL import Image
import google.generativeai as genai
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)

# OpenRouter client for Vision fallback
_openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
) if settings.OPENROUTER_API_KEY else None

def _fix_base64(b64_string: str) -> str:
    """Fixes missing padding in base64 strings."""
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    b64_string = re.sub(r'[^A-Za-z0-9+/]', '', b64_string)
    return b64_string + '=' * (-len(b64_string) % 4)

def resolve_file_bytes(file_path: str = '', base64_data: str = '') -> bytes:
    """Resolves raw file bytes either from disk path or base64 string."""
    if file_path:
        p = file_path
        if p.startswith('/app/data'):
            p = p.replace('/app/data', '/openclaw_data', 1)
        path_obj = Path(p)
        if path_obj.exists():
            return path_obj.read_bytes()
        alt_path = Path(file_path)
        if alt_path.exists():
            return alt_path.read_bytes()
        raise FileNotFoundError(f"File not found on server disk: {file_path}")
    elif base64_data:
        fixed_b64 = _fix_base64(base64_data)
        return base64.b64decode(fixed_b64)
    raise ValueError("Neither file_path nor base64_data provided.")

def _vision_via_openrouter(prompt: str, image_base64: str, mime_type: str) -> str:
    """Fallback: использует OpenRouter Vision API, если Gemini недоступен."""
    if not _openrouter_client:
        return None
    try:
        resp = _openrouter_client.chat.completions.create(
            model=settings.MODEL_VISION,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                }}
            ]}]
        )
        return f"⚠️ (Резервный анализ через OpenRouter)\n{resp.choices[0].message.content}"
    except Exception as e:
        logger.error(f"OpenRouter Vision fallback failed: {e}")
        return None


def analyze_image(file_path: str = '', image_base64: str = '', mime_type: str = 'image/jpeg', user_note: str = '') -> str:
    """Uses Google Gemini Vision API to describe image.
    Accepts file_path directly (e.g. /app/data/media/inbound/photo.jpg). DO NOT run base64 manually!"""
    try:
        image_data = resolve_file_bytes(file_path=file_path, base64_data=image_base64)
        qr_text = decode_qr_barcode_internal(image_data)
        
        prompt = (
            "Опиши это изображение максимально подробно на русском языке. "
            "Извлеки весь видимый текст. Если на фото люди, опиши их. Если это документ, чек или счет - "
            "сделай структурированную выжимку сумм и дат. "
            f"\nКомментарий пользователя: {user_note}"
        )
        
        result = None
        
        if settings.GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([
                    prompt, 
                    {"mime_type": mime_type, "data": image_data}
                ])
                result = response.text
            except Exception as e:
                logger.warning(f"Gemini Vision failed: {e}, trying OpenRouter fallback...")
        
        if result is None and (image_base64 or file_path):
            b64_str = base64.b64encode(image_data).decode('utf-8')
            result = _vision_via_openrouter(prompt, b64_str, mime_type)
        
        if result is None:
            return "Ошибка: Оба сервиса анализа изображений недоступны (Gemini и OpenRouter)."
        
        if qr_text:
            result += f"\n\n📱 Найдено в QR/штрихкоде:\n{qr_text}"
            
        return result
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return f"Ошибка при анализе изображения: {e}"

def analyze_video(file_path: str = '', video_base64: str = '', mime_type: str = 'video/mp4', user_note: str = '') -> str:
    """Uses Gemini to describe video content. Pass file_path directly."""
    if not settings.GOOGLE_API_KEY and not _openrouter_client:
        return "Ошибка: Не настроены API ключи для анализа видео."
        
    try:
        video_data = resolve_file_bytes(file_path=file_path, base64_data=video_base64)
        prompt = (
            "Посмотри это видео и опиши, что на нем происходит, на русском языке. "
            f"\nКомментарий пользователя: {user_note}"
        )
        
        if settings.GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([
                    prompt, 
                    {"mime_type": mime_type, "data": video_data}
                ])
                return response.text
            except Exception as e:
                logger.warning(f"Gemini Video failed: {e}")
        
        return "⚠️ Анализ видео временно недоступен (Gemini выдал ошибку). Попробуйте позже или отправьте скриншот из видео."
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        return f"Ошибка при анализе видео: {e}"

def analyze_audio(file_path: str = '', audio_base64: str = '', mime_type: str = 'audio/ogg') -> str:
    """Transcribes audio file using Gemini. Pass file_path directly (e.g. /app/data/media/inbound/audio.ogg). DO NOT run base64 manually."""
    if not settings.GOOGLE_API_KEY:
        return "Ошибка: Не настроен GOOGLE_API_KEY для транскрипции аудио."
        
    try:
        audio_data = resolve_file_bytes(file_path=file_path, base64_data=audio_base64)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = "Сделай полную текстовую транскрипцию этого аудио на русском языке."
        
        response = model.generate_content([
            prompt, 
            {"mime_type": mime_type, "data": audio_data}
        ])
        
        return response.text
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return f"⚠️ Ошибка при транскрипции аудио: {e}\nПопробуйте отправить ещё раз или позже."

def decode_qr_barcode(file_path: str = '', image_base64: str = '') -> str:
    """Decodes QR codes and barcodes from image."""
    try:
        image_data = resolve_file_bytes(file_path=file_path, base64_data=image_base64)
        result = decode_qr_barcode_internal(image_data)
        return result if result else "Коды не найдены на изображении."
    except Exception as e:
        logger.error(f"QR decode failed: {e}")
        return f"Ошибка при декодировании QR: {e}"

def decode_qr_barcode_internal(image_data: bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_data))
        decoded_objects = decode(image)
        
        if not decoded_objects:
            gray_image = image.convert('L')
            decoded_objects = decode(gray_image)
            
        if not decoded_objects:
            return ""
            
        results = []
        for obj in decoded_objects:
            try:
                data = obj.data.decode('utf-8')
            except:
                data = obj.data.decode('latin-1', errors='ignore')
            results.append(f"{obj.type}: {data}")
            
        return "\n".join(results)
    except Exception as e:
        logger.error(f"Internal QR decode error: {e}")
        return ""
