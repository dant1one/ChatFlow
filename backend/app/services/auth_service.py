from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.security import generate_token, hash_password, verify_password


def register_user(db: Session, payload: schemas.UserCreate) -> tuple[models.User, str]:
    existing = db.scalar(select(models.User).where(models.User.username == payload.username))
    if existing:
        raise ValueError("Username already exists.")

    user = models.User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    token = generate_token()
    session = models.UserSession(user_id=user.id, token=token)
    db.add(session)
    db.commit()
    db.refresh(user)
    return user, token


def login_user(db: Session, payload: schemas.LoginRequest) -> tuple[models.User, str]:
    user = db.scalar(select(models.User).where(models.User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise ValueError("Invalid username or password.")

    token = generate_token()
    session = models.UserSession(user_id=user.id, token=token)
    db.add(session)
    db.commit()
    return user, token

