# app/agent.py
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

# Import from your application's files
from config import llm, DB_CONFIG
from tools import sql_database_tool
# Ensure you are using the version of database_utils with the SQL validator helpers
from database_utils import initialize_comprehensive_log_table, add_to_comprehensive_log, get_schema_identifiers
from sql_validator import get_cased_identifiers, fix_sql_casing


# --- Agent State Definition (ensure it includes the corrected_sql_query) ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    history: str
    error_count: int
    user_query_for_log: str
    sql_query_for_log: str
    corrected_sql_query_for_log: str
    raw_tool_output_for_log: str


# --- Dummy Tools for Deterministic Routing ---
@tool
def route_to_sql_agent(query: str):
    """Route the user's request to the SQL agent for execution."""
    pass


@tool
def route_to_synthesis_agent(response: str):
    """Route the user's request for a direct conversational response."""
    pass


# --- Node Definitions ---

def capture_user_query(state: AgentState):
    """A new starting node to capture the user's query for logging."""
    print("--- CAPTURING USER QUERY FOR LOG ---")
    state["user_query_for_log"] = state["messages"][-1].content
    return state


def tool_calling_agent(state: AgentState):
    """
    This agent generates the initial SQL query using the detailed schema.
    The programmatic validator will still correct any mistakes.
    """
    print("--- 👨‍🏫 SQL QUERY GENERATOR (WITH DETAILED SCHEMA) ---")
    tools_to_bind = [sql_database_tool]
    llm_with_tools = llm.bind_tools(tools_to_bind)

    # --- PROVIDE YOUR DATABASE INFORMATION ---
    system_prompt = f"""You are a hyper-attentive SQL query analyst. Your only goal is to produce a single, perfect, executable SQL query for PostgreSQL. 
    You MUST refer ONLY to the complete database schema guide provided below. Do not assume or use any tables or columns not explicitly listed here.

# Complete Database Schema Guide for GenAI Model

## CRITICAL INSTRUCTIONS
- **CASE SENSITIVITY**: All table names, column names, and values are CASE SENSITIVE. Use EXACTLY as written below.
- **ONLY USE THESE TABLES AND COLUMNS**: Do not reference any tables or columns not listed here.
- **NO ASSUMPTIONS**: If a column or table is not explicitly listed, it does not exist.

---

## 📍 ADDRESS MANAGEMENT

### **`addresses`** Table
**Purpose**: Stores all physical address information for students, schools, and other entities.

**Columns**:
- **`address_id`**: Unique number that identifies each address (like a house number for the database)
- **`line_1`**: First line of street address (e.g., "123 Main Street")
- **`line_2`**: Second line of street address (e.g., "Apartment 4B") - can be empty
- **`line_3`**: Third line of street address (e.g., "Building C") - can be empty
- **`city`**: Name of the city (e.g., "New York")
- **`zip_postcode`**: Postal code or ZIP code (e.g., "10001")
- **`state_province_county`**: State, province, or county name (e.g., "California")
- **`country`**: Country name (e.g., "United States")
- **`other_address_details`**: Any extra address information not covered above

**Think of it like**: A filing cabinet where each drawer (`address_id`) contains a complete mailing address.

---

## 🎓 COURSE MANAGEMENT SYSTEM

### **`course`** Table (Note: lowercase: 'c' singular "course")
**Purpose**: Contains course schedules with starting dates and basic course names.

**Columns**:
- **`Course_id`**: Unique identifier for each course (Note: Capital 'C')
- **`Starting_Date`**: When the course begins (exact date)
- **`Course`**: The name of the course (Note: Capital 'C')

**Think of it like**: A calendar showing when each class starts.

### **`courses`** Table (Note: plural "courses")
**Purpose**: The main detailed information hub for all courses offered.
**Columns**:
- **`course_id`**: Unique identifier for each course (Note: lowercase 'c')
- **`course_name`**: Official name of the course (same information as `Course` in the `course` table)
- **`course_description`**: Detailed explanation of what the course teaches
- **`other_details`**: Any additional course information

**Think of it like**: A course catalog with full descriptions of every class.

### **`course_arrange`** Table
**Purpose**: Links teachers to the courses they teach for specific grade levels.
**Columns**:
- **`Course_ID`**: Which course is being taught. **CRITICAL: This joins with the `course_id` (all lowercase) column in the `courses` table.**
- **`Teacher_ID`**: Which teacher is teaching. **CRITICAL: This joins with the `Teacher_ID` column in the `teacher` table.**
- **`Grade`**: What grade level this arrangement is for.

**Think of it like**: A schedule board showing "Teacher Smith teaches Math to Grade 5"

### **`sections`** Table
**Purpose**: Breaks courses into smaller groups or different types of sessions.

**Columns**:
- **`section_id`**: Unique identifier for each section
- **`course_id`**: Which course this section belongs to (connects to `courses.course_id`)
- **`section_name`**: Name of the section (e.g., "Lecture A", "Lab Session B")
- **`section_department`**: Which department runs this section
- **`other_details`**: Additional section information
**Think of it like**: Dividing a big class into smaller groups, each with its own name.

---

## 🏫 ACADEMIC STRUCTURE

### **`departments`** Table
**Purpose**: Lists all academic departments in the institution.

**Columns**:
- **`department_id`**: Unique identifier for each department
- **`department_name`**: Official name of the department (e.g., "History Department", "Mathematics Department")
- **`department_description`**: What the department does and teaches
- **`other_details`**: Additional department information

**Think of it like**: Different sections of a library, each specializing in different subjects.

### **`degree_programs`** Table
**Purpose**: Information about degree programs that students can enroll in.

**Columns**:
- **`degree_program_id`**: Unique identifier for each degree program
- **`department_id`**: Which department offers this degree (connects to `departments.department_id`)
- **`degree_summary_name`**: Name of the degree (e.g., "Bachelor of Science in Biology")
- **`degree_summary_description`**: What this degree program covers
- **`other_details`**: Additional degree program information

**Think of it like**: Different paths students can take to graduate, each owned by a department.

### **`semesters`** Table
**Purpose**: Defines academic time periods.

**Columns**:
- **`semester_id`**: Unique identifier for each semester
- **`semester_name`**: Name of the semester (e.g., "Fall 2023", "Spring 2024")
- **`semester_description`**: Details about the semester
- **`other_details`**: Additional semester information

**Think of it like**: Time blocks when school is in session.

---

## 👨‍🎓 STUDENT MANAGEMENT

### **`students`** Table (Note: plural "students")
**Purpose**: Complete personal and academic information for every student.

**Columns**:
- **`student_id`**: Unique identifier for each student
- **`current_address_id`**: Where student lives now (connects to `addresses.address_id`)
- **`permanent_address_id`**: Student's permanent home address (connects to `addresses.address_id`)
- **`first_name`**: Student's first name
- **`middle_name`**: Student's middle name (can be empty)
- **`last_name`**: Student's last name
- **`cell_mobile_number`**: Student's phone number
- **`email_address`**: Student's email address
- **`ssn`**: Student's Social Security Number
- **`date_first_registered`**: When student first enrolled
- **`date_left`**: When student left (can be empty if still enrolled)
- **`other_student_details`**: Any other student information

**Think of it like**: A student ID card with all personal information.

### **`student_enrolment`** Table (Note: British spelling "enrolment")
**Purpose**: Records when a student registers for a degree program in a specific semester.

**Columns**:
- **`student_enrolment_id`**: Unique identifier for this enrollment event
- **`degree_program_id`**: Which degree program (connects to `degree_programs.degree_program_id`)
- **`semester_id`**: Which semester (connects to `semesters.semester_id`)
- **`student_id`**: Which student (connects to `students.student_id`)
- **`other_details`**: Additional enrollment information

**Think of it like**: A registration form that says "Student X signed up for Degree Y in Semester Z"

### **`student_enrolment_courses`** Table
**Purpose**: Links student enrollments to specific courses they take.

**Columns**:
- **`student_course_id`**: Unique identifier for a student taking a specific course
- **`course_id`**: Which course (connects to `courses.course_id`)
- **`student_enrolment_id`**: Which enrollment (connects to `student_enrolment.student_enrolment_id`)

**Think of it like**: A class roster showing which students are in which courses.

---

## 👨‍🏫 TEACHER MANAGEMENT

### **`teacher`** Table (Note: singular "teacher")
**Purpose**: Personal and professional information about all teachers.

**Columns**:
- **`Teacher_ID`**: Unique identifier for each teacher (Note: Capital 'T' and 'ID')
- **`Name`**: Full name of the teacher (Note: Capital 'N')
- **`Age`**: Teacher's age (Note: Capital 'A')
- **`Hometown`**: Where the teacher is from (Note: Capital 'H')

**Think of it like**: An employee directory for all teachers.

---

## 🚌 SCHOOL TRANSPORTATION SYSTEM

### **`School`** Table (Note: Capital 'S', singular)
**Purpose**: Information about different schools in the system.

**Columns**:
- **`School_Name`**: Name of the school (Note: both words capitalized with underscore)
- **`School_ID`**: Unique identifier for each school (Note: capitals and underscore)
- **`Grade`**: Grade levels at this school (Note: Capital 'G')
- **`school`**: Additional school information (Note: lowercase 's')
- **`location`**: Where the school is located (Note: lowercase)
- **`type`**: Type of school (Note: lowercase)

**Think of it like**: A directory of all schools in the district.

### **`driver`** Table (Note: lowercase 'd', singular)
**Purpose**: Information about school bus drivers.

**Columns**:
- **`Driver_ID`**: Unique identifier for each driver (Note: Capital 'D' and 'ID')
- **`Driver_name`**: Driver's full name (Note: Capital 'D')
- **`party`**: Driver's political party or group affiliation (Note: lowercase)
- **`home_city`**: City where driver lives (Note: lowercase with underscore)
- **`age`**: Driver's age (Note: lowercase)

**Think of it like**: Personnel files for all bus drivers.

### **`school_bus`** Table
**Purpose**: Links drivers to schools and tracks their employment details.

**Columns**:
- **`School_ID`**: Which school (connects to `School.School_ID`)
- **`Driver_ID`**: Which driver (connects to `driver.Driver_ID`)
- **`Years_working`**: How many years driver has worked this route (Note: capital 'Y' and underscore)
- **`if_full_time`**: Whether driver works full time or not (Note: lowercase with underscores)

**Think of it like**: A work assignment chart showing which driver works for which school.

---

## 📜 TRANSCRIPT SYSTEM

### **`transcripts`** Table
**Purpose**: High-level information about student academic transcripts.

**Columns**:
- **`transcript_id`**: Unique identifier for each transcript
- **`transcript_date`**: When the transcript was created
- **`other_details`**: Additional transcript information

**Think of it like**: A filing system for official grade reports.

### **`transcript_contents`** Table
**Purpose**: Links specific student courses to transcripts (shows what appears on each transcript).

**Columns**:
- **`student_course_id`**: Which student course (connects to `student_enrolment_courses.student_course_id`)
- **`transcript_id`**: Which transcript (connects to `transcripts.transcript_id`)

**Think of it like**: A table of contents showing which courses appear on which transcript.

---

## 🔗 KEY RELATIONSHIPS (How Tables Connect)

1. **Students and Addresses**: Students have two addresses (current and permanent)
2. **Students and Enrollment**: Students enroll in degree programs for specific semesters
3. **Enrollment and Courses**: Each enrollment can include multiple courses
4. **Courses and Sections**: Courses can be divided into sections
5. **Teachers and Courses**: Teachers are assigned to teach courses for specific grades
6. **Departments and Degrees**: Departments offer degree programs
7. **Schools and Drivers**: Drivers are assigned to work at schools
8. **Transcripts and Courses**: Transcripts contain specific student courses

## ⚠️ CRITICAL REMINDERS

1. **EXACT CASE MATCHING**: `Teacher_ID` ≠ `teacher_id` ≠ `Teacher_Id`
2. **TABLE NAME ACCURACY**: `course` (singular) vs `courses` (plural) are DIFFERENT tables
3. **COLUMN EXISTENCE**: If a column isn't listed here, it doesn't exist
4. **LINKING TABLES**: Tables like `course_arrange`, `school_bus`, `student_enrolment_courses`, and `transcript_contents` connect other tables together
5. **NO ASSUMPTIONS**: Only use what's explicitly documented here
    """
    messages_for_llm = [SystemMessage(content=system_prompt)] + state['messages']
    response = llm_with_tools.invoke(messages_for_llm)

    if not response.tool_calls:
        return {"messages": [AIMessage(content=response.content)]}

    return {"messages": [response]}


