# ui.py
import time
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from agent import get_agent_app
from config import DB_CONFIG
from database_utils import (
    initialize_conversation_history_table,
    add_to_conversation_history,
    get_recent_conversation_history,
)

# --- 1) PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ADK-MCP Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2) SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user"|"assistant", "content": "..."}]

# --- 3) UI STYLING & SIDEBAR ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Poppins', sans-serif; }
    .st-emotion-cache-1jicfl2 { background-color: #F0F2F6; }

    [data-testid="stChatMessage"] {
        border-radius: 20px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border: 1px solid transparent;
    }
    [data-testid="stChatMessage"]:has(div[data-testid="stAvatarIcon-user"]) {
        background-color: #E9F5FF;
        border-color: #B9D7F1;
    }
    [data-testid="stChatMessage"]:has(div[data-testid="stAvatarIcon-assistant"]) {
        background-color: #FFFFFF;
        border-color: #E6EAF1;
    }
    .header {
        font-size: 2.5rem;
        font-weight: 700;
        padding: 1.5rem 0;
        margin-bottom: 1rem;
        color: #2c3e50;
        text-align: center;
        background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    [data-testid="stChatInput"] {
        background-color: #FFFFFF;
        border-radius: 15px;
        border: 1px solid #E6EAF1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    }
</style>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("🤖 your Agent")
    st.markdown("---")
    st.subheader("💡 Try asking:")
    st.info("What are the names of all departments?")
    st.info("Give me the names and hometowns of all the teachers.")
    st.info("How many students are enrolled in each degree program?")

# --- 4) APP INITIALIZATION ---
@st.cache_resource
def initialize_system():
    # Ensure history table exists before any reads/writes
    initialize_conversation_history_table(DB_CONFIG)
    return get_agent_app()

agent_app = initialize_system()

# --- 5) OPTIONAL STREAMING ---
def stream_response(text: str):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)

# --- 6) MAIN CHAT INTERFACE ---
st.markdown('<p class="header">Chat with your Database</p>', unsafe_allow_html=True)

# Display past messages
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Handle new user input
prompt = st.chat_input("Ask your database a question...")
if prompt:
    # show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # build messages for agent
    messages_for_agent = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            messages_for_agent.append(HumanMessage(content=msg["content"]))
        else:
            messages_for_agent.append(AIMessage(content=msg["content"]))

    # fetch recent conversation history string (DB-backed)
    history_str = get_recent_conversation_history(DB_CONFIG, limit=10)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Agent is thinking..."):
            try:
                final_state = agent_app.invoke(
                    {
                        "messages": messages_for_agent,
                        "history": history_str,
                        # keep these optional keys if your AgentState expects them
                        "error_count": 0,
                        "user_query_for_log": "",
                        "sql_query_for_log": "",
                        "corrected_sql_query_for_log": "",
                        "raw_tool_output_for_log": "",
                    }
                )

                bot_response = final_state["messages"][-1].content

                # Stream output (or use st.markdown(bot_response) if you prefer)
                st.write_stream(stream_response(bot_response))

                # persist to DB conversation history
                add_to_conversation_history(DB_CONFIG, "User", prompt)
                add_to_conversation_history(DB_CONFIG, "Agent", bot_response)

            except Exception as e:
                bot_response = f"🚨 An error occurred: {e}"
                st.error(bot_response)

    # store assistant message in session state
    st.session_state.messages.append({"role": "assistant", "content": bot_response})
