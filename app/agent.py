# agent.py (complete updated version)
import operator
from typing import TypedDict, Annotated, List

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    SystemMessage,
    AIMessage,
    HumanMessage,
)

from config import llm, DB_CONFIG
from tools import sql_database_tool
from database_utils import (
    initialize_comprehensive_log_table,
    add_to_comprehensive_log,
    get_schema_identifiers,
)
from sql_validator import get_cased_identifiers, fix_sql_casing


# --- Agent State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    history: str
    error_count: int
    user_query_for_log: str
    sql_query_for_log: str
    corrected_sql_query_for_log: str
    raw_tool_output_for_log: str


# --- Router Tools (NO REQUIRED ARGS) ---
@tool
def route_to_sql_agent() -> str:
    """Route the user's request to the SQL agent for execution."""
    return "route_to_sql_agent"


@tool
def route_to_synthesis_agent() -> str:
    """Route the user's request for a direct conversational response."""
    return "route_to_synthesis_agent"


# --- Nodes ---

def capture_user_query(state: AgentState):
    """Starting node to capture the user's query for logging."""
    print("--- CAPTURING USER QUERY FOR LOG ---")
    if state.get("messages"):
        state["user_query_for_log"] = state["messages"][-1].content
    return state


def chief_router_node(state: AgentState):
    """Router to decide between querying the database or simple conversation."""
    print("--- 🧠 CHIEF ROUTER ---")

    router_tools = [route_to_sql_agent, route_to_synthesis_agent]
    llm_with_router_tools = llm.bind_tools(router_tools)

    system_prompt = (
        "You are a router.\n"
        "Call route_to_sql_agent ONLY if the user is asking about database data "
        "(tables, columns, counts, lists, joins, filters, aggregations).\n"
        "Call route_to_synthesis_agent for greetings, chit-chat, or non-database questions.\n"
        "You MUST respond by calling exactly one tool."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["messages"][-1].content),
    ]

    response = llm_with_router_tools.invoke(messages)
    return {"messages": [response]}


def route_logic(state: AgentState):
    """Routes based on the tool call from the chief_router."""
    msg = state["messages"][-1]
    if getattr(msg, "tool_calls", None):
        name = msg.tool_calls[0].get("name")
        if name == "route_to_sql_agent":
            print("--- ROUTE: SQL AGENT ---")
            return "tool_agent"

    print("--- ROUTE: SYNTHESIS AGENT ---")
    return "synthesis_agent"


def tool_calling_agent(state: AgentState):
    """
    Generates the SQL query using the detailed schema prompt.
    """
    print("--- 👨‍🏫 SQL QUERY GENERATOR ---")
    tools_to_bind = [sql_database_tool]
    llm_with_tools = llm.bind_tools(tools_to_bind)

    # NOTE: keep your long schema prompt if you want; shortened here for brevity.
    # Replace this system_prompt with your full schema guide.
    system_prompt = (
        "You are a hyper-attentive SQL query analyst for PostgreSQL.\n"
        "Return a tool call to sql_database_tool with args: {\"query\": \"...\"}.\n"
        "Only generate a single SELECT query.\n"
        "Use correct table/column casing exactly as specified by the schema.\n"
    )

    messages_for_llm = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm_with_tools.invoke(messages_for_llm)

    # Return the model response (may include tool_calls)
    return {"messages": [response]}


def tool_agent_has_tool_call(state: AgentState):
    """After SQL generation: only go to executor if a tool call exists."""
    msg = state["messages"][-1]
    if getattr(msg, "tool_calls", None):
        return "tool_executor"
    return "synthesis_agent"


