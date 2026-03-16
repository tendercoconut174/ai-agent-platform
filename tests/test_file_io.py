"""Unit tests for file I/O tool."""

import pytest


class TestFileIo:
    """Tests for read_file, write_file, list_files."""

    def test_write_and_read_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        """Write then read returns same content."""
        from shared.mcp.tools import file_io

        file_io.WORKSPACE_DIR = tmp_path
        r = file_io.write_file("test.txt", "hello world")
        assert r["success"] is True
        assert r["size"] == 11

        r2 = file_io.read_file("test.txt")
        assert r2["exists"] is True
        assert r2["content"] == "hello world"
        assert r2["size"] == 11

    def test_read_missing_returns_exists_false(self, tmp_path: pytest.TempPathFactory) -> None:
        """Reading non-existent file returns exists=False."""
        from shared.mcp.tools import file_io

        file_io.WORKSPACE_DIR = tmp_path
        r = file_io.read_file("nonexistent.txt")
        assert r["exists"] is False
        assert r["content"] == ""

    def test_path_traversal_blocked(self, tmp_path: pytest.TempPathFactory) -> None:
        """Path traversal (../) raises ValueError."""
        from shared.mcp.tools import file_io

        file_io.WORKSPACE_DIR = tmp_path
        with pytest.raises(ValueError, match="Path traversal"):
            file_io.read_file("../../../etc/passwd")

    def test_list_files_returns_structure(self, tmp_path: pytest.TempPathFactory) -> None:
        """list_files returns directory and files list."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("bb")
        from shared.mcp.tools import file_io

        file_io.WORKSPACE_DIR = tmp_path
        r = file_io.list_files(".")
        assert "files" in r
        assert len(r["files"]) >= 2
        names = [f["name"] for f in r["files"]]
        assert "a.txt" in names
        assert "b.txt" in names
