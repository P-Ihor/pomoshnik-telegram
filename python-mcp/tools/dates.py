import logging
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
) if settings.OPENROUTER_API_KEY else None

def extract_dates_and_events(text: str) -> str:
    """Uses LLM to extract dates, birthdays, deadlines, meetings from natural text. 
    Returns JSON with extracted events, suggested reminder times."""
    
    if not openrouter_client:
        return '{"error": "OpenRouter API key missing. Cannot extract dates."}'

    prompt = """
    Ты - система извлечения дат и событий из текста.
    Найди в тексте любые упоминания событий, встреч, дней рождений, сроков, покупок на определенную дату.
    Если дат/событий нет, верни пустой список events: [].
    
    Верни ТОЛЬКО валидный JSON в формате:
    {
        "events": [
            {
                "title": "Название события (например: День рождения мамы)",
                "date_mentioned": "Как это было сказано в тексте (например: 15 марта)",
                "type": "birthday|meeting|deadline|reminder",
                "suggested_reminder_cron": "Предложенное выражение cron для напоминания (если возможно, иначе null)",
                "description": "Дополнительный контекст"
            }
        ]
    }
    
    Текст пользователя:
    """
    
    try:
        response = openrouter_client.chat.completions.create(
            model=settings.MODEL_CHEAP,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        # Sometimes LLMs add markdown blocks like ```json ... ```, strip them
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return content.strip()
        
    except Exception as e:
        logger.error(f"Date extraction failed: {e}")
        return f'{{"error": "{str(e)}"}}'
