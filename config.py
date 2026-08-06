"""
Configuration settings for the Financial Document AI Assistant
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
VECTOR_DB_PATH = BASE_DIR / "vector_db"
UPLOAD_DIR = BASE_DIR / "uploads"

# Create directories if they don't exist
VECTOR_DB_PATH.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# API Configuration
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")
UPSTAGE_API_URL = "https://api.upstage.ai/v1/solar"

# Document Processing Configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))

# Streamlit Configuration
PAGE_TITLE = "금융상품 약관 AI 도우미"
PAGE_ICON = "🏦"
LAYOUT = "wide"
