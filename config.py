"""
config.py — Configuración centralizada de Billy AI Agent
Carga variables desde .env y define constantes del sistema.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Rutas base ───────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", str(BASE_DIR / "vector_store")))
CONVERSATIONS_DIR = Path(os.getenv("CONVERSATIONS_DIR", str(DATA_DIR / "conversations")))
UPLOADED_KNOWLEDGE_DIR = Path(os.getenv("UPLOADED_KNOWLEDGE_DIR", str(DATA_DIR / "uploaded_knowledge")))

for d in [DATA_DIR, VECTOR_STORE_DIR, CONVERSATIONS_DIR, UPLOADED_KNOWLEDGE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Ollama (Motor de IA local) ──────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_AVAILABLE_MODELS = [
    "deepseek-r1:8b",
    "llama3.1:8b",
]

# ─── Tokens ────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

# ─── Embeddings para RAG ──────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ─── Base de datos ────────────────────────────────────────
MEMORY_DB = os.getenv("MEMORY_DB", str(DATA_DIR / "memory.db"))
KNOWLEDGE_FILE = Path(os.getenv("KNOWLEDGE_FILE", str(BASE_DIR / "knowledge.json")))
PERSONALIDAD_FILE = Path(os.getenv("PERSONALIDAD_FILE", str(BASE_DIR / "personalidad.md")))
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", str(BASE_DIR / "prompts")))

# ─── Parámetros del modelo ────────────────────────────────
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

# ─── Logging ──────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Voz (opcional) ───────────────────────────────────────
VOICE_ENABLED = os.getenv("VOICE_ENABLED", "false").lower() == "true"
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "es")
VOICE_GENDER = os.getenv("VOICE_GENDER", "female")
VOICE_RATE = os.getenv("VOICE_RATE", "+0%")
VOICE_MAX_CHARS = int(os.getenv("VOICE_MAX_CHARS", "3000"))
ASR_MODEL = os.getenv("ASR_MODEL", "openai/whisper-large-v3")
VOICE_AUTO_REPLY = os.getenv("VOICE_AUTO_REPLY", "false").lower() == "true"

VOICE_TEMP_DIR = DATA_DIR / "voice_temp"
VOICE_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def validate_config():
    """Valida que la configuración mínima esté presente."""
    errors = []

    if not TELEGRAM_BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN no configurado. Obtén uno de @BotFather en Telegram.")

    if not KNOWLEDGE_FILE.exists():
        errors.append(f"Archivo knowledge.json no encontrado en {KNOWLEDGE_FILE}")

    if not PERSONALIDAD_FILE.exists():
        errors.append(f"Archivo personalidad.md no encontrado en {PERSONALIDAD_FILE}")

    if not PROMPTS_DIR.exists():
        errors.append(f"Directorio prompts no encontrado en {PROMPTS_DIR}")

    return errors
