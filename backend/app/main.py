"""Roomora AI API: the application factory.

Run locally:   uvicorn app.main:app --reload     then open http://127.0.0.1:8000/docs
Database tables come from Alembic migrations (`alembic upgrade head`), never from create_all.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.routers import admin, ai, auth, designers, designs, files, orders, products

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Roomora AI API",
        description="Backend for Roomora AI: login, furniture, designers, orders and the AI editor.",
        version="2.0.0",
    )

    # Browsers only let a page call an API on another origin if the API allows it.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (
        auth.router,
        products.router,
        designers.router,
        designers.bookings_router,
        orders.router,
        designs.router,
        ai.router,
        admin.router,
        files.router,
    ):
        app.include_router(router)

    if not settings.use_supabase_storage:
        # Local development only: expose the PUBLIC bucket. The private bucket is never mounted.
        public_dir = Path(settings.media_dir) / settings.public_bucket
        public_dir.mkdir(parents=True, exist_ok=True)
        app.mount(f"/media/{settings.public_bucket}", StaticFiles(directory=public_dir), name="media")

    @app.get("/health", tags=["Health"])
    def health():
        """Used by Railway's health check. Also confirms the database answers."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "error", "database": "unreachable"})
        return {"status": "ok", "database": "ok", "environment": settings.environment}

    @app.get("/", tags=["Health"])
    def home():
        return {"app": "Roomora AI API", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
