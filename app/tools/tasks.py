from ..connectors.taskmaster_client import TaskmasterClient
from ..services.summarizer import get_summarized_report
from ..models.schemas import Task

async def get_category_tasks(category_id: int, client: TaskmasterClient, time_window_days: int = 7):
    return await client.get_category_tasks(category_id, time_window_days=time_window_days)

async def get_tasks_by_alias(alias: str, client: TaskmasterClient, time_window_days: int = 7):
    """Search for tasks by alias / provider name."""
    return await client.search_tasks(alias, time_window_days=time_window_days)

async def get_all_blocked_tasks(client: TaskmasterClient):
    """Fetch all blocked tasks for an executive overview."""
    return await client.get_all_blocked_tasks()

async def get_all_overdue_tasks(client: TaskmasterClient):
    """Fetch all overdue tasks for an executive overview."""
    return await client.get_all_overdue_tasks()

async def get_provider_updates(provider_alias: str, client: TaskmasterClient, detail_level: str = "short", time_window_days: int = 7):
    """Fetch and summarize updates for a specific medical provider alias."""
    search_results = await client.search_tasks(provider_alias, time_window_days=time_window_days)
    if not search_results:
        return f"No tasks or updates found for provider '{provider_alias}'."
    
    # Extract tasks for summarization
    tasks = []
    for item in search_results:
        task_data = item["task"]
        t = Task(**task_data)
        tasks.append(t)
    
    label = f"Last {time_window_days} Days" if time_window_days else "All Time"
    return get_summarized_report(f"Provider: {provider_alias}", tasks, detail_level=detail_level, time_window_label=label)

async def get_task_summary(task_id: int, client: TaskmasterClient, detail_level: str = "short", time_window_days: int = None):
    """Fetch and summarize a specific task by its ID."""
    task = await client.get_task_by_id(task_id, time_window_days=time_window_days)
    if not task:
        return f"Task ID {task_id} not found."
    
    from ..services.summarizer import get_single_task_summary
    return get_single_task_summary(task, detail_level=detail_level)
