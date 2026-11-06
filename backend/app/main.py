import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, bundles, customers, health, networks, orders
from app.api.routes import admin_auth, admin_operations
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Obia API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.development_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "").strip()
    request.state.request_id = request_id[:100] if request_id else str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(networks.router, prefix="/api/v1")
app.include_router(bundles.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(admin_auth.router, prefix="/api/v1")
app.include_router(admin_operations.router, prefix="/api/v1")
