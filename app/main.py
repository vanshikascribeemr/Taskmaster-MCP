import structlog
import sys
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from .config import settings
from .connectors.taskmaster_client import TaskmasterClient
from .connectors.db import get_db, init_db
from .tools import categories, tasks, subscriptions, newsletter

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
import mcp.types as types

# Setup logging to stderr to avoid interfering with MCP stdio
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr)
)
logger = structlog.get_logger()

# Initialize Taskmaster Client
taskmaster_client = TaskmasterClient()

# Initialize MCP Server
mcp_server = Server("taskmaster-mcp")

# Initialize SSE Transport for Cloud/Remote MCP
sse = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_categories",
            description="Get all active categories from Taskmaster",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="search_tasks",
            description="Search for tasks by alias, provider name, keyword or Task ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "time_window_days": {"type": "integer", "description": "Number of days to look back for updates. Default 7. Use 0 or null for all time."}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_provider_updates",
            description="Get a summarized report for a specific medical provider alias",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider_alias": {"type": "string"},
                    "detail_level": {"type": "string", "enum": ["short", "detailed"], "default": "short"},
                    "time_window_days": {"type": "integer", "default": 7}
                },
                "required": ["provider_alias"]
            }
        ),
        types.Tool(
            name="get_task_summary",
            description="Fetch and summarize a specific task by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "detail_level": {"type": "string", "enum": ["short", "detailed"], "default": "short"},
                    "time_window_days": {"type": "integer", "description": "Number of days to look back for updates. Null for all time."}
                },
                "required": ["task_id"]
            }
        ),
        types.Tool(
            name="get_blocked_tasks",
            description="Fetch all blocked tasks across all categories",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_overdue_tasks",
            description="Fetch all overdue tasks across all categories",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_weekly_summary",
            description="Generate category-level summary",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_id": {"type": "integer"}
                },
                "required": ["category_id"]
            }
        ),
        types.Tool(
            name="get_category_tasks",
            description="Fetch tasks for a specific category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category_id": {"type": "integer"}
                },
                "required": ["category_id"]
            }
        ),
        types.Tool(
            name="list_user_subscriptions",
            description="Fetch categories subscribed by a user",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"}
                },
                "required": ["user_email"]
            }
        ),
        types.Tool(
            name="subscribe_category",
            description="Subscribe user to a category",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"},
                    "category_id": {"type": "integer"}
                },
                "required": ["user_email", "category_id"]
            }
        ),
        types.Tool(
            name="unsubscribe_category",
            description="Unsubscribe user from a category",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"},
                    "category_id": {"type": "integer"}
                },
                "required": ["user_email", "category_id"]
            }
        ),
        types.Tool(
            name="preview_newsletter",
            description="Preview user's weekly newsletter",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"}
                },
                "required": ["user_email"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_categories":
        res = await categories.get_categories(taskmaster_client)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "search_tasks":
        query = arguments.get("query")
        window = arguments.get("time_window_days", 7)
        res = await tasks.get_tasks_by_alias(query, taskmaster_client, time_window_days=window)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_provider_updates":
        alias = arguments.get("provider_alias")
        detail = arguments.get("detail_level", "short")
        window = arguments.get("time_window_days", 7)
        res = await tasks.get_provider_updates(alias, taskmaster_client, detail_level=detail, time_window_days=window)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_task_summary":
        tid = arguments.get("task_id")
        detail = arguments.get("detail_level", "short")
        window = arguments.get("time_window_days")
        res = await tasks.get_task_summary(tid, taskmaster_client, detail_level=detail, time_window_days=window)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_blocked_tasks":
        res = await tasks.get_all_blocked_tasks(taskmaster_client)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_overdue_tasks":
        res = await tasks.get_all_overdue_tasks(taskmaster_client)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_weekly_summary":
        cat_id = arguments.get("category_id")
        res = await newsletter.get_weekly_summary(cat_id, taskmaster_client)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "get_category_tasks":
        cat_id = arguments.get("category_id")
        res = await tasks.get_category_tasks(cat_id, taskmaster_client)
        return [types.TextContent(type="text", text=str(res))]
    elif name == "list_user_subscriptions":
        email = arguments.get("user_email")
        from .connectors.db import SessionLocal
        db = SessionLocal()
        try:
            subs = await subscriptions.list_user_subscriptions(email, db)
            all_cats = await taskmaster_client.get_all_categories()
            result = []
            for cat_id in subs:
                cat_info = next((c for c in all_cats if c.id == cat_id), {"id": cat_id, "name": "Unknown"})
                result.append(cat_info)
            return [types.TextContent(type="text", text=str(result))]
        finally:
            db.close()
    elif name == "subscribe_category":
        email = arguments.get("user_email")
        cat_id = arguments.get("category_id")
        from .connectors.db import SessionLocal
        db = SessionLocal()
        try:
            # Validate category_id
            all_cats = await taskmaster_client.get_all_categories()
            if not any(c.id == cat_id for c in all_cats):
                return [types.TextContent(type="text", text="Error: Invalid Category ID")]
            res = await subscriptions.subscribe_category(email, cat_id, db)
            return [types.TextContent(type="text", text=str(res))]
        finally:
            db.close()
    elif name == "unsubscribe_category":
        email = arguments.get("user_email")
        cat_id = arguments.get("category_id")
        from .connectors.db import SessionLocal
        db = SessionLocal()
        try:
            res = await subscriptions.unsubscribe_category(email, cat_id, db)
            return [types.TextContent(type="text", text=str(res))]
        finally:
            db.close()
    elif name == "preview_newsletter":
        email = arguments.get("user_email")
        from .connectors.db import SessionLocal
        db = SessionLocal()
        try:
            res = await newsletter.preview_newsletter(email, taskmaster_client, db)
            return [types.TextContent(type="text", text=str(res))]
        finally:
            db.close()
    else:
        raise ValueError(f"Unknown tool: {name}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    logger.info("Database initialized and service started")
    yield
    # Shutdown logic (optional)
    logger.info("Shutting down service")

# Add global exception handler for debugging
from fastapi.responses import JSONResponse
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

app = FastAPI(
    title="Taskmaster MCP Service",
    description="MCP Service connecting Taskmaster APIs and Newsletter Subscription DB to ChatGPT",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for cloud connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MCP SSE Endpoints ---

@app.get("/sse")
@app.get("/sse/")
async def handle_sse(request: Request):
    """Establish SSE connection with buffering disabled for Render"""
    logger.info("SSE GET request received", path=request.url.path)
    async with sse.connect_sse(request.scope, request.receive, request.send) as (read_stream, write_stream):
        try:
            await mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="taskmaster-mcp",
                    server_version="1.0.0",
                    capabilities=mcp_server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
        except Exception as e:
            logger.error("MCP Server Error", error=str(e))

@app.post("/sse")
@app.post("/sse/")
@app.post("/messages")
@app.post("/messages/")
async def handle_messages(request: Request):
    """Unified POST hub for all possible message endpoints to prevent 405 errors"""
    logger.info("POST message received", path=request.url.path)
    await sse.handle_post_request(request.scope, request.receive, request.send)

@app.get("/messages")
@app.get("/messages/")
async def handle_messages_get(request: Request):
    """Helpful GET for messages to debug connectivity"""
    return {"message": "The messages endpoint is for POST requests from the MCP client."}

# --- Standard REST Endpoints for ChatGPT Actions ---

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

# --- Root Welcome Page ---
@app.get("/")
async def root():
    return {
        "name": "Taskmaster MCP Service",
        "status": "online",
        "mcp_endpoint": "/sse",
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    import os
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", help="Run in MCP stdio mode")
    args = parser.parse_args()
    
    # Get port from environment (Render/Cloud) or fallback to 8000
    port = int(os.environ.get("PORT", 8000))
    
    if args.stdio:
        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="taskmaster-mcp",
                        server_version="1.0.0",
                        capabilities=mcp_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        asyncio.run(run_stdio())
    else:
        # Standard FastAPI/Uvicorn run for Web (ChatGPT REST + Cloud MCP SSE)
        logger.info("Starting web server", port=port)
        uvicorn.run(app, host="0.0.0.0", port=port)

