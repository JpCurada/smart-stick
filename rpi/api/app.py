"""FastAPI app factory."""

from __future__ import annotations

from fastapi import FastAPI

from api.dependencies import Container, build_container, set_container
from api.middleware import install_middleware
from api.routes import router
from utils.logger import get_logger


def create_app(container: Container | None = None) -> FastAPI:
    """Build the FastAPI app and wire startup / shutdown hooks."""
    app = FastAPI(
        title="Smart Stick API",
        version="1.1.0",
        description="Local HTTP API exposed by the Smart Stick RPi backend.",
    )
    install_middleware(app)
    app.include_router(router)

    log = get_logger("api.app")
    state_container = container or build_container()
    set_container(state_container)
    app.state.container = state_container

    @app.on_event("startup")
    def _startup() -> None:
        log.info("starting Smart Stick services")
        state_container.session_service.start()
        state_container.start_all()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        log.info("shutting down Smart Stick services")
        state_container.session_service.end()
        state_container.stop_all()

    return app
