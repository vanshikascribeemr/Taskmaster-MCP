from ..connectors.taskmaster_client import TaskmasterClient
from ..services.summarizer import get_summarized_report
from .subscriptions import list_user_subscriptions
from sqlalchemy.orm import Session

async def get_weekly_summary(category_id: int, client: TaskmasterClient):
    # Fetch category info to get name
    categories = await client.get_all_categories()
    category = next((c for c in categories if c.id == category_id), None)
    category_name = category.name if category else f"Category {category_id}"
    
    tasks = await client.get_category_tasks(category_id)
    return get_summarized_report(category_name, tasks)

async def preview_newsletter(user_email: str, client: TaskmasterClient, db: Session):
    # 1. Get subscriptions
    category_ids = await list_user_subscriptions(user_email, db)
    if not category_ids:
        return {"message": "User has no subscriptions"}
    
    # 2. Fetch categories info
    all_categories = await client.get_all_categories()
    
    # 3. For each subscription, fetch tasks and summarize
    preview = []
    for cat_id in category_ids:
        cat_info = next((c for c in all_categories if c.id == cat_id), None)
        cat_name = cat_info.name if cat_info else f"Category {cat_id}"
        
        tasks = await client.get_category_tasks(cat_id)
        summary = get_summarized_report(cat_name, tasks)
        
        preview.append({
            "category_id": cat_id,
            "category_name": cat_name,
            "summary": summary
        })
    
    return {
        "user_email": user_email,
        "newsletter_preview": preview
    }
