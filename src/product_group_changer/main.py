"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from product_group_changer.api.routes import health, product_groups
from product_group_changer.config import get_settings
from product_group_changer.dependencies import AppState


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()

    # Initialize application state
    app.state.app_state = AppState(settings=settings)
    await app.state.app_state.initialize()

    yield

    # Cleanup
    await app.state.app_state.cleanup()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Product Group Changer",
        description="API for bulk product group management in P21 inventory items",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(product_groups.router, prefix="/api", tags=["Product Groups"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "product_group_changer.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )
