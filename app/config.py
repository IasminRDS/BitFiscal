from pydantic_settings import BaseSettings
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    # 🔐 JWT
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # 🗄️ Database
    DATABASE_URL: str = "sqlite:///./bitfiscal.db"

    # 🌐 App
    APP_NAME: str = "BITFISCAL - Gestão Contábil"  # ← ALTERADO
    DEBUG: bool = True

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
