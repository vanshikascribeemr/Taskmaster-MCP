import httpx
import os
import datetime
import structlog
import asyncio
from typing import List, Dict, Optional
from ..models.schemas import Task, CategoryBrief

from ..config import settings

logger = structlog.get_logger()

class TaskmasterClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or settings.TASKMASTER_API_URL
        self.api_key = api_key or settings.TASKMASTER_API_KEY
        self._cache = {}
        self.cache_ttl = settings.CACHE_TTL

    def _get_auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def get_all_categories(self) -> List[CategoryBrief]:
        """Fetch all categories from Taskmaster."""
        cache_key = "categories"
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return data

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/GetAllCategories",
                    headers=self._get_auth_header(),
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                raw_cats = []
                if isinstance(data, list):
                    raw_cats = data
                elif isinstance(data, dict):
                    raw_cats = data.get("Data", data.get("categories", []))
                
                categories = []
                for cat in raw_cats:
                    cat_id = cat.get("TaskCategoryId") or cat.get("CategoryId")
                    cat_name = cat.get("TaskCategoryName") or cat.get("CategoryName")
                    if cat_id and cat_name:
                        categories.append(CategoryBrief(id=cat_id, name=cat_name))
                
                self._cache[cache_key] = (categories, datetime.datetime.now())
                return categories
            except Exception as e:
                logger.error("Failed to fetch categories", error=str(e))
                return []

    async def get_category_tasks(self, category_id: int) -> List[Task]:
        """Fetch tasks for a specific category."""
        cache_key = f"tasks_{category_id}"
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return data

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/GetCategoryTasks",
                    params={"CategoryId": category_id},
                    headers=self._get_auth_header()
                )
                response.raise_for_status()
                data = response.json()
                
                tasks_list = []
                if isinstance(data, list):
                    tasks_list = data
                elif isinstance(data, dict):
                    tasks_list = data.get("Data") or data.get("tasks") or []

                tasks = [Task(**t) for t in tasks_list]
                
                # Fetch comments for each task to enable summarization
                await asyncio.gather(*[self._enrich_task_comments(client, t) for t in tasks])
                self._cache[cache_key] = (tasks, datetime.datetime.now())
                return tasks
            except Exception as e:
                logger.error("Failed to fetch tasks", category_id=category_id, error=str(e))
                return []

    async def search_tasks(self, query: str) -> List[Dict]:
        """Search for tasks matching a query across all categories."""
        categories = await self.get_all_categories()
        query = query.lower()
        
        # We only search categories that are likely to contain provider info or are active
        # To avoid massive latency, we might prioritize categories or use a concurrency limit
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_and_filter(cat):
            async with semaphore:
                tasks = await self.get_category_tasks(cat.id)
                matches = []
                for t in tasks:
                    if query in t.taskSubject.lower() or (t.assigneeName and query in t.assigneeName.lower()):
                        matches.append({
                            "category": cat.name,
                            "task": t.model_dump(by_alias=True)
                        })
                return matches

        results = await asyncio.gather(*[fetch_and_filter(cat) for cat in categories])
        # Flatten the list
        flat_results = [item for sublist in results for item in sublist]
        return flat_results

    async def get_all_blocked_tasks(self) -> List[Dict]:
        """Fetch all tasks that are currently blocked across all categories."""
        categories = await self.get_all_categories()
        
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_blocked(cat):
            async with semaphore:
                tasks = await self.get_category_tasks(cat.id)
                blocks = []
                for t in tasks:
                    status = t.taskStatus.lower()
                    # Filter for statuses that imply being blocked or on hold
                    if "blocked" in status or "hold" in status or "stopped" in status:
                        blocks.append({
                            "category": cat.name,
                            "task": t.model_dump(by_alias=True)
                        })
                return blocks

        results = await asyncio.gather(*[fetch_blocked(cat) for cat in categories])
        return [item for sublist in results for item in sublist]

    async def get_all_overdue_tasks(self) -> List[Dict]:
        """Fetch all tasks that are currently overdue across all categories."""
        categories = await self.get_all_categories()
        
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_overdue(cat):
            async with semaphore:
                tasks = await self.get_category_tasks(cat.id)
                overdue = []
                for t in tasks:
                    # Check the daysOverdue field
                    if t.daysOverdue and t.daysOverdue > 0:
                        overdue.append({
                            "category": cat.name,
                            "task": t.model_dump(by_alias=True)
                        })
                return overdue

        results = await asyncio.gather(*[fetch_overdue(cat) for cat in categories])
        return [item for sublist in results for item in sublist]

    async def _enrich_task_comments(self, client: httpx.AsyncClient, task: Task):
        """Fetch last 7 days of comments for a task."""
        try:
            response = await client.post(
                f"{self.base_url}/GetTaskFollowUpHistory",
                json={"TaskId": task.taskId, "PageSize": 20},
                headers={"Content-Type": "application/json", **self._get_auth_header()},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                history = []
                if isinstance(data, dict):
                    inner = data.get("Data", {})
                    history = (inner.get("FollowUpHistoryDetails", []) if isinstance(inner, dict) 
                               else (data.get("FollowUpHistoryDetails", []) if isinstance(data.get("FollowUpHistoryDetails"), list) else []))
                
                # Filter for last 7 days and format
                threshold = datetime.datetime.now() - datetime.timedelta(days=7)
                comments = []
                for item in history:
                    try:
                        date_str = (item.get("FollowUpDate") or "").replace("Z", "")
                        if "." in date_str:
                            date_str = date_str.split(".")[0]
                        f_date = datetime.datetime.fromisoformat(date_str)
                        if f_date >= threshold:
                            text = item.get("TaskFollowUpComments") or item.get("FollowUpComment")
                            if text:
                                comments.append(text)
                    except:
                        continue
                task.followUpComments = comments
        except Exception as e:
            logger.warning("Failed to enrich task comments", task_id=task.taskId, error=str(e))
