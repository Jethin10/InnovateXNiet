from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import Settings, build_settings
from app.db.management import initialize_database
from app.db.session import create_session_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database(app.state.engine)
    yield


def create_app(overrides: dict[str, str] | None = None) -> FastAPI:
    settings: Settings = build_settings(overrides)
    session_factory = create_session_factory(settings.database_url)
    engine = session_factory.kw["bind"]
    initialize_database(engine)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
