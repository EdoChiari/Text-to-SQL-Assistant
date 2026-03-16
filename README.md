# 🔍 Text-to-SQL Assistant

## What is this project?
A Python tool that lets you query any PostgreSQL database using natural language. Instead of writing SQL manually, you ask questions in plain English and the assistant automatically generates and executes the query, then returns a human-readable answer.

## How it works
1. The script reads your database schema automatically
2. You ask a question in natural language
3. Claude AI translates it into a PostgreSQL query
4. The query is executed on your database
5. Claude interprets the results into a clear answer
6. Everything is saved in a session folder (.json + .docx)

## Example
```
Ask a question: What are the top 5 best selling products?

→ Claude generates SQL with JOIN between order_items and products
→ Executes on PostgreSQL
→ Answer: "The top 5 best selling products are Soccer Goal (301 units),
   Dog Bed with Canopy (284 units), Soccer Net (280 units)..."
```

## Tech Stack
- Python 3.12
- Anthropic Claude API (`claude-sonnet-4-6`)
- PostgreSQL + psycopg2
- python-docx for report generation
- python-dotenv for secure credential management

## Setup
1. Clone the repository
2. Create a `.env` file with your credentials:
```
   ANTHROPIC_API_KEY=your-key-here
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your-database
   DB_USER=your-user
   DB_PASSWORD=your-password
```
3. Install dependencies:
```
   pip install anthropic psycopg2-binary python-dotenv python-docx
```
4. Run:
```
   python script.py
```
5. Ask questions, type `exit` to save the session

## Output
Each session is saved in a dedicated folder:
```
📁 session_name/
    ├── session_name.json    ← structured data
    └── session_name.docx    ← formatted report
```

## Roadmap
- [ ] Error handling for invalid SQL queries
- [ ] Support for multiple databases in the same session
- [ ] Web interface for non-technical users
- [ ] Scheduled automated reports