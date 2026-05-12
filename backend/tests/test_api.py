from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_chat.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_user_create_and_duplicate_validation() -> None:
    response = client.post("/auth/register", json={"username": "qa_user", "password": "password123"})
    assert response.status_code == 201
    assert response.json()["user"]["username"] == "qa_user"
    token = response.json()["token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    duplicate = client.post("/auth/register", json={"username": "qa_user", "password": "password123"})
    assert duplicate.status_code == 409


def test_send_message_and_fetch_conversation_and_search() -> None:
    user_1_data = client.post(
        "/auth/register", json={"username": "sender_1", "password": "password123"}
    ).json()
    user_2_data = client.post(
        "/auth/register", json={"username": "receiver_1", "password": "password123"}
    ).json()
    user_1 = user_1_data["user"]
    user_2 = user_2_data["user"]
    token_1 = user_1_data["token"]

    send = client.post(
        "/messages",
        json={"receiver_id": user_2["id"], "content": "hello integration test"},
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert send.status_code == 201

    conversation = client.get(
        f"/messages/conversation?user_a={user_1['id']}&user_b={user_2['id']}",
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert conversation.status_code == 200
    assert len(conversation.json()) == 1

    search = client.get(
        f"/messages/search?user_a={user_1['id']}&user_b={user_2['id']}&query=integration",
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert search.status_code == 200
    assert len(search.json()) == 1

