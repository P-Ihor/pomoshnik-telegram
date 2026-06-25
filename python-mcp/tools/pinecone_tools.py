import json
import logging
from config import settings

logger = logging.getLogger(__name__)

# Initialize Pinecone and SentenceTransformer lazily to save startup memory
pc = None
index = None
embedder = None

def _init_pinecone():
    global pc, index, embedder
    if not settings.PINECONE_API_KEY:
        return False
        
    try:
        if pc is None:
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            index = pc.Index(settings.PINECONE_INDEX_NAME)
        if embedder is None:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        return True
    except Exception as e:
        logger.error(f"Pinecone init failed: {e}")
        return False

def search_memory(query: str, top_k: int = 5) -> str:
    """Embeds query with sentence-transformers, searches Pinecone."""
    if not _init_pinecone():
        return "Pinecone не настроен (отсутствует PINECONE_API_KEY). Используйте встроенную память (MEMORY.md)."
        
    try:
        vector = embedder.encode(query).tolist()
        results = index.query(vector=vector, top_k=top_k, include_metadata=True)
        
        if not results.matches:
            return "Ничего не найдено в Pinecone."
            
        output = [f"Найдено {len(results.matches)} результатов:"]
        for match in results.matches:
            score = match.score
            meta = match.metadata or {}
            text = meta.get('text', '[Без текста]')
            output.append(f"- (Score: {score:.2f}) {text}")
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Pinecone search failed: {e}")
        return f"Ошибка поиска в Pinecone: {e}"

def save_to_memory(text: str, metadata_json: str = '{}') -> str:
    """Embeds text, upserts to Pinecone with metadata."""
    if not _init_pinecone():
        return "Pinecone не настроен. Сохраните это в MEMORY.md."
        
    try:
        import uuid
        vector = embedder.encode(text).tolist()
        
        try:
            metadata = json.loads(metadata_json)
        except json.JSONDecodeError:
            metadata = {}
            
        metadata['text'] = text
        record_id = str(uuid.uuid4())
        
        index.upsert(vectors=[(record_id, vector, metadata)])
        return f"Успешно сохранено в Pinecone (ID: {record_id})."
    except Exception as e:
        logger.error(f"Pinecone save failed: {e}")
        return f"Ошибка сохранения в Pinecone: {e}"

def get_memory_stats() -> str:
    """Returns Pinecone index stats."""
    if not _init_pinecone():
        return "Pinecone не настроен."
        
    try:
        stats = index.describe_index_stats()
        return f"Статистика Pinecone:\nВсего векторов: {stats.total_vector_count}\nПространства имен: {stats.namespaces}"
    except Exception as e:
        logger.error(f"Pinecone stats failed: {e}")
        return f"Ошибка получения статистики Pinecone: {e}"
