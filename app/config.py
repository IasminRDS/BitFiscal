from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str
    SECRET_KEY: str
    ADMIN_USER: str
    ADMIN_PASS: str
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    COOKIE_SECURE: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
