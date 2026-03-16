"""FastAPI gateway service."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from shared.logging_config import setup_logging

setup_logging()

import logging

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from services.gateway.api.routes import router
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, get_metrics

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


@app.get("/health")
def health():
    """Liveness probe - service is running."""
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe - dependencies (DB) are reachable."""
    import asyncio
    try:
        from services.gateway.session_manager import _check_db
        db_ok = await asyncio.to_thread(_check_db)
        return {"status": "ready", "database": "ok" if db_ok else "in-memory"}
    except Exception as e:
        logger.warning("[ready] Check failed: %s", e)
        return {"status": "degraded", "database": "unknown"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics."""
    return Response(content=get_metrics(), media_type="text/plain; version=0.0.4")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record request metrics."""
    import time
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - t0
    endpoint = request.url.path or "unknown"
    status = "success" if response.status_code < 400 else "error"
    REQUEST_COUNT.labels(service="gateway", endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(service="gateway", endpoint=endpoint).observe(elapsed)
    return response

logger.info("Gateway service started")
