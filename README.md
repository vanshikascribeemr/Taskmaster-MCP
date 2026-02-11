# Taskmaster MCP Service

MCP (Model Context Protocol) service that connects Taskmaster APIs and Newsletter Subscription DB to ChatGPT.

## 🚀 "Ask GPT Everything" - New Capabilities
You can now ask ChatGPT high-level executive questions about the Taskmaster ecosystem:
- **"What is the status of provider Shiv Pal Yadav?"** (Searches all categories and summarizes)
- **"Show me all blocked tasks across the company."** (Identifies bottlenecks)
- **"Which projects have overdue tasks?"** (Real-time deadline tracking)
- **"Search for all tasks containing 'MedCode'."** (Global keyword search)

---

## 🛠 Features
- **Live Taskmaster Integration**: Dynamic fetching of categories and tasks from `hrms.scribeemr.com`.
- **Global Search**: Cross-category searching by alias, keyword, or provider name.
- **Risk Detection**: Automated scanning for Blocked and Overdue tasks.
- **TF-IDF Summarization**: Intelligent ranking and narration of task updates.
- **Subscription Management**: PostgreSQL-backed user personalization for newsletters.

---

## 📦 Project Structure
```text
taskmaster-mcp-service/
├── app/
│   ├── main.py            # FastAPI Application & MCP Endpoints
│   ├── connectors/
│   │   ├── taskmaster_client.py   # The "Brain": Live fetching & Search
│   │   └── db.py                  # PostgreSQL/SQLAlchemy Connector
│   ├── tools/
│   │   ├── categories.py          # Category tools
│   │   ├── tasks.py               # Task, Search, and Risk tools
│   │   ├── newsletter.py          # Summary & Preview tools
│   │   └── subscriptions.py       # Personalization tools
│   ├── services/
│   │   └── summarizer.py          # TF-IDF & Narrative Logic
│   └── models/
│       └── schemas.py             # Re-mapped Pydantic Schemas (Live API matched)
├── Dockerfile
├── requirements.txt
└── .env
```

---

## 🛠 MCP Tools (FastAPI Endpoints)
The following tools are exposed for ChatGPT:

### 🔍 Search & Risk Tools
- `search_tasks`: Global search by keyword or provider name.
- `get_provider_updates`: Generates a professional summary for a specific alias.
- `get_blocked_tasks`: Finds all "Blocked" or "On Hold" tasks company-wide.
- `get_overdue_tasks`: Lists all tasks currently past their deadline.

### 📋 Standard Tools
- `get_categories`: Lists all project categories.
- `get_category_tasks`: Detailed list of tasks for a category.
- `get_weekly_summary`: Narrative assessment of a category.
- `preview_newsletter`: End-to-end view of a user's upcoming newsletter.

---

## 🚀 How to Connect to ChatGPT (OpenAPI Schema)
Copy this JSON into your ChatGPT Custom GPT **Actions** configuration:

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Taskmaster MCP",
    "version": "1.0.0",
    "description": "Executive intelligence for Taskmaster APIs."
  },
  "servers": [{"url": "https://your-deployed-url.com"}],
  "paths": {
    "/tools/search_tasks": {
      "get": {
        "operationId": "search_tasks",
        "parameters": [{"name": "query", "in": "query", "required": true, "schema": {"type": "string"}}]
      }
    },
    "/tools/get_provider_updates": {
      "get": {
        "operationId": "get_provider_updates",
        "parameters": [{"name": "provider_alias", "in": "query", "required": true, "schema": {"type": "string"}}]
      }
    },
    "/tools/get_blocked_tasks": {
      "get": { "operationId": "get_blocked_tasks" }
    },
    "/tools/get_overdue_tasks": {
      "get": { "operationId": "get_overdue_tasks" }
    },
    "/tools/get_categories": {
      "get": { "operationId": "get_categories" }
    },
    "/tools/get_weekly_summary": {
      "get": {
        "operationId": "get_weekly_summary",
        "parameters": [{"name": "category_id", "in": "query", "required": true, "schema": {"type": "integer"}}]
      }
    },
    "/tools/preview_newsletter": {
      "get": {
        "operationId": "preview_newsletter",
        "parameters": [{"name": "user_email", "in": "query", "required": true, "schema": {"type": "string"}}]
      }
    }
  }
}
```

---

## ⚙️ Local Setup
1. `pip install -r requirements.txt`
2. `uvicorn app.main:app --reload`
3. Access at `http://localhost:8000/docs` to test tools manually.
