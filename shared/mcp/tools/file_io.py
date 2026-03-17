"""File I/O tool – read, write, and convert files in a workspace directory."""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE_DIR = Path(os.getenv("FILE_WORKSPACE", "/tmp/agent_workspace"))


def _ensure_workspace() -> Path:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_DIR


def _safe_path(filename: str) -> Path:
    """Resolve path within workspace, preventing directory traversal."""
    ws = _ensure_workspace()
    resolved = (ws / filename).resolve()
    if not str(resolved).startswith(str(ws.resolve())):
        logger.warning("[file_io] Path traversal blocked: %s", filename)
        raise ValueError("Path traversal not allowed")
    return resolved


def read_file(filename: str) -> dict[str, Any]:
    """Read a file from the agent workspace.

    Args:
        filename: Name of the file (relative to workspace).

    Returns:
        Dict with filename, content, size, and exists fields.
    """
    path = _safe_path(filename)
    if not path.exists():
        logger.debug("[file_io] read_file | file not found: %s", filename)
        return {"filename": filename, "content": "", "size": 0, "exists": False}
    content = path.read_text(encoding="utf-8", errors="replace")
    logger.info("[file_io] read_file | filename=%s | size=%d", filename, len(content))
    return {"filename": filename, "content": content, "size": len(content), "exists": True}


def write_file(filename: str, content: str) -> dict[str, Any]:
    """Write content to a file in the agent workspace.

    Args:
        filename: Name of the file (relative to workspace).
        content: Text content to write.

    Returns:
        Dict with filename, size, and success fields.
    """
    path = _safe_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("[file_io] write_file | filename=%s | size=%d", filename, len(content))
    return {"filename": filename, "size": len(content), "success": True}


def list_files(directory: str = ".") -> dict[str, Any]:
    """List files in a workspace directory.

    Args:
        directory: Subdirectory relative to workspace (default: root).

    Returns:
        Dict with directory and files list.
    """
    path = _safe_path(directory)
    if not path.is_dir():
        logger.debug("[file_io] list_files | not a directory: %s", directory)
        return {"directory": directory, "files": [], "error": "Not a directory"}
    files = []
    for entry in sorted(path.iterdir()):
        files.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": entry.stat().st_size if entry.is_file() else 0,
        })
    logger.info("[file_io] list_files | directory=%s | count=%d", directory, len(files))
    return {"directory": directory, "files": files}
