import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TASKMASTER_API_URL: str = "https://hrms.scribeemr.com/api/HrmsWebApi"
    TASKMASTER_API_KEY: str = ""
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/newsletter"
    CACHE_TTL: int = 300
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"

settings = Settings()