def custom_tool_executor(state: AgentState):
    """
    Intercepts the generated SQL, validates and corrects casing issues,
    and then executes the guaranteed-correct query.
    """
    print("--- 🛡️ VALIDATING AND EXECUTING SQL ---")
    try:
        last_message = state["messages"][-1]

        if not last_message.tool_calls:
            error_content = "[TOOL_ERROR] The agent could not determine which tool to use. Please rephrase."
            return {"messages": [ToolMessage(content=error_content, tool_call_id="error")]}

        tool_call = last_message.tool_calls[0]
        tool_input = tool_call["args"]

        original_sql_query = tool_input.get("query")
        if not original_sql_query:
            return {"messages": [
                ToolMessage(content="[TOOL_ERROR] Agent did not produce a query.", tool_call_id=tool_call["id"])]}

        print(f"Original Query from LLM: {original_sql_query}")

        schema_identifiers = get_schema_identifiers(DB_CONFIG)
        cased_identifiers = get_cased_identifiers(schema_identifiers)
        corrected_sql_query = fix_sql_casing(original_sql_query, cased_identifiers)
        print(f"Corrected Query for Execution: {corrected_sql_query}")

        tool_input["query"] = corrected_sql_query
        raw_result = sql_database_tool.invoke(tool_input)

        tool_message = ToolMessage(content=str(raw_result), tool_call_id=tool_call["id"])

        return {
            "messages": [tool_message],
            "sql_query_for_log": original_sql_query,
            "corrected_sql_query_for_log": corrected_sql_query,
            "raw_tool_output_for_log": str(raw_result)
        }

    except Exception as e:
        print(f"[ERROR] in custom_tool_executor: {e}")
        error_content = f"[TOOL_ERROR] Could not execute tool: {e}"
        return {"messages": [ToolMessage(content=error_content, tool_call_id="error")]}


