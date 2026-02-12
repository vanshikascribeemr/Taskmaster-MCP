from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import structlog
from ..config import settings

logger = structlog.get_logger()

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Mapping table as requested in prompt: user_category_subscriptions
user_category_subscriptions = Table(
    "user_category_subscriptions",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("category_id", Integer), # We store the Taskmaster category_id
    UniqueConstraint("user_id", "category_id", name="uix_user_category")
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)

def init_db():
    try:
        # Check if we are using a real URL or a placeholder
        if "@db" in settings.DATABASE_URL:
            logger.error("Database connection failed: 'db' is a placeholder. Please set a valid DATABASE_URL in Render.")
            return
            
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas synchronized successfully")
    except Exception as e:
        logger.error("Critical: Could not initialize database", error=str(e), url=settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else "N/A")
        # In some cloud environments, we might want to continue even if DB fails 
        # so that non-DB tools can still function.

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
