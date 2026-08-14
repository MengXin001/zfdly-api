import json
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, BeforeValidator, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors(value: Any) -> list[str] | str:
    if isinstance(value, str) and not value.startswith("["):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class AdminUser(BaseModel):
    phone: str
    name: str
    password: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    API_V1_STR: str = "/api"
    SECRET_KEY: SecretStr
    ENVIRONMENT: Literal["local", "staging", "production"] = "production"
    DATABASE_URL: str = "sqlite:///./app.db"
    UPLOAD_DIR: str = "data/uploads"
    SESSION_MAX_AGE_SECONDS: int = 60 * 60 * 24 * 14
    ADMIN_USERS: SecretStr
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

    @computed_field
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    @property
    def admin_users(self) -> list[AdminUser]:
        try:
            raw_users = json.loads(self.ADMIN_USERS.get_secret_value())
        except json.JSONDecodeError as exc:
            raise ValueError("ADMIN_USERS must be a JSON array") from exc
        return [AdminUser.model_validate(item) for item in raw_users]

    @property
    def session_cookie_secure(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
