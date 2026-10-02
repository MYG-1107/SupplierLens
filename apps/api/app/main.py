from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.db import init_db, seed_demo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    seed_demo()
    yield


app = FastAPI(
    title="SupplierLens API",
    version="0.2.0",
    description="Evidence-first supplier verification and procurement risk intelligence API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "supplierlens-api", "version": "0.2.0"}


app.include_router(router)
