# ADK-MCP-Agent: Conversational Database Agent

This project implements a sophisticated conversational AI agent that can interact with a PostgreSQL database. The agent uses the LangGraph framework to create a robust, multi-step reasoning process. It features a SQL-generating LLM, a programmatic SQL validator to fix casing errors, and a user-friendly interface built with Streamlit.

## Key Features

-   **Natural Language to SQL**: Ask complex questions in plain English and get answers directly from your database.
-   **Self-Correcting SQL**: An integrated SQL validator automatically corrects case-sensitivity errors in the generated queries before execution, ensuring high reliability.
-   **Conversational Interface**: A clean and intuitive chat interface powered by Streamlit for seamless interaction.
-   **Modular & Extensible**: Built with LangGraph, making it easy to add new tools, agents, or logic to the workflow.
-   **Comprehensive Logging**: All interactions, including user queries, generated SQL, corrected SQL, and final responses, are logged for monitoring and debugging.

## Project Structure

```
ADK-MCP-Agent/
├── app/
│   ├── agent.py          # Core agent logic and graph definition
│   ├── config.py         # API keys and database configuration
│   ├── database_utils.py # Helper functions for DB interaction
│   ├── sql_validator.py  # Programmatic SQL casing correction
│   └── tools.py          # Custom tools (SQL executor)
├── ui.py                 # Main Streamlit application file
├── requirements.txt      # Python dependencies
├── .gitignore            # Files to be ignored by Git
└── README.md             # Project documentation
```

## Setup and Installation

Follow these steps to get the project running on your local machine.

### 1. Prerequisites

-   Python 3.8+
-   A running PostgreSQL database.
-   A Google AI API Key.

### 2. Clone the Repository

```bash
git clone https://github.com/your-username/ADK-MCP-Agent.git
cd ADK-MCP-Agent
```

### 3. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

You need to configure your database credentials and your Google API key.

1.  **Modify `app/config.py`**:
    Update the `DB_CONFIG` dictionary with your PostgreSQL connection details.

    ```python
    # app/config.py
    DB_CONFIG = {
        "dbname": "your_db_name",
        "user": "your_db_user",
        "password": "your_db_password",
        "host": "localhost",
        "port": "5432",
    }
    ```

2.  **Set Your Google API Key**:
    It is recommended to set your API key as an environment variable for security.

    ```bash
    # On macOS/Linux
    export GOOGLE_API_KEY="your_api_key_here"

    # On Windows (Command Prompt)
    set GOOGLE_API_KEY="your_api_key_here"
    ```
    Alternatively, you can hardcode it in `app/config.py`, but this is not recommended for public repositories.

## How to Run the Application

Once the setup is complete, you can start the Streamlit application from the root directory of the project.

```bash
streamlit run ui.py
```

Open your web browser and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`). You can now start chatting with your database!

## Example Questions

-   "How many teachers are there in total?"
-   "What are the names of all the departments?"
-   "Show me the names and hometowns of all teachers."
-   "Which courses start after '2023-01-01'?"
Use code with caution.
Markdown
By following this guide, your GitHub repository will be well-organized, easy for others to clone and run, and will professionally showcase your skills in building complex AI applications.
