# tools.py
import psycopg2
from langchain_core.tools import tool
from config import DB_CONFIG, chroma_collection

@tool
def sql_database_tool(query: str) -> str:
    """
    Executes a read-only SQL query against the PostgreSQL database and returns the result.
    Use this tool to answer questions about data in the database.
    Example queries:
    'SELECT COUNT(*) FROM students;'
    'SELECT gender, AVG(math_score) FROM performance JOIN students ON performance.student_id = students.student_id GROUP BY gender;'
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)

        if cur.description:
            rows = cur.fetchall()
            headers = [desc[0] for desc in cur.description]
            results = [dict(zip(headers, row)) for row in rows]
            conn.close()
            if not results:
                return "[DATABASE] Query executed successfully, but returned no results."
            return str(results)
        else:

            conn.commit()
            conn.close()
            return f"[DATABASE] Non-SELECT query executed successfully. {cur.rowcount} rows affected."
    except Exception as e:
        return f"[SQL_ERROR] {e}"

@tool
def vector_store_retrieval_tool(query: str) -> str:
    """
    Retrieves relevant context, examples, or database schema information from the vector store.
    Use this to get information about table structures, column names, or how to use the system.
    For example: 'What are the columns in the students table?' or 'Describe the course table.'
    """
    try:
        results = chroma_collection.query(query_texts=[query], n_results=1)
        documents = results.get("documents", [[]])[0]
        if documents:
            return documents[0]
        else:
            return "[VECTOR_STORE] No specific schema information found for that query."
    except Exception as e:
        return f"[VECTOR_STORE_ERROR] {e}"