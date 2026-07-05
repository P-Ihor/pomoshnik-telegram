import base64
import io
import logging
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


def analyze_image(image_base64: str, mime_type: str = 'image/jpeg', user_note: str = '') -> str:
    """Uses Google Gemini Vision API to describe image and runs QR/barcode detection via pyzbar.
    Falls back to OpenRouter Vision if Gemini fails.
    Returns detailed description in Russian."""

    try:
        # Decode base64
        image_data = base64.b64decode(image_base64)
        
        # 1. QR/Barcode decode (always works, local)
        qr_text = decode_qr_barcode_internal(image_data)
        
        prompt = (
            "Опиши это изображение максимально подробно на русском языке. "
            "Извлеки весь видимый текст. Если на фото люди, опиши их. Если это документ, чек или счет - "
            "сделай структурированную выжимку сумм и дат. "
            f"\nКомментарий пользователя: {user_note}"
        )
        
        result = None
        
        # 2. Try Gemini Vision first
        if settings.GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-2.0-flash-001')
                response = model.generate_content([
                    prompt, 
                    {"mime_type": mime_type, "data": image_data}
                ])
                result = response.text
            except Exception as e:
                logger.warning(f"Gemini Vision failed: {e}, trying OpenRouter fallback...")
        
        # 3. Fallback to OpenRouter Vision
        if result is None:
            result = _vision_via_openrouter(prompt, image_base64, mime_type)
        
        if result is None:
            return "Ошибка: Оба сервиса анализа изображений недоступны (Gemini и OpenRouter)."
        
        if qr_text:
            result += f"\n\n📱 Найдено в QR/штрихкоде:\n{qr_text}"
            
        return result
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return f"Ошибка при анализе изображения: {e}"

def analyze_video(video_base64: str, mime_type: str = 'video/mp4', user_note: str = '') -> str:
    """Uses Gemini to describe video content. Falls back to OpenRouter if Gemini fails."""
    if not settings.GOOGLE_API_KEY and not _openrouter_client:
        return "Ошибка: Не настроены API ключи для анализа видео."
        
    try:
        video_data = base64.b64decode(video_base64)
        prompt = (
            "Посмотри это видео и опиши, что на нем происходит, на русском языке. "
            f"\nКомментарий пользователя: {user_note}"
        )
        
        # Try Gemini first
        if settings.GOOGLE_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-2.0-flash-001')
                response = model.generate_content([
                    prompt, 
                    {"mime_type": mime_type, "data": video_data}
                ])
                return response.text
            except Exception as e:
                logger.warning(f"Gemini Video failed: {e}")
        
        # Fallback: describe that we couldn't process the video
        return "⚠️ Анализ видео временно недоступен (Gemini выдал ошибку). Попробуйте позже или отправьте скриншот из видео."
        
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        return f"Ошибка при анализе видео: {e}"

def analyze_audio(audio_base64: str, mime_type: str = 'audio/ogg') -> str:
    """Primary: Gemini audio. Returns transcription. Falls back gracefully."""
    if not settings.GOOGLE_API_KEY:
        return "Ошибка: Не настроен GOOGLE_API_KEY для транскрипции аудио."
        
    try:
        audio_data = base64.b64decode(audio_base64)
        model = genai.GenerativeModel('gemini-2.0-flash-001')
        prompt = "Сделай полную текстовую транскрипцию этого аудио на русском языке."
        
        response = model.generate_content([
            prompt, 
            {"mime_type": mime_type, "data": audio_data}
        ])
        
        return response.text
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        return f"⚠️ Ошибка при транскрипции аудио: {e}\nПопробуйте отправить ещё раз или позже."

def decode_qr_barcode(image_base64: str) -> str:
    """Decodes QR codes and barcodes from image."""
    try:
        image_data = base64.b64decode(image_base64)
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
