import psycopg2
from typing import Dict, List

# --- CONVERSATION HISTORY FUNCTIONS (Used by UI) ---

def initialize_conversation_history_table(db_config: Dict[str, str]):
    """Initializes the simple conversation_history table."""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                speaker VARCHAR(10) NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Error initializing conversation history table: {e}")

def add_to_conversation_history(db_config: Dict[str, str], speaker: str, message: str):
    """Adds a message to the simple conversation_history table."""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversation_history (speaker, message) VALUES (%s, %s);",
            (speaker, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Error adding message to conversation history: {e}")

def get_recent_conversation_history(db_config: Dict[str, str], limit: int = 10) -> str:
    """Retrieves recent messages for the agent's context string."""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(
            "SELECT speaker, message FROM conversation_history ORDER BY timestamp DESC LIMIT %s;",
            (limit,)
        )
        rows = cur.fetchall()
        conn.close()
        history_list = [f"{speaker}: {message}" for speaker, message in reversed(rows)]
        return "\n".join(history_list)
    except Exception as e:
        print(f"[ERROR] Error retrieving conversation history: {e}")
        return ""


# --- SCHEMA AND IDENTIFIER FUNCTIONS (Used by Agent and Validator) ---

def get_schema_identifiers(db_config: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Retrieves all table and column names from the database, structured for the validator.
    Returns a dictionary with 'tables' and 'columns' keys.
    """
    identifiers = {"tables": [], "columns": []}
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        # Get all table names from the public schema
        cur.execute("""
            SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname = 'public';
        """)
        tables = [row[0] for row in cur.fetchall()]
        identifiers["tables"] = tables

        all_columns = []
        # Get all column names from those tables
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public';
        """)
        columns = [row[0] for row in cur.fetchall()]

        # Get a unique list of all column names
        identifiers["columns"] = list(set(columns))

        conn.close()
        return identifiers
    except Exception as e:
        print(f"[ERROR] Error fetching schema identifiers: {e}")
        return identifiers


# --- COMPREHENSIVE LOGGING FUNCTIONS (UPDATED) ---

def initialize_comprehensive_log_table(db_config: dict):
    """Initializes the comprehensive_agent_logs table with the new corrected query column."""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comprehensive_agent_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                user_query TEXT,
                sql_query_generated TEXT,
                raw_tool_output TEXT,
                final_agent_response TEXT
            );
        """)
        conn.commit()
        # Add the new column for the corrected query if it doesn't exist (for backward compatibility)
        cur.execute("""
            ALTER TABLE comprehensive_agent_logs 
            ADD COLUMN IF NOT EXISTS sql_query_corrected TEXT;
        """)
        conn.commit()
        conn.close()
        print("Comprehensive agent logs table initialized or already exists.")
    except Exception as e:
        print(f"Error initializing comprehensive agent logs table: {e}")


def add_to_comprehensive_log(db_config: dict, user_query: str, final_response: str, sql_query: str = None, corrected_sql_query: str = None, raw_tool_output: str = None):
    """Adds a structured log entry, including the corrected query, to the comprehensive_agent_logs table."""
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO comprehensive_agent_logs (user_query, sql_query_generated, sql_query_corrected, raw_tool_output, final_agent_response) 
               VALUES (%s, %s, %s, %s, %s);""",
            (user_query, sql_query, corrected_sql_query, raw_tool_output, final_response)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error adding to comprehensive agent logs: {e}")