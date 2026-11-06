from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, bundles, customers, health, networks, orders
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Falaaa API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(networks.router, prefix="/api/v1")
app.include_router(bundles.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
