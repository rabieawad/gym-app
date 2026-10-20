from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from . import models  # noqa: F401  (registers tables on Base.metadata)
from .config import DEFAULT_SECRET, settings
from .database import Base, SessionLocal, engine
from .routers import all_routers
from .seed import seed_builtin_exercises


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production" and settings.secret_key == DEFAULT_SECRET:
        raise RuntimeError("Set SECRET_KEY to a long random value before running in production.")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_builtin_exercises(db)
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

for router in all_routers:
    app.include_router(router)

# Serve the static frontend from the same process. Mounted last so /api/* wins.
if settings.frontend_dir and Path(settings.frontend_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
