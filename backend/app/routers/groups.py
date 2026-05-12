from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    GroupCreate,
    GroupInviteCreate,
    GroupInviteRead,
    GroupMemberUpdate,
    GroupMessageCreate,
    GroupMessageRead,
    GroupRead,
    GroupUpdate,
    UserRead,
)
from app.services import group_service
from app.websocket import manager

router = APIRouter(prefix="/groups", tags=["groups"])


def _to_group_read(db: Session, group) -> GroupRead:
    members = group_service.list_group_members(db, group.id)
    return GroupRead(
        id=group.id,
        name=group.name,
        created_by=group.created_by,
        created_at=group.created_at,
        participant_count=len(members),
        members=[UserRead.model_validate(member) for member in members],
    )


def _to_invite_read(invite) -> GroupInviteRead:
    return GroupInviteRead(
        id=invite.id,
        group_id=invite.group_id,
        group_name=invite.group.name,
        inviter_id=invite.inviter_id,
        inviter_username=invite.inviter.username,
        invitee_id=invite.invitee_id,
        status=invite.status,
        created_at=invite.created_at,
    )


@router.get("", response_model=list[GroupRead])
def get_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupRead]:
    groups = group_service.get_user_groups(db, current_user.id)
    return [_to_group_read(db, group) for group in groups]


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    try:
        group = group_service.create_group(db, current_user.id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_group_read(db, group)


@router.patch("/{group_id}", response_model=GroupRead)
def rename_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    try:
        group = group_service.rename_group(db, group_id, current_user.id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_group_read(db, group)


@router.post("/{group_id}/members", status_code=status.HTTP_204_NO_CONTENT)
def add_member(
    group_id: int,
    payload: GroupMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        group_service.add_member(db, group_id, current_user.id, payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        group_service.remove_member(db, group_id, current_user.id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        group_service.leave_group(db, group_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{group_id}/messages", response_model=list[GroupMessageRead])
def get_group_messages(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupMessageRead]:
    try:
        messages = group_service.get_group_messages(db, group_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [
        GroupMessageRead(
            id=message.id,
            group_id=message.group_id,
            sender_id=message.sender_id,
            sender_username=message.sender.username,
            content=message.content,
            timestamp=message.timestamp,
        )
        for message in messages
    ]


@router.post("/{group_id}/messages", response_model=GroupMessageRead, status_code=status.HTTP_201_CREATED)
async def send_group_message(
    group_id: int,
    payload: GroupMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupMessageRead:
    try:
        message = group_service.send_group_message(db, group_id, current_user.id, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    members = group_service.list_group_members(db, group_id)
    data = GroupMessageRead(
        id=message.id,
        group_id=message.group_id,
        sender_id=message.sender_id,
        sender_username=current_user.username,
        content=message.content,
        timestamp=message.timestamp,
    )
    await manager.broadcast_to_users(
        [member.id for member in members],
        {"type": "new_group_message", "message": data.model_dump(mode="json")},
    )
    return data


@router.get("/invites/pending", response_model=list[GroupInviteRead])
def get_pending_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupInviteRead]:
    invites = group_service.get_pending_invites_for_user(db, current_user.id)
    return [_to_invite_read(invite) for invite in invites]


@router.post("/{group_id}/invites", response_model=GroupInviteRead, status_code=status.HTTP_201_CREATED)
async def invite_user(
    group_id: int,
    payload: GroupInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupInviteRead:
    try:
        invite = group_service.create_invite(db, group_id, current_user.id, payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    data = _to_invite_read(invite)
    await manager.broadcast_to_users(
        [invite.invitee_id],
        {"type": "group_invite", "invite": data.model_dump(mode="json")},
    )
    return data


@router.post("/invites/{invite_id}/accept", response_model=GroupInviteRead)
async def accept_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupInviteRead:
    try:
        invite = group_service.respond_invite(db, invite_id, current_user.id, accept=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    data = _to_invite_read(invite)
    await manager.broadcast_to_users(
        [invite.inviter_id],
        {"type": "group_invite_response", "invite": data.model_dump(mode="json")},
    )
    return data


@router.post("/invites/{invite_id}/decline", response_model=GroupInviteRead)
async def decline_invite(
    invite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupInviteRead:
    try:
        invite = group_service.respond_invite(db, invite_id, current_user.id, accept=False)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    data = _to_invite_read(invite)
    await manager.broadcast_to_users(
        [invite.inviter_id],
        {"type": "group_invite_response", "invite": data.model_dump(mode="json")},
    )
    return data

