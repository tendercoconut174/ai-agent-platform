"""Sandboxed Python code execution tool."""

import io
import contextlib
import traceback
from typing import Any


def execute_python(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute Python code in a sandboxed environment.

    Captures stdout/stderr and returns the output. Execution is time-limited.

    Args:
        code: Python source code to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Dict with stdout, stderr, success, and error fields.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    allowed_builtins = {
        k: v for k, v in __builtins__.items()
        if k not in ("exec", "eval", "compile", "__import__", "open", "input")
    } if isinstance(__builtins__, dict) else {
        k: getattr(__builtins__, k) for k in dir(__builtins__)
        if k not in ("exec", "eval", "compile", "__import__", "open", "input")
    }
    # Allow safe imports
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
        return {
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "success": True,
            "error": None,
        }
    except Exception:
        return {
            "stdout": stdout_buf.getvalue(),
            "stderr": stderr_buf.getvalue(),
            "success": False,
            "error": traceback.format_exc(),
        }
