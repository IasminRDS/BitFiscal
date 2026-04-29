from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "segredo"
    DATABASE_URL: str = "sqlite:///./bitfiscal.db"
    BACKUP_SOURCE_DIRS: str = ""
    BACKUP_DEST_DIR: str = ""
    RSYNC_OPTIONS: str = "-avz --delete"
    MONITOR_HOSTS: str = ""
    MONITOR_SERVICES: str = ""
    MONITOR_INTERVAL: int = 300
    USAGE_HOSTS_FILE: str = "/etc/hosts"
    USAGE_BACKUP_FILE: str = "/etc/hosts.bak"
    KNOWLEDGE_BASE_FILE: str = "data/base_conhecimento.json"
    COOKIE_SECURE: bool = False
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
