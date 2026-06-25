import logging
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY
) if settings.OPENROUTER_API_KEY else None

def smart_analyze(text: str, complexity: str = 'auto') -> str:
    """Routes to cheap or smart model based on complexity. 
    If 'auto': uses cheap model to classify, then routes. 
    Complexities: 'simple' (Gemini Flash), 'complex' (Claude Sonnet), 'auto' (detect)."""
    
    if not openrouter_client:
        return "Ошибка: Отсутствует OPENROUTER_API_KEY."
        
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
        logger.error(f"Smart routing failed: {e}")
        return f"Ошибка при маршрутизации запроса: {e}"
