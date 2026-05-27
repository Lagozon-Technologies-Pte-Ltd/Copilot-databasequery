from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import pyodbc
import os
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# =========================================================
# AZURE SQL CONFIG
# =========================================================

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

# =========================================================
# MICROSOFT GRAPH / OAUTH CONFIG
# =========================================================

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = [
    "User.Read",
    "Mail.Send",
    "Mail.Read",
    "Mail.ReadWrite",
    "Calendars.ReadWrite",
    "Sites.Read.All",
    "Sites.ReadWrite.All",
    "Files.Read.All",
    "Files.ReadWrite.All"
]

# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
async def root():

    return {
        "message": "Enterprise Copilot Backend Running"
    }

# =========================================================
# LOGIN ENDPOINT
# =========================================================

@app.get("/login")
async def login():

    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    return RedirectResponse(auth_url)

# =========================================================
# AUTH CALLBACK
# =========================================================

@app.get("/auth/callback")
async def auth_callback(request: Request):

    code = request.query_params.get("code")

    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    access_token = result.get("access_token")

    if access_token:

        return {
            "message": "Login successful",
            "access_token": access_token
        }

    else:

        return {
            "error": result
        }

# =========================================================
# EXECUTE SQL QUERY
# =========================================================

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

        # FORMAT RESPONSE
        formatted_response = ""

        if len(results) == 0:

            formatted_response = "No records found."

        else:

            formatted_response += "Query Results:\n\n"

            for index, row in enumerate(results, start=1):

                formatted_response += f"🔹 Record {index}\n"

                for key, value in row.items():

                    formatted_response += f"   • {key}: {value}\n"

                formatted_response += "\n"

        return {
            "formatted_response": formatted_response,
            "raw_results": results
        }

    except Exception as e:

        return {
            "error": str(e)
        }

# =========================================================
# SEND MAIL AS LOGGED-IN USER
# =========================================================

@app.post("/send-mail")
async def send_mail(data: dict):

    try:

        access_token = data.get("access_token")

        recipient = data.get("recipient")
        subject = data.get("subject")
        body = data.get("body")

        if not access_token:

            return {
                "error": "Access token missing"
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient
                        }
                    }
                ]
            }
        }

        response = requests.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers=headers,
            json=email_data
        )

        return {
            "status_code": response.status_code,
            "message": "Mail sent successfully",
            "response": response.text
        }

    except Exception as e:

        return {
            "error": str(e)
        }
        
        
# =========================================================
# READ LAST 10 MAILS
# =========================================================

@app.post("/read-mails")
async def read_mails(data: dict):

    try:

        access_token = data.get("access_token")

        if not access_token:

            return {
                "error": "Access token missing"
            }

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/messages?$top=10",
            headers=headers
        )

        mails = response.json()

        formatted_response = ""

        if "value" in mails:

            for index, mail in enumerate(mails["value"], start=1):

                subject = mail.get("subject", "No Subject")

                sender = (
                    mail.get("from", {})
                    .get("emailAddress", {})
                    .get("address", "Unknown Sender")
                )

                received = mail.get("receivedDateTime", "")

                formatted_response += (
                    f"📧 Mail {index}\n"
                    f"Subject: {subject}\n"
                    f"From: {sender}\n"
                    f"Received: {received}\n\n"
                )

        return {
            "formatted_response": formatted_response,
            "raw_response": mails
        }

    except Exception as e:

        return {
            "error": str(e)
        }        
        

# =========================================================
# GET USER PROFILE
# =========================================================

@app.post("/my-profile")
async def my_profile(data: dict):

    try:

        access_token = data.get("access_token")

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers=headers
        )

        return response.json()

    except Exception as e:

        return {
            "error": str(e)
        }

# =========================================================
# GET SHAREPOINT SITES
# =========================================================

@app.post("/sharepoint-sites")
async def sharepoint_sites(data: dict):

    try:

        access_token = data.get("access_token")

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(
            "https://graph.microsoft.com/v1.0/sites",
            headers=headers
        )

        return response.json()

    except Exception as e:

        return {
            "error": str(e)
        }
