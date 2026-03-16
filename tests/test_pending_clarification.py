"""Tests for pending clarification manager (human-in-the-loop)."""

from unittest.mock import patch

import pytest

from services.gateway.pending_clarification_manager import (
    load_and_clear_pending_clarification,
    save_pending_clarification,
)


class TestPendingClarificationManager:
    """Tests for save/load of pending clarifications."""

    @patch("services.gateway.pending_clarification_manager._check_db", return_value=False)
    def test_save_and_load_in_memory(self, mock_check_db: object) -> None:
        """When DB unavailable, save and load work in-memory."""
        # Clear any prior state
        import services.gateway.pending_clarification_manager as pcm
        pcm._memory_pending.clear()

        save_pending_clarification(
            workflow_id="wf-123",
            session_id="sess-456",
            original_goal="research companies",
            question="Which industry?",
            output_format="json",
        )
        rec = load_and_clear_pending_clarification("wf-123")
        assert rec is not None
        assert rec.workflow_id == "wf-123"
        assert rec.session_id == "sess-456"
        assert rec.original_goal == "research companies"
        assert rec.question == "Which industry?"
        assert rec.output_format == "json"

    @patch("services.gateway.pending_clarification_manager._check_db", return_value=False)
    def test_load_returns_none_when_not_found(self, mock_check_db: object) -> None:
        """Load returns None when no pending clarification exists."""
        import services.gateway.pending_clarification_manager as pcm
        pcm._memory_pending.clear()

        rec = load_and_clear_pending_clarification("nonexistent")
        assert rec is None

    @patch("services.gateway.pending_clarification_manager._check_db", return_value=False)
    def test_load_clears_after_fetch(self, mock_check_db: object) -> None:
        """Load removes the pending clarification (one-time use)."""
        import services.gateway.pending_clarification_manager as pcm
        pcm._memory_pending.clear()

        save_pending_clarification(
            workflow_id="wf-789",
            session_id=None,
            original_goal="create report",
            question="What topic?",
            output_format="pdf",
        )
        rec1 = load_and_clear_pending_clarification("wf-789")
        rec2 = load_and_clear_pending_clarification("wf-789")
        assert rec1 is not None
        assert rec2 is None
