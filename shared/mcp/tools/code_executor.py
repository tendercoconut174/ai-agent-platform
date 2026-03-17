"""Sandboxed Python code execution tool with enforced timeout."""

import contextlib
import io
import logging
import multiprocessing
import traceback
from typing import Any

logger = logging.getLogger(__name__)


def _run_in_sandbox(code: str, result_queue: multiprocessing.Queue) -> None:
    """Target function for the subprocess -- executes code in a sandbox."""
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    allowed_builtins = {
        k: v for k, v in __builtins__.items()
        if k not in ("exec", "eval", "compile", "__import__", "open", "input")
    } if isinstance(__builtins__, dict) else {
        k: getattr(__builtins__, k) for k in dir(__builtins__)
        if k not in ("exec", "eval", "compile", "__import__", "open", "input")
    }

    import importlib
    safe_modules = {"math", "json", "re", "datetime", "collections", "itertools", "functools", "statistics", "csv", "io"}

    def safe_import(name, *args, **kwargs):
        if name in safe_modules:
            return importlib.import_module(name)
        raise ImportError(f"Import of '{name}' is not allowed in sandbox")

    sandbox_globals = {"__builtins__": {**allowed_builtins, "__import__": safe_import}}

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(code, sandbox_globals)
        result_queue.put({
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "success": True,
            "error": None,
        })
    except Exception:
        result_queue.put({
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "success": False,
            "error": traceback.format_exc(),
        })


def execute_python(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute Python code in a sandboxed subprocess with enforced timeout.

    Args:
        code: Python source code to execute.
        timeout: Maximum execution time in seconds (actually enforced).

    Returns:
        Dict with stdout, stderr, success, and error fields.
    """
    logger.info("[code_executor] execute_python | code_len=%d | timeout=%d", len(code), timeout)
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    proc = multiprocessing.Process(target=_run_in_sandbox, args=(code, result_queue))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        logger.warning("[code_executor] Execution timed out after %ds", timeout)
        proc.kill()
        proc.join(timeout=5)
        return {
            "stdout": "",
            "stderr": "",
            "success": False,
            "error": f"Execution timed out after {timeout} seconds. "
                     f"The code took too long -- simplify or use smaller inputs.",
        }

    if not result_queue.empty():
        out = result_queue.get_nowait()
        logger.info("[code_executor] DONE | success=%s", out.get("success", False))
        return out

    logger.warning("[code_executor] Process exited with no output")
    return {
        "stdout": "",
        "stderr": "",
        "success": False,
        "error": "Execution failed with no output (process exited unexpectedly).",
    }
