"""FastAPI application factory and ASGI entry point."""

from contextlib import asynccontextmanager
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from .api import router
from .database import (
    create_database_engine,
    create_session_factory,
    get_database_url,
)
from .execution.docker_runner import DockerRunner
from .request_limits import SubmissionBodyLimitMiddleware
from .seed import seed_initial_data
from .services.evaluation_service import ExecutionRunner, EvaluationService


def create_app(
    database_url: Optional[str] = None,
    *,
    seed_data: bool = True,
    execution_runner: Optional[ExecutionRunner] = None,
) -> FastAPI:
    """Create an app with its own engine, session factory, and catalog seed."""
    engine = create_database_engine(database_url or get_database_url())
    session_factory: sessionmaker = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if seed_data:
            with session_factory() as session:
                seed_initial_data(session)
        yield
        engine.dispose()

    app = FastAPI(
        title="Python Code Evaluator API",
        version="3.0.0",
        description=(
            "Exercise catalog and Docker-isolated Python evaluation API. "
            "Untrusted source is never run in this application process."
        ),
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.evaluation_service = EvaluationService(execution_runner or DockerRunner())
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Accept", "Content-Type"],
            allow_credentials=False,
        )
    app.add_middleware(SubmissionBodyLimitMiddleware)
    app.include_router(router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Basic process health check; database readiness is checked by requests."""
        return {"status": "ok"}

    return app


app = create_app()
