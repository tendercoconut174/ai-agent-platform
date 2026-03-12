"""Entry point for ai-agent-platform."""

import argparse
import subprocess
import sys


def run_gateway(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI gateway."""
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "services.gateway.main:app", "--host", host, "--port", str(port)],
        check=True,
    )


def run_worker() -> None:
    """Start the worker service."""
    subprocess.run(
        [sys.executable, "-m", "services.workers.worker_service"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-agent-platform",
        description="AI Agent Platform - Gateway, Worker, and more.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Service to run")

    gateway_parser = subparsers.add_parser("gateway", help="Start the FastAPI gateway")
    gateway_parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    gateway_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    gateway_parser.set_defaults(func=lambda args: run_gateway(args.host, args.port))

    worker_parser = subparsers.add_parser("worker", help="Start the worker service")
    worker_parser.set_defaults(func=lambda args: run_worker())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