def custom_tool_executor(state: AgentState):
    """
    Intercepts the generated SQL, validates and corrects casing issues,
    and then executes the corrected query.
    """
    print("--- 🛡️ VALIDATING AND EXECUTING SQL ---")
    try:
        last_message = state["messages"][-1]
        if not getattr(last_message, "tool_calls", None):
            return {
                "messages": [
                    ToolMessage(content="[TOOL_ERROR] No tool call found.", tool_call_id="error")
                ]
            }

        # Find the sql_database_tool call (in case multiple tool calls exist)
        sql_call = None
        for tc in last_message.tool_calls:
            if tc.get("name") == "sql_database_tool":
                sql_call = tc
                break

        if not sql_call:
            return {
                "messages": [
                    ToolMessage(
                        content="[TOOL_ERROR] Expected sql_database_tool call, but none found.",
                        tool_call_id="error",
                    )
                ]
            }

        tool_input = sql_call.get("args", {}) or {}
        original_sql_query = tool_input.get("query")
        if not original_sql_query:
            return {
                "messages": [
                    ToolMessage(
                        content="[TOOL_ERROR] Tool call missing 'query'.",
                        tool_call_id=sql_call.get("id", "error"),
                    )
                ]
            }

        print(f"Original Query from LLM: {original_sql_query}")

        schema_identifiers = get_schema_identifiers(DB_CONFIG)
        cased_identifiers = get_cased_identifiers(schema_identifiers)
        corrected_sql_query = fix_sql_casing(original_sql_query, cased_identifiers)

        print(f"Corrected Query for Execution: {corrected_sql_query}")

        raw_result = sql_database_tool.invoke({"query": corrected_sql_query})

        tool_message = ToolMessage(
            content=str(raw_result),
            tool_call_id=sql_call.get("id", "sql_database_tool"),
        )

        return {
            "messages": [tool_message],
            "sql_query_for_log": original_sql_query,
            "corrected_sql_query_for_log": corrected_sql_query,
            "raw_tool_output_for_log": str(raw_result),
        }

    except Exception as e:
        print(f"[ERROR] in custom_tool_executor: {e}")
        return {
            "messages": [
                ToolMessage(content=f"[TOOL_ERROR] Could not execute tool: {e}", tool_call_id="error")
            ]
        }


def synthesis_agent(state: AgentState):
    """
    Formats the final output and shows the corrected SQL query used.
    This keeps your existing approach (LLM formats table), but now router/executor are stable.
    """
    print("--- ✍️ SYNTHESIS AGENT ---")
    sql_query = state.get("corrected_sql_query_for_log") or state.get("sql_query_for_log", "No SQL query was run.")

    synthesis_prompt = f"""You are an expert data presentation assistant.

UNBREAKABLE RULES:
1) Start with this exact dropdown:
<details><summary>View Executed SQL Query</summary>```sql
{sql_query}
```</details>

2) Look at the most recent ToolMessage output in the context:
- If it is a JSON-like list/dicts with multiple rows, output a Markdown table.
- If a single row/value, output a sentence.
- If it contains [SQL_ERROR] or [TOOL_ERROR], apologize and ask to rephrase.

Conversation Context:
{state["messages"]}
"""

    response = llm.invoke(synthesis_prompt)
    return {"messages": [AIMessage(content=response.content)]}


def log_interaction_node(state: AgentState):
    """Final node to log the entire interaction."""
    print("--- 📝 LOGGING INTERACTION ---")
    add_to_comprehensive_log(
        db_config=DB_CONFIG,
        user_query=state.get("user_query_for_log"),
        sql_query=state.get("sql_query_for_log"),
        corrected_sql_query=state.get("corrected_sql_query_for_log"),
        raw_tool_output=state.get("raw_tool_output_for_log"),
        final_response=state["messages"][-1].content,
    )
    return state


# --- Graph Assembly ---
def get_agent_app():
    """Configures and compiles the agentic graph."""
    print("--- Configuring and Compiling Agentic Graph ---")
    initialize_comprehensive_log_table(DB_CONFIG)

    workflow = StateGraph(AgentState)

    workflow.add_node("capture_user_query", capture_user_query)
    workflow.add_node("chief_router", chief_router_node)
    workflow.add_node("tool_agent", tool_calling_agent)
    workflow.add_node("tool_executor", custom_tool_executor)
    workflow.add_node("synthesis_agent", synthesis_agent)
    workflow.add_node("log_interaction_node", log_interaction_node)

    workflow.set_entry_point("capture_user_query")
    workflow.add_edge("capture_user_query", "chief_router")

    workflow.add_conditional_edges(
        "chief_router",
        route_logic,
        {
            "tool_agent": "tool_agent",
            "synthesis_agent": "synthesis_agent",
        },
    )

    # IMPORTANT: conditional after tool_agent
    workflow.add_conditional_edges(
        "tool_agent",
        tool_agent_has_tool_call,
        {
            "tool_executor": "tool_executor",
            "synthesis_agent": "synthesis_agent",
        },
    )

    workflow.add_edge("tool_executor", "synthesis_agent")
    workflow.add_edge("synthesis_agent", "log_interaction_node")
    workflow.add_edge("log_interaction_node", END)

    app = workflow.compile()
    print("✅ Agentic system compiled and ready.")
    return app
