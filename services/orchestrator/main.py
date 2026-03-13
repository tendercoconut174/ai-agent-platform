"""Orchestrator FastAPI service."""

from dotenv import load_dotenv

load_dotenv()

from shared.logging_config import setup_logging

setup_logging()

import logging

from fastapi import FastAPI

from services.orchestrator.api.routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Platform Orchestrator")
app.include_router(router)

logger.info("Orchestrator service started")
