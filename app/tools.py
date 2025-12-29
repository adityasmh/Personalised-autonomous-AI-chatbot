# tools.py
import json
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from config import DB_CONFIG, chroma_collection

# Allow SELECT or WITH ... SELECT only. Block multi-statement and writes.
READONLY_RE = re.compile(r"^\s*(with\b[\s\S]*?\bselect\b|select\b)", re.IGNORECASE)

BLOCKLIST_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|merge|call|execute|do)\b",
    re.IGNORECASE,
)

def _is_readonly_single_statement(sql: str) -> bool:
    s = sql.strip()
    # Block internal semicolons (multi-statement). Allow trailing semicolon only.
    if ";" in s.rstrip(";"):
        return False
    if BLOCKLIST_RE.search(s):
        return False
    return bool(READONLY_RE.match(s))

@tool
def sql_database_tool(query: str) -> str:
    """
    Executes a READ-ONLY SQL query (SELECT / WITH ... SELECT) and returns JSON.
    """
    if not _is_readonly_single_statement(query):
        return "[SQL_ERROR] Only single-statement, read-only SELECT queries are allowed."

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG, connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "5")))
        conn.set_session(readonly=True, autocommit=True)

        # RealDictCursor returns dict rows directly
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)

            if cur.description:
                rows = cur.fetchall()  # list[dict]
                if not rows:
                    return json.dumps({"rows": [], "message": "Query executed successfully, but returned no results."})
                return json.dumps({"rows": rows})
            return json.dumps({"rows": [], "message": "Query executed successfully (no rows)."})
    except Exception as e:
        return f"[SQL_ERROR] {e}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

@tool
def vector_store_retrieval_tool(query: str) -> str:
    """
    Retrieves relevant schema/context from the vector store.
    """
    try:
        results = chroma_collection.query(query_texts=[query], n_results=1)
        documents = results.get("documents", [[]])[0]
        if documents:
            return documents[0]
        return "[VECTOR_STORE] No specific schema information found for that query."
    except Exception as e:
        return f"[VECTOR_STORE_ERROR] {e}"
