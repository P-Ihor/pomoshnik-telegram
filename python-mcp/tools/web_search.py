import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def perform_web_search(query: str, max_results: int = 5) -> str:
    """Ищет информацию в интернете (через DuckDuckGo).
    Возвращает найденные результаты, включая ссылки и фрагменты текста.
    Используй это, когда тебе нужно узнать актуальные новости, цены, инструкции или найти специфичную информацию.
    """
    try:
        results = []
        with DDGS() as ddgs:
            # text() generator yields dicts like: {'title': '...', 'href': '...', 'body': '...'}
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)
        
        if not results:
            return f"Ничего не найдено по запросу: {query}"
            
        output = f"Результаты поиска по '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'Без названия')
            href = res.get('href', '#')
            body = res.get('body', '')
            output += f"{i}. {title}\nURL: {href}\nSnippet: {body}\n\n"
            
        return output
    except Exception as e:
        logger.error(f"Web search failed for query '{query}': {e}")
        return f"Ошибка при поиске в интернете: {e}"
