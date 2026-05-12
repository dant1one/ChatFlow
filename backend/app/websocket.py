from collections import defaultdict
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import SessionLocal
from app.models import GroupMember, UserSession

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> bool:
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            if not self.connections[user_id]:
                self.connections.pop(user_id, None)
                return True
        return False

    async def broadcast_to_users(self, user_ids: list[int], payload: dict) -> None:
        for user_id in user_ids:
            for ws in list(self.connections.get(user_id, set())):
                try:
                    await ws.send_json(payload)
                except RuntimeError:
                    self.disconnect(user_id, ws)

    async def broadcast_presence(self, user_id: int, online: bool) -> None:
        payload = {"type": "presence", "user_id": user_id, "online": online}
        for target_id in list(self.connections.keys()):
            for ws in list(self.connections.get(target_id, set())):
                try:
                    await ws.send_json(payload)
                except RuntimeError:
                    self.disconnect(target_id, ws)

    async def send_online_snapshot(self, websocket: WebSocket) -> None:
        await websocket.send_json(
            {
                "type": "presence_snapshot",
                "online_user_ids": list(self.connections.keys()),
            }
        )


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_updates(websocket: WebSocket, user_id: int) -> None:
    token = websocket.query_params.get("token", "")
    with SessionLocal() as db:
        session = db.scalar(select(UserSession).where(UserSession.token == token))
        if not session or session.user_id != user_id:
            await websocket.close(code=1008)
            return

    await manager.connect(user_id, websocket)
    await manager.send_online_snapshot(websocket)
    await manager.broadcast_presence(user_id, online=True)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            event_type = payload.get("type")
            if event_type == "typing_dm":
                receiver_id = int(payload.get("receiver_id", 0))
                if receiver_id > 0:
                    await manager.broadcast_to_users(
                        [receiver_id],
                        {"type": "typing_dm", "sender_id": user_id},
                    )
            elif event_type == "typing_group":
                group_id = int(payload.get("group_id", 0))
                if group_id > 0:
                    with SessionLocal() as db:
                        member_ids = list(
                            db.scalars(
                                select(GroupMember.user_id).where(GroupMember.group_id == group_id)
                            )
                        )
                    targets = [member_id for member_id in member_ids if member_id != user_id]
                    if targets:
                        await manager.broadcast_to_users(
                            targets,
                            {"type": "typing_group", "sender_id": user_id, "group_id": group_id},
                        )
    except WebSocketDisconnect:
        became_offline = manager.disconnect(user_id, websocket)
        if became_offline:
            await manager.broadcast_presence(user_id, online=False)

