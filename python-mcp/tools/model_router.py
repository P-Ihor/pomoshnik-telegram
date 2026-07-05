import logging
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
) if settings.OPENROUTER_API_KEY else None

# Gemini fallback (бесплатный)
_gemini_model = None

def _get_gemini_fallback():
    global _gemini_model
    if _gemini_model is None and settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            _gemini_model = genai.GenerativeModel('gemini-2.0-flash-001')
        except Exception as e:
            logger.error(f"Gemini fallback init failed: {e}")
    return _gemini_model


def _try_gemini_fallback(text: str) -> str:
    """Попытка ответить через бесплатный Gemini, если OpenRouter недоступен."""
    fallback = _get_gemini_fallback()
    if fallback:
        try:
            resp = fallback.generate_content(
                f"Ты — Помощник, личный AI-ассистент. Отвечай на русском языке.\n\n{text}"
            )
            return f"⚠️ (Резервная модель Gemini)\n{resp.text}"
        except Exception as e2:
            logger.error(f"Gemini fallback also failed: {e2}")
            return f"❌ Обе модели недоступны. OpenRouter и Gemini выдали ошибки."
    return None


def smart_analyze(text: str, complexity: str = 'auto') -> str:
    """Routes to cheap or smart model based on complexity. 
    If 'auto': uses cheap model to classify, then routes. 
    Complexities: 'simple' (Gemini Flash), 'complex' (Claude Sonnet), 'auto' (detect).
    Falls back to free Gemini API if OpenRouter fails."""
    
    if not openrouter_client:
        # Нет OpenRouter — сразу пробуем Gemini
        result = _try_gemini_fallback(text)
        if result:
            return result
        return "Ошибка: Отсутствуют API ключи (OPENROUTER_API_KEY и GOOGLE_API_KEY)."
        
    try:
        model_to_use = settings.MODEL_CHEAP
        
        if complexity == 'complex':
            model_to_use = settings.MODEL_SMART
        elif complexity == 'auto':
            # Quick check to see if it needs smart model
            decision_response = openrouter_client.chat.completions.create(
                model=settings.MODEL_CHEAP,
                messages=[
                    {"role": "system", "content": "Reply ONLY with 'simple' or 'complex'. Is this prompt asking for deep reasoning, heavy coding, or complex logic?"},
                    {"role": "user", "content": text[:500]} # only check beginning to save tokens
                ],
                temperature=0.1
            )
            decision = decision_response.choices[0].message.content.strip().lower()
            if 'complex' in decision:
                model_to_use = settings.MODEL_SMART
                
        logger.info(f"Routing to model: {model_to_use}")
        
        response = openrouter_client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": "Ты Помощник. Отвечай на русском языке."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
        
    except Exception as e:
        logger.warning(f"OpenRouter failed ({e}), trying Gemini fallback...")
        result = _try_gemini_fallback(text)
        if result:
            return result
        return f"Ошибка при маршрутизации запроса: {e}"
