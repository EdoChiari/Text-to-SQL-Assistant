import streamlit as st
import psycopg2
import anthropic
import markdown
from html2docx import html2docx
from docx import Document
from datetime import datetime
import os
import json
import io
from dotenv import load_dotenv

load_dotenv()

st.title("🔍 Text-to-SQL Assistant")
st.caption("Ask questions about your database in plain English")

# Initialize session state
if "session_data" not in st.session_state:
    st.session_state.session_data = []
if "selected_db" not in st.session_state:
    st.session_state.selected_db = None
if "schema" not in st.session_state:
    st.session_state.schema = None

# Connect to postgres to list databases
@st.cache_data
def get_databases():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname="postgres",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        SELECT datname FROM pg_database
        WHERE datistemplate = false AND datname != 'postgres'
        ORDER BY datname
    """)
    databases = [row[0] for row in cur.fetchall()]
    conn.close()
    return databases

# Get schema for selected database
@st.cache_data
def get_schema(db_name):
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=db_name,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    schema = {}
    for table, column, dtype in cur.fetchall():
        if table not in schema:
            schema[table] = []
        schema[table].append(f"{column} ({dtype})")
    conn.close()
    return schema

# Sidebar — database selection
with st.sidebar:
    st.header("Database")
    databases = get_databases()
    selected_db = st.selectbox("Select a database", databases)

    if selected_db != st.session_state.selected_db:
        st.session_state.selected_db = selected_db
        st.session_state.schema = get_schema(selected_db)
        st.session_state.session_data = []

    st.divider()
    st.header("Available Tables")
    if st.session_state.schema:
        tables = list(st.session_state.schema.items())
        for i, (table, columns) in enumerate(tables):
            st.markdown(f"**{table}**")
            for col in columns:
                st.text(f"  {col}")
            if i < len(tables) - 1:
                st.divider()

# Main area — question input
question = st.text_input("Ask a question about your database:")

if st.button("Ask", type="primary") and question:
    schema = st.session_state.schema
    schema_text = ""
    for table, columns in schema.items():
        schema_text += f"\nTable: {table}\n"
        schema_text += "\n".join([f"  - {col}" for col in columns])
        schema_text += "\n"

    client = anthropic.Anthropic()

    with st.spinner("Generating SQL..."):
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": f"""
                You are a SQL expert. Given the following database schema,
                write a PostgreSQL query to answer the user's question.
                Return ONLY the SQL query, nothing else.
                
                Database schema:
                {schema_text}
                
                User question: {question}
                """}
            ]
        )

    sql_query = message.content[0].text

    with st.expander("Generated SQL"):
        st.code(sql_query, language="sql")

    # Execute query
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=selected_db,
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute(sql_query)
        results = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
        conn.close()

        if not results:
            st.warning("No results found for this question.")
        else:
            results_text = ", ".join(column_names) + "\n"
            for row in results:
                results_text += str(row) + "\n"

            with st.spinner("Interpreting results..."):
                interpretation = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    messages=[
                        {"role": "user", "content": f"""
                        The user asked: "{question}"
                        
                        The SQL query returned these results:
                        {results_text}
                        
                        Please provide a clear, concise answer in natural language.
                        No SQL, no technical details — just a clean human-readable answer.
                        Use only text, headings, and numbered or bullet lists.
                        Do NOT use markdown tables.
                        """}
                    ]
                )

            answer = interpretation.content[0].text
            st.markdown(answer)

            st.session_state.session_data.append({
                "question": question,
                "sql_query": sql_query,
                "answer": answer,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

    except Exception as e:
        st.error(f"Query failed: {e}")

# Session history
if st.session_state.session_data:
    st.divider()
    st.header("Session History")
    for i, item in enumerate(st.session_state.session_data, 1):
        with st.expander(f"Q{i}: {item['question']}"):
            st.code(item["sql_query"], language="sql")
            st.markdown(item["answer"])

    # Save session button
    st.divider()
    default_name = f"{selected_db}_{datetime.now().strftime('%Y-%m-%d')}"
    session_name = st.text_input("Session name", value=default_name)

    if st.button("💾 Save Session"):
        os.makedirs(session_name, exist_ok=True)

        with open(f"{session_name}/{session_name}.json", "w", encoding="utf-8") as f:
            json.dump({
                "database": selected_db,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "questions": st.session_state.session_data
            }, f, ensure_ascii=False, indent=2)

        doc = Document()
        doc.add_heading("Text-to-SQL Session Report", level=1)
        doc.add_paragraph(f"Database: {selected_db}")
        doc.add_paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        for i, item in enumerate(st.session_state.session_data, 1):
            doc.add_heading(f"Question {i}: {item['question']}", level=2)
            doc.add_heading("SQL Query", level=3)
            doc.add_paragraph(item["sql_query"])
            doc.add_heading("Answer", level=3)
            html_content = markdown.markdown(item["answer"])
            tmp_bytes = html2docx(html_content, title="")
            tmp_doc = Document(io.BytesIO(tmp_bytes.getvalue()))
            for element in tmp_doc.element.body:
                doc.element.body.append(element)

        doc.save(f"{session_name}/{session_name}.docx")
        st.success(f"Session saved in {session_name}/")