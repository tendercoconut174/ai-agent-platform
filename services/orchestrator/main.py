"""Orchestrator FastAPI service."""

from dotenv import load_dotenv

load_dotenv()

from shared.logging_config import setup_logging

setup_logging()

import logging

from fastapi import FastAPI
from fastapi.responses import Response

from services.orchestrator.api.routes import router
from shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, get_metrics

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent Platform Orchestrator")
app.include_router(router)


@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness probe - orchestrator is ready to accept work."""
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics."""
    return Response(content=get_metrics(), media_type="text/plain; version=0.0.4")


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Record request metrics."""
    import time
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - t0
    endpoint = request.url.path or "unknown"
    status = "success" if response.status_code < 400 else "error"
    REQUEST_COUNT.labels(service="orchestrator", endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(service="orchestrator", endpoint=endpoint).observe(elapsed)
    return response

logger.info("Orchestrator service started")
