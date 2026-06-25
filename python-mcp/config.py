import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class Settings:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "telegram-memory")
    
    MODEL_CHEAP = os.getenv("MODEL_CHEAP", "google/gemini-2.0-flash-001")
    MODEL_SMART = os.getenv("MODEL_SMART", "anthropic/claude-3-5-sonnet")
    MODEL_VISION = os.getenv("MODEL_VISION", "google/gemini-2.0-flash-001")
    
    BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "ru")

settings = Settings()

if not settings.GOOGLE_API_KEY:
    logging.warning("GOOGLE_API_KEY is missing. Vision tools will fail.")
if not settings.OPENROUTER_API_KEY:
    logging.warning("OPENROUTER_API_KEY is missing. Smart routing will fail.")
if not settings.PINECONE_API_KEY:
    logging.warning("PINECONE_API_KEY is missing. Pinecone tools will return errors.")
