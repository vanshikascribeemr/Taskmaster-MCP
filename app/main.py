import structlog
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from .config import settings
from .connectors.taskmaster_client import TaskmasterClient
from .connectors.db import get_db, init_db
from .tools import categories, tasks, subscriptions, newsletter

from contextlib import asynccontextmanager

# Setup logging
structlog.configure()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    logger.info("Database initialized and service started")
    yield
    # Shutdown logic (optional)
    logger.info("Shutting down service")

app = FastAPI(
    title="Taskmaster MCP Service",
    description="MCP Service connecting Taskmaster APIs and Newsletter Subscription DB to ChatGPT",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize Taskmaster Client
taskmaster_client = TaskmasterClient()

# --- MCP Tools Endpoints ---

@app.get("/tools/get_categories", summary="Get all active categories from Taskmaster")
async def get_categories():
    return await categories.get_categories(taskmaster_client)

@app.get("/tools/get_category_tasks", summary="Fetch tasks for a specific category")
async def get_category_tasks(category_id: int):
    return await tasks.get_category_tasks(category_id, taskmaster_client)

@app.get("/tools/search_tasks", summary="Search for tasks by alias, provider name, or keyword across all categories")
async def search_tasks(query: str):
    return await tasks.get_tasks_by_alias(query, taskmaster_client)

@app.get("/tools/get_provider_updates", summary="Get a summarized report for a specific medical provider alias")
async def get_provider_updates(provider_alias: str):
    return await tasks.get_provider_updates(provider_alias, taskmaster_client)

@app.get("/tools/get_blocked_tasks", summary="Fetch all blocked tasks across all categories for emergency review")
async def get_blocked_tasks():
    return await tasks.get_all_blocked_tasks(taskmaster_client)

@app.get("/tools/get_overdue_tasks", summary="Fetch all overdue tasks across all categories for deadline tracking")
async def get_overdue_tasks():
    return await tasks.get_all_overdue_tasks(taskmaster_client)

@app.get("/tools/get_weekly_summary", summary="Generate category-level summary")
async def get_weekly_summary(category_id: int):
    return await newsletter.get_weekly_summary(category_id, taskmaster_client)

@app.get("/tools/list_user_subscriptions", summary="Fetch categories subscribed by a user")
async def list_user_subscriptions(user_email: str, db: Session = Depends(get_db)):
    subs = await subscriptions.list_user_subscriptions(user_email, db)
    # Complement with category names for better UX
    all_cats = await taskmaster_client.get_all_categories()
    result = []
    for cat_id in subs:
        cat_info = next((c for c in all_cats if c.id == cat_id), {"id": cat_id, "name": "Unknown"})
        result.append(cat_info)
    return result

@app.get("/tools/preview_newsletter", summary="Preview user's weekly newsletter")
async def preview_newsletter(user_email: str, db: Session = Depends(get_db)):
    return await newsletter.preview_newsletter(user_email, taskmaster_client, db)

@app.post("/tools/subscribe_category", summary="Subscribe user to a category")
async def subscribe_category(user_email: str, category_id: int, db: Session = Depends(get_db)):
    # Validate category_id against Taskmaster as requested in Security Model
    all_cats = await taskmaster_client.get_all_categories()
    if not any(c.id == category_id for c in all_cats):
        raise HTTPException(status_code=400, detail="Invalid Category ID")
    
    return await subscriptions.subscribe_category(user_email, category_id, db)

@app.post("/tools/unsubscribe_category", summary="Unsubscribe user from a category")
async def unsubscribe_category(user_email: str, category_id: int, db: Session = Depends(get_db)):
    return await subscriptions.unsubscribe_category(user_email, category_id, db)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

