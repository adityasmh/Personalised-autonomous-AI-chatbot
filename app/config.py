# config.py
import os
import warnings
import chromadb
from google.api_core import exceptions
from langchain_google_genai import ChatGoogleGenerativeAI

# ─────────────────────────────────────────────
# Configurations
# ─────────────────────────────────────────────

DB_CONFIG = {
    "dbname": "educational_datasets",
    "user": "postgres",
    "password": "adi123",
    "host": "localhost",
    "port": "5432",
}

# Suppress the specific UserWarning about ADC credentials without a quota project
warnings.filterwarnings("ignore", category=UserWarning, module="google.auth._default")

# --- ChromaDB Client ---
try:
    chroma_db_path = "/tmp/chromadb_storage"
    os.makedirs(chroma_db_path, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=chroma_db_path)
    chroma_collection = chroma_client.get_or_create_collection("database_schema")
    print(f"ChromaDB client initialized using persistent storage at: {chroma_db_path}")
except Exception as e:
    print(f"🚨 Error initializing ChromaDB client: {e}")
    chroma_client = chromadb.Client()  # Fallback to in-memory
    chroma_collection = chroma_client.get_or_create_collection("database_schema")
    print("Falling back to in-memory ChromaDB.")


# --- LLM Initialization ---
try:
    google_api_key = os.environ.get("PASTE YOUR API KEY HERE (GEMINI IS PREFFERED)")
    if not google_api_key:
        print("Warning: GOOGLE_API_KEY environment variable not set. Using a placeholder.")
        # Replace with your actual key if not set as an environment variable
        google_api_key = "YOUR API KEY"

    llm = ChatGoogleGenerativeAI(model="whatever model u decide to go with", temperature=0.1, google_api_key=google_api_key)
    llm.invoke("Test message.")  # Test API key
    print("Google Generative AI model loaded successfully.")
except exceptions.PermissionDenied as e:
    print(f"🚨 Google API Permission Denied: {e}. Check your API key and project permissions.")
    exit()
except Exception as e:
    print(f"🚨 An unexpected error occurred during LLM initialization: {e}")
    exit()