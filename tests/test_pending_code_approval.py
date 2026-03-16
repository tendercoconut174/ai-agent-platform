"""Tests for pending code approval manager (human-in-the-loop)."""

from unittest.mock import patch

import pytest

from shared.pending_code_approval_manager import (
    load_and_clear_pending_code_approval,
    save_pending_code_approval,
    save_pending_code_approval_by_id,
)


class TestPendingCodeApprovalManager:
    """Tests for save/load of pending code approvals."""

    @patch("shared.pending_code_approval_manager._check_db", return_value=False)
    def test_save_and_load_in_memory(self, mock_check_db: object) -> None:
        """When DB unavailable, save and load work in-memory."""
        import shared.pending_code_approval_manager as pcm

        pcm._memory_pending.clear()

        approval_id = save_pending_code_approval(
            workflow_id="wf-123",
            session_id="sess-456",
            code="print(2 + 2)",
            step_id="step-1",
            original_goal="calculate 2+2",
            output_format="json",
        )
        assert approval_id is not None

        rec = load_and_clear_pending_code_approval(approval_id)
        assert rec is not None
        assert rec.workflow_id == "wf-123"
        assert rec.session_id == "sess-456"
        assert rec.code == "print(2 + 2)"
        assert rec.step_id == "step-1"
        assert rec.original_goal == "calculate 2+2"
        assert rec.output_format == "json"

    @patch("shared.pending_code_approval_manager._check_db", return_value=False)
    def test_load_returns_none_when_not_found(self, mock_check_db: object) -> None:
        """Load returns None when no pending code approval exists."""
        import shared.pending_code_approval_manager as pcm

        pcm._memory_pending.clear()

        rec = load_and_clear_pending_code_approval("nonexistent-approval-id")
        assert rec is None

    @patch("shared.pending_code_approval_manager._check_db", return_value=False)
    def test_load_clears_after_fetch(self, mock_check_db: object) -> None:
        """Load removes the pending code approval (one-time use)."""
        import shared.pending_code_approval_manager as pcm

        pcm._memory_pending.clear()

        approval_id = save_pending_code_approval(
            workflow_id="wf-789",
            session_id=None,
            code="x = 1",
            step_id="step-1",
            original_goal="set x",
            output_format="json",
        )
        rec1 = load_and_clear_pending_code_approval(approval_id)
        rec2 = load_and_clear_pending_code_approval(approval_id)
        assert rec1 is not None
        assert rec2 is None

    @patch("shared.pending_code_approval_manager._check_db", return_value=False)
    def test_save_by_id_and_load(self, mock_check_db: object) -> None:
        """save_pending_code_approval_by_id allows gateway to save pending received from orchestrator."""
        import shared.pending_code_approval_manager as pcm

        pcm._memory_pending.clear()

        approval_id = "fixed-id-12345"
        save_pending_code_approval_by_id(
            approval_id=approval_id,
            workflow_id="wf-1",
            session_id="sess-1",
            code="print(1+1)",
            step_id="step_1",
            original_goal="calculate 1+1",
            output_format="json",
        )
        rec = load_and_clear_pending_code_approval(approval_id)
        assert rec is not None
        assert rec.approval_id == approval_id
        assert rec.code == "print(1+1)"
        assert rec.original_goal == "calculate 1+1"
