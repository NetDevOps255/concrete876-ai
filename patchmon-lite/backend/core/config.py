from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
import os


class Settings(BaseSettings):
    database_url: str = "sqlite:////data/patchmon.db"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h

    # API key for curl/external access — set this in .env
    # Generate with: openssl rand -hex 32
    api_key: str = ""

    # Admin password for the UI login screen
    # Stored as bcrypt hash — use scripts/hash_password.py to generate
    admin_password_hash: str = ""
    admin_username: str = "admin"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    proxmox_host: str = ""
    proxmox_token_id: str = ""
    proxmox_token_secret: str = ""
    proxmox_node: str = "pve"

    ssh_default_user: str = "root"
    ssh_connect_timeout: int = 10
    ssh_command_timeout: int = 120

    # Scheduler intervals (seconds)
    patch_check_interval: int = 3600       # 1h
    docker_check_interval: int = 3600
    proxmox_sync_interval: int = 300       # 5m

    # Security — set ALLOWED_ORIGINS in .env for production
    # e.g. ALLOWED_ORIGINS=https://patchmon.yourdomain.com
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate limiting (requests per minute per IP on auth endpoints)
    auth_rate_limit: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

connect_args = {"check_same_thread": False}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
