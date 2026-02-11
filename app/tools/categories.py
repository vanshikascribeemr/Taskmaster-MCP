from ..connectors.taskmaster_client import TaskmasterClient

async def get_categories(client: TaskmasterClient):
    return await client.get_all_categories()
