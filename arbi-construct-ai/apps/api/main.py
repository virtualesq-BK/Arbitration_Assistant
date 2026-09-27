"""ArbiConstruct AI — FastAPI application factory."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1 import api_router
from core.config import settings

DISCLAIMER = (
    "ArbiConstruct AI provides AI-assisted information management and research. It does not provide "
    "legal advice or legal representation. AI outputs must be reviewed by qualified legal professionals."
)


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = FastAPI(
        title="ArbiConstruct AI API",
        version="0.1.0",
        description="International construction arbitration case management.\n\n" + DISCLAIMER,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "model": settings.OPENAI_MODEL}

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"name": "ArbiConstruct AI API", "docs": "/docs", "disclaimer": DISCLAIMER}

    return app


app = create_app()
