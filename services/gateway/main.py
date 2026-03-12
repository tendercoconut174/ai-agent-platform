"""FastAPI gateway service."""

from dotenv import load_dotenv

load_dotenv()

from typing import Dict, Any

from fastapi import FastAPI

from services.gateway.api.routes import router

app = FastAPI(title="AI Agent Platform Gateway")

app.include_router(router)


@app.get("/health")
def health() -> Dict[str, Any]:
    """Health check endpoint.

    Returns:
        Status dict indicating service health.
    """
    return {"status": "ok"}
