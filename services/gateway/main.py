"""FastAPI gateway service."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from shared.logging_config import setup_logging

setup_logging()

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from services.gateway.api.routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Platform Gateway")
app.include_router(router)

# Serve UI static files
ui_dir = Path(__file__).resolve().parent.parent.parent / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")


@app.get("/")
def root():
    """Redirect to test UI."""
    return RedirectResponse(url="/ui/")

logger.info("Gateway service started")


@app.get("/health")
def health():
    return {"status": "ok"}
