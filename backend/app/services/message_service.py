from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app import models, schemas


def send_message(db: Session, sender_id: int, payload: schemas.MessageCreate) -> models.Message:
    sender = db.get(models.User, sender_id)
    receiver = db.get(models.User, payload.receiver_id)
    if not sender or not receiver:
        raise ValueError("Sender or receiver does not exist.")
    if sender_id == payload.receiver_id:
        raise ValueError("Sender and receiver cannot be the same user.")

    message = models.Message(
        sender_id=sender_id,
        receiver_id=payload.receiver_id,
        content=payload.content.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation(db: Session, user_a: int, user_b: int) -> list[models.Message]:
    return list(
        db.scalars(
            select(models.Message)
            .where(
                or_(
                    and_(models.Message.sender_id == user_a, models.Message.receiver_id == user_b),
                    and_(models.Message.sender_id == user_b, models.Message.receiver_id == user_a),
                )
            )
            .order_by(models.Message.timestamp.asc(), models.Message.id.asc())
        )
    )


def search_messages(db: Session, user_a: int, user_b: int, query: str) -> list[models.Message]:
    pattern = f"%{query.strip()}%"
    return list(
        db.scalars(
            select(models.Message)
            .where(
                or_(
                    and_(models.Message.sender_id == user_a, models.Message.receiver_id == user_b),
                    and_(models.Message.sender_id == user_b, models.Message.receiver_id == user_a),
                )
            )
            .where(models.Message.content.ilike(pattern))
            .order_by(models.Message.timestamp.asc(), models.Message.id.asc())
        )
    )

