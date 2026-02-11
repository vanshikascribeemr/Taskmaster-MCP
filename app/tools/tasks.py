from ..connectors.taskmaster_client import TaskmasterClient
from ..services.summarizer import get_summarized_report
from ..models.schemas import Task

async def get_category_tasks(category_id: int, client: TaskmasterClient):
    return await client.get_category_tasks(category_id)

async def get_tasks_by_alias(alias: str, client: TaskmasterClient):
    """Search for tasks by alias / provider name."""
    return await client.search_tasks(alias)

async def get_all_blocked_tasks(client: TaskmasterClient):
    """Fetch all blocked tasks for an executive overview."""
    return await client.get_all_blocked_tasks()

async def get_all_overdue_tasks(client: TaskmasterClient):
    """Fetch all overdue tasks for an executive overview."""
    return await client.get_all_overdue_tasks()

async def get_provider_updates(provider_alias: str, client: TaskmasterClient):
    """Fetch and summarize updates for a specific medical provider alias."""
    search_results = await client.search_tasks(provider_alias)
    if not search_results:
        return f"No tasks or updates found for provider '{provider_alias}'."
    
    # Extract tasks for summarization
    tasks = []
    for item in search_results:
        task_data = item["task"]
        # Convert back to Task object for summarizer (Task object uses field aliases for construction if populate_by_name is true)
        # Note: model_dump(by_alias=True) returns keys like 'TaskId', 'SubjectLine'
        # Task class expects these as aliases and will map them to taskId, taskSubject
        t = Task(**task_data)
        tasks.append(t)
    
    return get_summarized_report(f"Provider: {provider_alias}", tasks)
