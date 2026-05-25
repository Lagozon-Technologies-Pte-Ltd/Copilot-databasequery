from fastapi import FastAPI
from dotenv import load_dotenv
import os
import pyodbc

# Load .env variables
load_dotenv()

app = FastAPI()

# Environment Variables
server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

# SQL Connection String
connection_string = f"""
DRIVER={{ODBC Driver 18 for SQL Server}};
SERVER={server};
DATABASE={database};
UID={username};
PWD={password};
Encrypt=yes;
TrustServerCertificate=no;
Connection Timeout=30;
"""

@app.get("/")
async def root():
    return {
        "message": "AI SQL Backend Running"
    }

@app.post("/execute-query")
async def execute_query(data: dict):

    sql_query = data.get("sql_query")

    # Validate query exists
    if not sql_query:
        return {
            "error": "No SQL query provided"
        }

    # Allow ONLY SELECT queries
    if not sql_query.strip().upper().startswith("SELECT"):
        return {
            "error": "Only SELECT queries are allowed"
        }

    try:

        # Connect to Azure SQL
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Execute Query
        cursor.execute(sql_query)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch rows
        rows = cursor.fetchall()

        # Convert rows to JSON
        results = []

        for row in rows:
            results.append(dict(zip(columns, row)))

        conn.close()

        return {
            "results": results
        }

    except Exception as e:
        return {
            "error": str(e)
        }