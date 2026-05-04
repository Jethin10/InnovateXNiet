from __future__ import annotations

import os

from pydantic import BaseModel


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "http://localhost:3003",
    "http://127.0.0.1:3003",
    "http://localhost:3004",
    "http://127.0.0.1:3004",
    "https://innovate-x-niet.vercel.app",
]

DEFAULT_CORS_ORIGIN_REGEX = r"^https://innovate-x-niet(?:-[a-z0-9-]+)?-jethin10s-projects\.vercel\.app$"


def _cors_origins() -> list[str]:
    configured = _csv_env("CORS_ORIGINS", "")
    return sorted(set(DEFAULT_CORS_ORIGINS + configured))


class Settings(BaseModel):
    app_name: str = "placement-trust-backend"
    app_env: str = "development"
    database_url: str = "sqlite:///./placement_trust.db"
    app_version: str = "0.2.0"
    model_artifact_path: str = "artifacts/trust_model.joblib"
    docs_enabled: bool = True
    auth_secret_key: str = "change-me-in-production"
    access_token_ttl_seconds: int = 3600
    admin_registration_key: str = "change-me-admin-key"
    github_token: str | None = None
    github_max_repositories: int = 100
    github_max_enriched_repositories: int = 5
    judge0_base_url: str | None = None
    judge0_api_key: str | None = None
    judge0_auth_token: str | None = None
    judge0_python_language_id: int = 71
    huggingface_api_token: str | None = None
    huggingface_proctoring_model: str = "facebook/detr-resnet-50"
    huggingface_proctoring_disabled: bool = False
    rapidapi_key: str | None = None
    jsearch_host: str = "jsearch.p.rapidapi.com"
    cors_origins: list[str] = []
    cors_origin_regex: str | None = None

def build_settings(overrides: dict[str, str] | None = None) -> Settings:
    values = {
        "app_name": os.getenv("APP_NAME", "placement-trust-backend"),
        "app_env": os.getenv("APP_ENV", "development"),
        "database_url": os.getenv("DATABASE_URL", "sqlite:///./placement_trust.db"),
        "app_version": os.getenv("APP_VERSION", "0.2.0"),
        "model_artifact_path": os.getenv("MODEL_ARTIFACT_PATH", "artifacts/trust_model.joblib"),
        "docs_enabled": os.getenv("DOCS_ENABLED", "true").lower() == "true",
        "auth_secret_key": os.getenv("AUTH_SECRET_KEY", "change-me-in-production"),
        "access_token_ttl_seconds": int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600")),
        "admin_registration_key": os.getenv("ADMIN_REGISTRATION_KEY", "change-me-admin-key"),
        "github_token": os.getenv("GITHUB_TOKEN") or None,
        "github_max_repositories": int(os.getenv("GITHUB_MAX_REPOSITORIES", "100")),
        "github_max_enriched_repositories": int(os.getenv("GITHUB_MAX_ENRICHED_REPOSITORIES", "5")),
        "judge0_base_url": os.getenv("JUDGE0_BASE_URL") or None,
        "judge0_api_key": os.getenv("JUDGE0_API_KEY") or None,
        "judge0_auth_token": os.getenv("JUDGE0_AUTH_TOKEN") or None,
        "judge0_python_language_id": int(os.getenv("JUDGE0_PYTHON_LANGUAGE_ID", "71")),
        "huggingface_api_token": os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN") or None,
        "huggingface_proctoring_model": os.getenv("HUGGINGFACE_PROCTORING_MODEL", "facebook/detr-resnet-50"),
        "huggingface_proctoring_disabled": os.getenv("HUGGINGFACE_PROCTORING_DISABLED", "false").lower() == "true",
        "rapidapi_key": os.getenv("RAPIDAPI_KEY") or os.getenv("JSEARCH_API_KEY") or None,
        "jsearch_host": os.getenv("JSEARCH_HOST", "jsearch.p.rapidapi.com"),
        "cors_origins": _cors_origins(),
        "cors_origin_regex": os.getenv("CORS_ORIGIN_REGEX") or DEFAULT_CORS_ORIGIN_REGEX,
    }
    if overrides:
        values.update(overrides)
    return Settings(**values)
