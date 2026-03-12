"""Orchestrator FastAPI service."""

from dotenv import load_dotenv

load_dotenv()

from typing import Any, Dict

from fastapi import FastAPI

from services.orchestrator.api.routes import router

app = FastAPI(title="AI Agent Platform Orchestrator")

app.include_router(router)


@app.get("/health")
def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {"status": "ok"}
