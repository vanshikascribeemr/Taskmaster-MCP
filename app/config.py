import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TASKMASTER_API_URL: str = os.getenv("TASKMASTER_API_URL", "https://hrms.scribeemr.com/api/HrmsWebApi")
    TASKMASTER_API_KEY: str = os.getenv("TASKMASTER_API_KEY", "")
    MCP_API_KEY: str = os.getenv("MCP_API_KEY", "")
    _database_url: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/newsletter")
    CACHE_TTL: int = 300
    LOG_LEVEL: str = "info"

    @property
    def DATABASE_URL(self) -> str:
        # Render provides postgres:// but SQLAlchemy requires postgresql://
        url = self._database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
