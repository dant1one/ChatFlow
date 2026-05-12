from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def get_users(db: Session) -> list[models.User]:
    return list(db.scalars(select(models.User).order_by(models.User.username.asc())))


def search_users(db: Session, query: str) -> list[models.User]:
    pattern = f"%{query.strip()}%"
    return list(
        db.scalars(
            select(models.User).where(models.User.username.ilike(pattern)).order_by(models.User.username.asc())
        )
    )


def get_user_by_id(db: Session, user_id: int) -> models.User | None:
    return db.get(models.User, user_id)

