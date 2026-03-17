"""Entry point for ai-agent-platform."""

import argparse
import logging
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def run_gateway(host: str = "0.0.0.0", port: int = 8000) -> None:
    logger.info("[main] Starting gateway | host=%s | port=%d", host, port)
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "services.gateway.main:app", "--host", host, "--port", str(port)],
        check=True,
    )


def run_orchestrator(host: str = "0.0.0.0", port: int = 8001) -> None:
    logger.info("[main] Starting orchestrator | host=%s | port=%d", host, port)
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "services.orchestrator.main:app", "--host", host, "--port", str(port)],
        check=True,
    )


def run_migrate() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


def run_scheduler() -> None:
    logger.info("[main] Starting scheduler")
    from services.scheduler.scheduler_service import main as scheduler_main

    scheduler_main()


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-agent-platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gw = subparsers.add_parser("gateway")
    gw.add_argument("--host", default="0.0.0.0")
    gw.add_argument("--port", type=int, default=8000)
    gw.set_defaults(func=lambda a: run_gateway(a.host, a.port))

    orch = subparsers.add_parser("orchestrator")
    orch.add_argument("--host", default="0.0.0.0")
    orch.add_argument("--port", type=int, default=8001)
    orch.set_defaults(func=lambda a: run_orchestrator(a.host, a.port))

    subparsers.add_parser("migrate").set_defaults(func=lambda a: run_migrate())

    sched = subparsers.add_parser("scheduler")
    sched.set_defaults(func=lambda a: run_scheduler())

    args = parser.parse_args()
    logger.info("[main] Running command: %s", args.command)
    args.func(args)


if __name__ == "__main__":
    main()
