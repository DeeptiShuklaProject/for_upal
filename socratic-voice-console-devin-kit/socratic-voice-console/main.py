"""FastAPI entry point for the Socratic Voice Console."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from professor_qa import __version__
from professor_qa.knowledge import UnknownKnowledgeModule
from professor_qa.middleware import (
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)
from professor_qa.models import AskRequest, AskResponse, ConfigResponse, HealthResponse
from professor_qa.service import ProfessorService

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def create_app(service: ProfessorService | None = None) -> FastAPI:
    application = FastAPI(
        title="Socratic Voice Console",
        summary="Grounded professor Q&A with local and cloud voice providers.",
        version=__version__,
    )
    application.state.service = service or ProfessorService.from_env()
    application.add_middleware(RequestBodyLimitMiddleware, max_bytes=32 * 1024)
    application.add_middleware(GZipMiddleware, minimum_size=1024)
    application.add_middleware(SecurityHeadersMiddleware)
    application.mount(
        "/static", StaticFiles(directory=ROOT_DIR / "static"), name="static"
    )

    @application.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(ROOT_DIR / "index.html")

    @application.get("/api/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return application.state.service.health()

    @application.get("/api/config", response_model=ConfigResponse, tags=["system"])
    async def configuration() -> ConfigResponse:
        return application.state.service.configuration()

    @application.post("/api/ask", response_model=AskResponse, tags=["professor"])
    async def ask(payload: AskRequest) -> AskResponse:
        try:
            return await application.state.service.ask(payload)
        except UnknownKnowledgeModule as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
