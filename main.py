from fastapi import FastAPI
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Azure SQL Connection
server = os.getenv("DB_SERVER")
database = os.getenv("DB_NAME")
username = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

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

    # Allow only SELECT queries
    if not sql_query.strip().upper().startswith("SELECT"):
        return {
            "error": "Only SELECT queries are allowed"
        }

    # Block dangerous SQL
    blocked_keywords = [
        "DELETE",
        "DROP",
        "UPDATE",
        "ALTER",
        "INSERT",
        "TRUNCATE"
    ]

    for keyword in blocked_keywords:
        if keyword in sql_query.upper():
            return {
                "error": f"{keyword} operations are not allowed"
            }

    try:

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        cursor.execute(sql_query)

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        results = []

        for row in rows:
            results.append(dict(zip(columns, row)))

        conn.close()

        # ---------- FORMAT RESPONSE ----------
        formatted_response = ""

        if len(results) == 0:
            formatted_response = "No records found."

        else:

            # Dynamic formatting
            for index, row in enumerate(results, start=1):

                formatted_response += f"Record {index}:\n"

                for key, value in row.items():
                    formatted_response += f"• {key}: {value}\n"

                formatted_response += "\n"

        return {
            "formatted_response": formatted_response,
            "raw_results": results
        }

    except Exception as e:
        return {
            "error": str(e)
        }
