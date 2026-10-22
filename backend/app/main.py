from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, invoices
from app.core.config import get_settings
from app.services.storage import S3Storage, get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = get_storage()
    if isinstance(storage, S3Storage):
        storage.ensure_bucket()
    yield


app = FastAPI(title="FinQuery API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
