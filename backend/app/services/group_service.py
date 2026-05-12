from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas


def _ensure_member(db: Session, group_id: int, user_id: int) -> None:
    membership = db.scalar(
        select(models.GroupMember).where(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id,
        )
    )
    if not membership:
        raise ValueError("User is not a member of this group.")


def create_group(db: Session, current_user_id: int, payload: schemas.GroupCreate) -> models.Group:
    group = models.Group(name=payload.name.strip(), created_by=current_user_id)
    db.add(group)
    db.flush()

    unique_member_ids = set(payload.member_ids + [current_user_id])
    users = list(db.scalars(select(models.User).where(models.User.id.in_(unique_member_ids))))
    found_ids = {user.id for user in users}
    missing = unique_member_ids - found_ids
    if missing:
        raise ValueError("Some users do not exist.")

    for user_id in unique_member_ids:
        db.add(models.GroupMember(group_id=group.id, user_id=user_id))

    db.commit()
    db.refresh(group)
    return group


def get_user_groups(db: Session, user_id: int) -> list[models.Group]:
    return list(
        db.scalars(
            select(models.Group)
            .join(models.GroupMember, models.GroupMember.group_id == models.Group.id)
            .where(models.GroupMember.user_id == user_id)
            .order_by(models.Group.name.asc())
        )
    )


def rename_group(db: Session, group_id: int, current_user_id: int, new_name: str) -> models.Group:
    group = db.get(models.Group, group_id)
    if not group:
        raise ValueError("Group not found.")
    _ensure_member(db, group_id, current_user_id)
    group.name = new_name.strip()
    db.commit()
    db.refresh(group)
    return group


def add_member(db: Session, group_id: int, current_user_id: int, user_id: int) -> None:
    _ensure_member(db, group_id, current_user_id)
    user = db.get(models.User, user_id)
    if not user:
        raise ValueError("User not found.")
    existing = db.scalar(
        select(models.GroupMember).where(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id,
        )
    )
    if existing:
        raise ValueError("User is already in the group.")
    db.add(models.GroupMember(group_id=group_id, user_id=user_id))
    db.commit()


def remove_member(db: Session, group_id: int, current_user_id: int, user_id: int) -> None:
    _ensure_member(db, group_id, current_user_id)
    membership = db.scalar(
        select(models.GroupMember).where(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id,
        )
    )
    if not membership:
        raise ValueError("User is not in the group.")
    db.delete(membership)
    db.commit()


def leave_group(db: Session, group_id: int, current_user_id: int) -> None:
    membership = db.scalar(
        select(models.GroupMember).where(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == current_user_id,
        )
    )
    if not membership:
        raise ValueError("You are not a member of this group.")
    db.delete(membership)
    db.commit()


def list_group_members(db: Session, group_id: int) -> list[models.User]:
    return list(
        db.scalars(
            select(models.User)
            .join(models.GroupMember, models.GroupMember.user_id == models.User.id)
            .where(models.GroupMember.group_id == group_id)
            .order_by(models.User.username.asc())
        )
    )


def send_group_message(db: Session, group_id: int, current_user_id: int, content: str) -> models.GroupMessage:
    _ensure_member(db, group_id, current_user_id)
    message = models.GroupMessage(group_id=group_id, sender_id=current_user_id, content=content.strip())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_group_messages(db: Session, group_id: int, current_user_id: int) -> list[models.GroupMessage]:
    _ensure_member(db, group_id, current_user_id)
    return list(
        db.scalars(
            select(models.GroupMessage)
            .where(models.GroupMessage.group_id == group_id)
            .order_by(models.GroupMessage.timestamp.asc(), models.GroupMessage.id.asc())
        )
    )


def create_invite(db: Session, group_id: int, inviter_id: int, invitee_username: str) -> models.GroupInvite:
    _ensure_member(db, group_id, inviter_id)
    invitee = db.scalar(select(models.User).where(models.User.username == invitee_username.strip()))
    if not invitee:
        raise ValueError("User not found.")
    if invitee.id == inviter_id:
        raise ValueError("You cannot invite yourself.")
    existing_member = db.scalar(
        select(models.GroupMember).where(models.GroupMember.group_id == group_id, models.GroupMember.user_id == invitee.id)
    )
    if existing_member:
        raise ValueError("User is already a group member.")
    pending = db.scalar(
        select(models.GroupInvite).where(
            models.GroupInvite.group_id == group_id,
            models.GroupInvite.invitee_id == invitee.id,
            models.GroupInvite.status == "pending",
        )
    )
    if pending:
        raise ValueError("Pending invite already exists.")
    invite = models.GroupInvite(group_id=group_id, inviter_id=inviter_id, invitee_id=invitee.id, status="pending")
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def get_pending_invites_for_user(db: Session, user_id: int) -> list[models.GroupInvite]:
    return list(
        db.scalars(
            select(models.GroupInvite)
            .where(models.GroupInvite.invitee_id == user_id, models.GroupInvite.status == "pending")
            .order_by(models.GroupInvite.created_at.desc())
        )
    )


def respond_invite(db: Session, invite_id: int, user_id: int, accept: bool) -> models.GroupInvite:
    invite = db.get(models.GroupInvite, invite_id)
    if not invite or invite.invitee_id != user_id:
        raise ValueError("Invite not found.")
    if invite.status != "pending":
        raise ValueError("Invite is no longer pending.")
    if accept:
        membership = db.scalar(
            select(models.GroupMember).where(
                models.GroupMember.group_id == invite.group_id,
                models.GroupMember.user_id == user_id,
            )
        )
        if not membership:
            db.add(models.GroupMember(group_id=invite.group_id, user_id=user_id))
        invite.status = "accepted"
    else:
        invite.status = "declined"
    db.commit()
    db.refresh(invite)
    return invite

