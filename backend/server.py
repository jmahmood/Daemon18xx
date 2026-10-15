"""ASGI application. Run from the repository root with uvicorn backend.server:app."""

import os
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import db
from backend.rules1830_api import router as rules1830_router
from backend.rules1889_api import router as rules1889_router


@asynccontextmanager
async def lifespan(app):
    db.db_path.parent.mkdir(parents=True, exist_ok=True)
    await db.initialize()
    yield


app = FastAPI(
    title="Daemon18xx",
    description="Authoritative Python rules and persistent HTTP games for 1830 and 1889.",
    lifespan=lifespan,
)
origins = [
    origin.strip()
    for origin in os.environ.get("DAEMON18XX_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(rules1830_router)
app.include_router(rules1889_router)


@app.get("/", tags=["service"])
async def service():
    return {"service": "Daemon18xx", "variants": ["1830", "1889"], "docs": "/docs"}


@app.get("/health", tags=["service"])
async def health():
    """Check that the existing database and its schema can be read."""
    try:
        async with aiosqlite.connect(
            db.db_path.resolve().as_uri() + "?mode=rw", uri=True
        ) as connection:
            await connection.execute("SELECT id FROM games LIMIT 1")
    except aiosqlite.Error as error:
        raise HTTPException(503, "Database unavailable") from error
    return {"status": "ok"}
