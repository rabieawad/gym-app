from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

from . import models  # noqa: F401  (registers tables on Base.metadata)
from .config import DEFAULT_SECRET, settings
from .database import Base, SessionLocal, engine
from .routers import all_routers
from .seed import seed_builtin_exercises

# Define Prometheus metrics

# HTTP Metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
)

REQUEST_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
)

# Business Metrics
EXERCISES_CREATED = Counter(
    'exercises_created_total',
    'Total exercises created',
)

ACTIVE_USERS = Gauge(
    'active_users',
    'Number of active users',
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production" and settings.secret_key == DEFAULT_SECRET:
        raise RuntimeError("Set SECRET_KEY to a long random value before running in production.")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_builtin_exercises(db)
    # Initialize active users to 0
    ACTIVE_USERS.set(0)
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


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Only track non-metrics endpoints to avoid infinite recursion
    if request.url.path != "/metrics":
        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()

        REQUEST_TIME.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(process_time)

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


for router in all_routers:
    app.include_router(router)

# Serve the static frontend from the same process. Mounted last so /api/* wins.
if settings.frontend_dir and Path(settings.frontend_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
