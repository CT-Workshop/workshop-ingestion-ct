import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.routes import documents, health
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.getLogger(__name__).info("Starting %s v%s env=%s", settings.app_name, __version__, settings.environment)
    yield
    logging.getLogger(__name__).info("Shutdown %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(documents.router)
    return app


app = create_app()
