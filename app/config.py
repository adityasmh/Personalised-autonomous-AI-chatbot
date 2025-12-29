# config.py
import os
import warnings
import chromadb
from google.api_core import exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

# Suppress the specific UserWarning about ADC credentials without a quota project
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth._default")

def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"{name} is not set")
    return val

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "educational_datasets"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": _require_env("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}

# --- ChromaDB Client ---
try:
    chroma_db_path = os.environ.get("CHROMA_PATH", "/tmp/chromadb_storage")
    os.makedirs(chroma_db_path, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection("database_schema")
    print(f"ChromaDB client initialized using persistent storage at: {chroma_db_path}")
except Exception as e:
    print(f"🚨 Error initializing ChromaDB client: {e}")
    chroma_client = chromadb.Client()  # fallback to in-memory
    chroma_collection = chroma_client.get_or_create_collection("database_schema")
    print("Falling back to in-memory ChromaDB.")

# --- LLM Initialization ---
try:
    google_api_key = _require_env("GOOGLE_API_KEY")
    model_name = os.environ.get("GOOGLE_MODEL", "gemini-1.5-pro")  # change if needed

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.1,
        google_api_key=google_api_key,
    )
    print("Google Generative AI model loaded successfully.")
except exceptions.PermissionDenied as e:
    raise RuntimeError(f"Google API Permission Denied: {e}. Check your API key and project permissions.") from e
except Exception as e:
    raise RuntimeError(f"Unexpected error during LLM initialization: {e}") from e
