from sqlalchemy.orm import Session
from ..connectors.db import User, user_category_subscriptions
from sqlalchemy import select, insert, delete

async def list_user_subscriptions(user_email: str, db: Session):
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    # Query the mapping table
    query = select(user_category_subscriptions.c.category_id).where(user_category_subscriptions.c.user_id == user.id)
    result = db.execute(query).scalars().all()
    return list(result)

async def subscribe_category(user_email: str, category_id: int, db: Session):
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Check if already subscribed
    query = select(user_category_subscriptions).where(
        user_category_subscriptions.c.user_id == user.id,
        user_category_subscriptions.c.category_id == category_id
    )
    existing = db.execute(query).first()
    if not existing:
        stmt = insert(user_category_subscriptions).values(user_id=user.id, category_id=category_id)
        db.execute(stmt)
        db.commit()
    return {"status": "success", "message": f"Subscribed {user_email} to category {category_id}"}

async def unsubscribe_category(user_email: str, category_id: int, db: Session):
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    
    stmt = delete(user_category_subscriptions).where(
        user_category_subscriptions.c.user_id == user.id,
        user_category_subscriptions.c.category_id == category_id
    )
    db.execute(stmt)
    db.commit()
    return {"status": "success", "message": f"Unsubscribed {user_email} from category {category_id}"}
