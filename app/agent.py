from langchain_core.tools import tool

@tool
def route_to_sql_agent() -> str:
    """Route the user's request to the SQL agent for execution."""
    return "route_to_sql_agent"

@tool
def route_to_synthesis_agent() -> str:
    """Route the user's request for a direct conversational response."""
    return "route_to_synthesis_agent"
