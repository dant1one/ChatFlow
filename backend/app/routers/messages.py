from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import MessageCreate, MessageRead
from app.services import message_service
from app.websocket import manager

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageRead:
    try:
        message = message_service.send_message(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    message_data = MessageRead.model_validate(message)
    await manager.broadcast_to_users(
        [message.sender_id, message.receiver_id],
        {
            "type": "new_message",
            "message": message_data.model_dump(mode="json"),
        },
    )
    return message_data


@router.get("/conversation", response_model=list[MessageRead])
def get_conversation(
    user_a: int = Query(..., gt=0),
    user_b: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    if current_user.id not in (user_a, user_b):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view conversations you are part of.",
        )
    messages = message_service.get_conversation(db, user_a, user_b)
    return [MessageRead.model_validate(message) for message in messages]


@router.get("/search", response_model=list[MessageRead])
def search_messages(
    user_a: int = Query(..., gt=0),
    user_b: int = Query(..., gt=0),
    query: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageRead]:
    if current_user.id not in (user_a, user_b):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only search conversations you are part of.",
        )
    messages = message_service.search_messages(db, user_a, user_b, query)
    return [MessageRead.model_validate(message) for message in messages]

