"""Unit tests for code executor tool."""

import pytest

from shared.mcp.tools.code_executor import execute_python


class TestExecutePython:
    """Tests for execute_python function."""

    def test_simple_code_succeeds(self) -> None:
        """Simple safe code runs and returns stdout."""
        result = execute_python("print(2 + 3)")
        assert result["success"] is True
        assert result["stdout"].strip() == "5"
        assert result["error"] is None

    def test_math_module_allowed(self) -> None:
        """math module is in safe list."""
        result = execute_python("import math; print(int(math.sqrt(16)))")
        assert result["success"] is True
        assert "4" in result["stdout"]

    def test_unsafe_import_blocked(self) -> None:
        """os and other modules are blocked."""
        result = execute_python("import os; print(os.listdir('.'))")
        assert result["success"] is False
        assert "not allowed" in result.get("error", "").lower() or "ImportError" in result.get("error", "")

    def test_open_blocked(self) -> None:
        """open() is not in allowed builtins."""
        result = execute_python("open('/etc/passwd').read()")
        assert result["success"] is False

    def test_exception_captured(self) -> None:
        """Runtime errors are captured in error field."""
        result = execute_python("1 / 0")
        assert result["success"] is False
        assert "ZeroDivisionError" in result.get("error", "") or "division" in result.get("error", "").lower()

    def test_timeout_enforced(self) -> None:
        """Code that runs too long is killed."""
        result = execute_python("while True: pass", timeout=1)
        assert result["success"] is False
        assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()
