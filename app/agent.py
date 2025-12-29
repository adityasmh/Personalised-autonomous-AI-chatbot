from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage


@tool
def route_to_sql_agent() -> str:
    """Route the user's request to the SQL agent for execution."""
    return "route_to_sql_agent"

@tool
def route_to_synthesis_agent() -> str:
    """Route the user's request for a direct conversational response."""
    return "route_to_synthesis_agent"
    from langchain_core.messages import SystemMessage, HumanMessage

def chief_router_node(state: AgentState):
    print("--- 🧠 CHIEF ROUTER ---")
    router_tools = [route_to_sql_agent, route_to_synthesis_agent]
    llm_with_router_tools = llm.bind_tools(router_tools)

    prompt = (
        "You are a router.\n"
        "Call route_to_sql_agent ONLY if the user is asking about database data, tables, columns, counts, lists, joins, etc.\n"
        "Call route_to_synthesis_agent for greetings, chit-chat, or non-database questions.\n"
        "Return a tool call, not normal text."
    )

    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f'User message: {state["messages"][-1].content}'),
    ]
    response = llm_with_router_tools.invoke(messages)
    return {"messages": [response]}
def route_logic(state: AgentState):
    msg = state["messages"][-1]
    if getattr(msg, "tool_calls", None):
        name = msg.tool_calls[0].get("name")
        if name == "route_to_sql_agent":
            print("--- ROUTE: Decided to go to SQL Agent ---")
            return "tool_agent"
    # fallback
    print("--- ROUTE: Decided to go to Synthesis Agent ---")
    return "synthesis_agent"
def tool_agent_has_tool_call(state: AgentState):
    msg = state["messages"][-1]
    if getattr(msg, "tool_calls", None):
        return "tool_executor"
    return "synthesis_agent"
workflow.add_conditional_edges(
    "tool_agent",
    tool_agent_has_tool_call,
    {
        "tool_executor": "tool_executor",
        "synthesis_agent": "synthesis_agent",
    },
)
def custom_tool_executor(state: AgentState):
    print("--- 🛡️ VALIDATING AND EXECUTING SQL ---")
    try:
        last_message = state["messages"][-1]
        if not getattr(last_message, "tool_calls", None):
            return {"messages": [ToolMessage(content="[TOOL_ERROR] No tool call found.", tool_call_id="error")]}

        # Find the sql_database_tool call if present
        sql_call = None
        for tc in last_message.tool_calls:
            if tc.get("name") == "sql_database_tool":
                sql_call = tc
                break

        if not sql_call:
            return {"messages": [ToolMessage(content="[TOOL_ERROR] Expected sql_database_tool call, but none found.", tool_call_id="error")]}

        tool_input = sql_call.get("args", {}) or {}
        original_sql_query = tool_input.get("query")
        if not original_sql_query:
            return {"messages": [ToolMessage(content="[TOOL_ERROR] Tool call missing 'query'.", tool_call_id=sql_call.get("id", "error"))]}

        print(f"Original Query from LLM: {original_sql_query}")

        schema_identifiers = get_schema_identifiers(DB_CONFIG)
        cased_identifiers = get_cased_identifiers(schema_identifiers)
        corrected_sql_query = fix_sql_casing(original_sql_query, cased_identifiers)
        print(f"Corrected Query for Execution: {corrected_sql_query}")

        raw_result = sql_database_tool.invoke({"query": corrected_sql_query})

        tool_message = ToolMessage(content=str(raw_result), tool_call_id=sql_call.get("id", "sql_database_tool"))

        return {
            "messages": [tool_message],
            "sql_query_for_log": original_sql_query,
            "corrected_sql_query_for_log": corrected_sql_query,
            "raw_tool_output_for_log": str(raw_result),
        }

    except Exception as e:
        print(f"[ERROR] in custom_tool_executor: {e}")
        return {"messages": [ToolMessage(content=f"[TOOL_ERROR] Could not execute tool: {e}", tool_call_id="error")]}


