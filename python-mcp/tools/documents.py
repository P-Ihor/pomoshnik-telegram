import base64
import io
import logging
import yt_dlp
import trafilatura
from pypdf import PdfReader
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

# We use OpenRouter for text analysis
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
) if settings.OPENROUTER_API_KEY else None

def analyze_document(doc_base64: str, filename: str, mime_type: str) -> str:
    """For PDFs: pypdf text extraction + AI summary. For text files: direct AI analysis."""
    try:
        data = base64.b64decode(doc_base64)
        text_content = ""
        
        if mime_type == "application/pdf" or filename.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(data))
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        elif mime_type.startswith("text/") or filename.endswith((".txt", ".csv", ".md")):
            text_content = data.decode('utf-8', errors='ignore')
        else:
            return f"Неподдерживаемый тип документа для текстового анализа: {mime_type}. Попробуйте отправить как фото."

        if not text_content.strip():
            return "Документ пуст или текст не удалось извлечь (возможно, это сканированный PDF без OCR)."

        # Truncate if too long (rough limit for LLM context)
        text_content = text_content[:50000]

        system_prompt = "Ты аналитик документов. Проанализируй текст и выдай подробное резюме на русском языке."
        user_prompt = f"Файл: {filename}\nТекст:\n{text_content}"

        # Try OpenRouter first
        if openrouter_client:
            try:
                response = openrouter_client.chat.completions.create(
                    model=settings.MODEL_CHEAP,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as or_err:
                logger.warning(f"OpenRouter doc analysis failed: {or_err}, trying Gemini...")

        # Fallback to Gemini
        if settings.GOOGLE_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                model = genai.GenerativeModel('gemini-2.0-flash-001')
                resp = model.generate_content(f"{system_prompt}\n\n{user_prompt}")
                return f"⚠️ (Резервная модель)\n{resp.text}"
            except Exception as g_err:
                logger.error(f"Gemini doc fallback also failed: {g_err}")

        return f"Текст извлечен, но AI-анализ недоступен.\n\nНачало текста:\n{text_content[:500]}..."

    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        return f"Ошибка при анализе документа: {e}"

def process_link(url: str) -> str:
    """For social media: yt-dlp metadata. For general web: trafilatura text extraction. Returns structured summary."""
    try:
        social_domains = ['instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'facebook.com', 'reddit.com']
        is_social = any(domain in url.lower() for domain in social_domains)

        if is_social:
            return _extract_via_ytdlp(url)
        else:
            return _extract_via_trafilatura(url)
    except Exception as e:
        logger.error(f"Link processing failed: {e}")
        return f"Ошибка при обработке ссылки: {e}"

def _extract_via_ytdlp(url: str) -> str:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'ignoreerrors': True,
        'extract_flat': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return _extract_via_trafilatura(url)
                
            title = info.get('title') or info.get('fulltitle') or 'Social Media Post'
            description = info.get('description') or ''
            uploader = info.get('uploader') or info.get('channel') or 'Unknown'
            
            content = f"📱 Социальные медиа: {url}\n"
            content += f"👤 Автор: {uploader}\n"
            content += f"📄 Заголовок: {title}\n\n"
            content += f"📝 Описание: {description[:1500]}"
            
            return content
    except Exception as e:
        logger.warning(f"yt-dlp failed, falling back to trafilatura: {e}")
        return _extract_via_trafilatura(url)

def _extract_via_trafilatura(url: str) -> str:
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(downloaded, include_comments=False)
            metadata = trafilatura.extract_metadata(downloaded)
            title = metadata.title if metadata and metadata.title else "Web Article"
            
            content = f"🌐 Веб-страница: {url}\n"
            content += f"📄 Заголовок: {title}\n\n"
            
            if result:
                content += f"📝 Содержимое:\n{result[:3000]}..."
            else:
                content += "Не удалось извлечь текстовое содержимое."
                
            return content
        return "Не удалось скачать страницу (возможно, защита от ботов)."
    except Exception as e:
        return f"Ошибка извлечения веб-страницы: {e}"
