from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.replace("_", "").isalnum():
            raise ValueError("Username can contain only letters, numbers, and underscores.")
        return cleaned


class UserRead(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    receiver_id: int
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be empty.")
        return cleaned


class MessageRead(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=128)


class AuthResponse(BaseModel):
    token: str
    user: UserRead


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    member_ids: list[int] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class GroupMemberUpdate(BaseModel):
    user_id: int


class GroupRead(BaseModel):
    id: int
    name: str
    created_by: int
    created_at: datetime
    participant_count: int
    members: list[UserRead]


class GroupMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def validate_content_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message content cannot be empty.")
        return cleaned


class GroupMessageRead(BaseModel):
    id: int
    group_id: int
    sender_id: int
    sender_username: str
    content: str
    timestamp: datetime


class GroupInviteCreate(BaseModel):
    username: str = Field(min_length=3, max_length=30)


class GroupInviteRead(BaseModel):
    id: int
    group_id: int
    group_name: str
    inviter_id: int
    inviter_username: str
    invitee_id: int
    status: str
    created_at: datetime

