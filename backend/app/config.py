from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Realtime Chat API"
    database_url: str = "sqlite:///./chat.db"
    allowed_origins: list[str] = ["*"]


settings = Settings()

