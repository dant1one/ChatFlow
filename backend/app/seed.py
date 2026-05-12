from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Message, User


def seed_database(db: Session) -> None:
    users_count = db.scalar(select(func.count()).select_from(User)) or 0
    if users_count > 0:
        return

    alice = User(username="alice")
    bob = User(username="bob")
    clara = User(username="clara")
    db.add_all([alice, bob, clara])
    db.flush()

    db.add_all(
        [
            Message(sender_id=alice.id, receiver_id=bob.id, content="Hi Bob, welcome to the chat!"),
            Message(sender_id=bob.id, receiver_id=alice.id, content="Thanks Alice, this looks great."),
            Message(sender_id=clara.id, receiver_id=alice.id, content="Hello Alice, are you available today?"),
        ]
    )
    db.commit()