def synthesis_agent(state: AgentState):
    """
    Formats the final output, showing the user the *corrected* SQL query
    that was actually executed. This version has specific rules for table formatting.
    """
    print("--- ✍️ SYNTHESIS AGENT (WITH TABLE FORMATTING) ---")
    sql_query = state.get("corrected_sql_query_for_log") or state.get("sql_query_for_log", "No SQL query was run.")

    # --- NEW PROMPT WITH EXPLICIT TABLE FORMATTING RULES ---
    synthesis_prompt = f"""You are an expert data presentation assistant. Your primary goal is to present data in the clearest way possible for the user.

    **YOUR UNBREAKABLE RULES:**
    1.  **Always Create the SQL Dropdown First:** You MUST begin your response with the collapsible SQL query dropdown. The format is: `<details><summary>View Executed SQL Query</summary>```sql\n{sql_query}\n```</details>`

    2.  **Check the Tool Output for Formatting:** Look at the most recent `ToolMessage` in the conversation context.
        - **IF the result is a list with multiple dictionaries** (e.g., `[...], [...]`), you **MUST** format the final answer as a clean Markdown table. Use the dictionary keys as the table headers.
        - **IF the result is a single number, a single name, or a list with only one dictionary**, you should present it as a natural language sentence.
        - **IF the result contains `[SQL_ERROR]` or `[TOOL_ERROR]`**, apologize that the query failed, explain that you ran into an issue, and ask the user to rephrase their question. Do not try to make up an answer.

    3.  **Do Not Mention the Query in the Final Answer:** The dropdown handles the query. Just present the data.

    **EXAMPLE OF A PERFECT TABLE-BASED RESPONSE:**
    ---
    *User asks: "Who are the teachers and what are their hometowns?"*
    *Tool returns: `ToolMessage(content="[{{'Name': 'John Smith', 'Hometown': 'Springfield'}}, {{'Name': 'Jane Doe', 'Hometown': 'Rivertown'}}]")`*

    *Your final response should be:*
    <details><summary>View Executed SQL Query</summary>```sql
    SELECT "Name", "Hometown" FROM teacher
    ```</details>
    Here are the teachers and their hometowns:

    | Name       | Hometown   |
    |------------|------------|
    | John Smith | Springfield|
    | Jane Doe   | Rivertown  |
    ---

    **EXAMPLE OF A PERFECT SENTENCE-BASED RESPONSE:**
    ---
    *User asks: "How many teachers are there?"*
    *Tool returns: `ToolMessage(content="[{{'count': 27}}]")`*

    *Your final response should be:*
    <details><summary>View Executed SQL Query</summary>```sql
    SELECT count(*) FROM teacher
    ```</details>
    There are 27 teachers in total.
    ---

    **Conversation Context (includes the real tool results):**
    {state['messages']}

    Generate the final user-facing response now, strictly following these rules.
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
        final_response=state["messages"][-1].content
    )
    return state


# --- Routers ---
def chief_router_node(state: AgentState):
    """Router to decide between querying the database or simple conversation."""
    print("--- 🧠 CHIEF ROUTER ---")
    router_tools = [route_to_sql_agent, route_to_synthesis_agent]
    llm_with_router_tools = llm.bind_tools(router_tools)

    prompt = f"""You are a router. Based on the user's latest message, should you query the database or just chat?
    Call `route_to_sql_agent` for questions about data. Call `route_to_synthesis_agent` for greetings or chit-chat.
    User's LATEST Message: "{state['messages'][-1].content}"
    """
    response = llm_with_router_tools.invoke(prompt)
    return {"messages": [response]}


def route_logic(state: AgentState):
    """Correctly routes based on the tool call from the chief_router."""
    if state["messages"][-1].tool_calls and state["messages"][-1].tool_calls[0]["name"] == "route_to_sql_agent":
        print("--- ROUTE: Decided to go to SQL Agent ---")
        return "tool_agent"
    print("--- ROUTE: Decided to go to Synthesis Agent ---")
    return "synthesis_agent"


# --- Graph Assembly ---
def get_agent_app():
    """Configures and compiles the final, robust agentic graph with validation."""
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
        "chief_router", route_logic, {
            "tool_agent": "tool_agent",
            "synthesis_agent": "synthesis_agent",
        }
    )
    workflow.add_edge("tool_agent", "tool_executor")
    workflow.add_edge("tool_executor", "synthesis_agent")
    workflow.add_edge("synthesis_agent", "log_interaction_node")
    workflow.add_edge("log_interaction_node", END)

    app = workflow.compile()
    print("✅ Agentic system with SQL validation compiled and ready.")
    return app