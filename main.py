"""Entry point for ai-agent-platform."""

import argparse
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def run_gateway(host: str = "0.0.0.0", port: int = 8000) -> None:
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "services.gateway.main:app", "--host", host, "--port", str(port)],
        check=True,
    )


def run_orchestrator(host: str = "0.0.0.0", port: int = 8001) -> None:
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "services.orchestrator.main:app", "--host", host, "--port", str(port)],
        check=True,
    )


def run_migrate() -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
