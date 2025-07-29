# The corrected and clean ui.py

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
import time

# Import from your application's modules
from agent import get_agent_app
from database_utils import add_to_conversation_history, get_recent_conversation_history
from config import DB_CONFIG

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="ADK-MCP Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 3. UI STYLING & SIDEBAR ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Poppins', sans-serif; }
    .st-emotion-cache-1jicfl2 { background-color: #F0F2F6; }
    [data-testid="stChatMessage"] { border-radius: 20px; padding: 1rem 1.25rem; margin-bottom: 1rem; box-shadow: 0 4px 6px rgba(0,0,0,0.04); border: 1px solid transparent; }
    [data-testid="stChatMessage"]:has(div[data-testid="stAvatarIcon-user"]) { background-color: #E9F5FF; border-color: #B9D7F1; }
    [data-testid="stChatMessage"]:has(div[data-testid="stAvatarIcon-assistant"]) { background-color: #FFFFFF; border-color: #E6EAF1; }
    .header { font-size: 2.5rem; font-weight: 700; padding: 1.5rem 0; margin-bottom: 1rem; color: #2c3e50; text-align: center; background: -webkit-linear-gradient(45deg, #6a11cb, #2575fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    [data-testid="stChatInput"] { background-color: #FFFFFF; border-radius: 15px; border: 1px solid #E6EAF1; box-shadow: 0 4px 6px rgba(0,0,0,0.04); }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🤖 your Agent")
    st.markdown("---")
    st.subheader("💡 Try Asking random stuff hehe ")
    st.info("anything about the database?")
    st.info("What are the names of all departments?")
    st.info("Give me the names and hometowns of all the teachers.")


# --- 4. APP INITIALIZATION ---
@st.cache_resource
def initialize_system():
    return get_agent_app()


agent_app = initialize_system()


# --- 5. DYNAMIC RESPONSE STREAMING FUNCTION ---
def stream_response(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.04)


# --- 6. MAIN CHAT INTERFACE ---
st.markdown('<p class="header">Chat with your Database</p>', unsafe_allow_html=True)

# Display past messages
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Handle new user input
if prompt := st.chat_input("Ask your database a question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Agent is thinking..."):
            try:
                messages_for_agent = [
                    HumanMessage(content=msg["content"]) if msg["role"] == "user"
                    else AIMessage(content=msg["content"])
                    for msg in st.session_state.messages
                ]
                history_str = get_recent_conversation_history(DB_CONFIG, limit=10)

                final_state = agent_app.invoke({
                    "messages": messages_for_agent,
                    "history": history_str
                })

                bot_response = final_state["messages"][-1].content
                st.write_stream(stream_response(bot_response))

                add_to_conversation_history(DB_CONFIG, "User", prompt)
                add_to_conversation_history(DB_CONFIG, "Agent", bot_response)

            except Exception as e:
                error_message = f"🚨 An error occurred: {e}"
                st.error(error_message)
                bot_response = error_message

    st.session_state.messages.append({"role": "assistant", "content": bot_response})