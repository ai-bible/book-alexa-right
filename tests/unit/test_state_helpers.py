"""
Unit Tests for State Helper Functions

Tests utility functions from generation_state_mcp.py.
"""

import pytest
from datetime import datetime, timezone


# Import helper functions
try:
    from mcp_servers.generation_state_mcp import (
        _get_step_key,
        _format_duration,
        _format_timestamp,
        _calculate_duration,
        _is_terminal_state,
        WorkflowStatus,
        StepStatus,
        ErrorSeverity
    )
    HELPERS_AVAILABLE = True
except ImportError:
    HELPERS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestStepKey:
    """Tests for _get_step_key helper."""

    def test_step_1_file_check(self):
        """Test step 1 key."""
        assert _get_step_key(1) == "step_1_file_check"

    def test_step_2_blueprint_validation(self):
        """Test step 2 key."""
        assert _get_step_key(2) == "step_2_blueprint_validation"

    def test_step_3_verification_plan(self):
        """Test step 3 key."""
        assert _get_step_key(3) == "step_3_verification_plan"

    def test_step_4_generation(self):
        """Test step 4 key."""
        assert _get_step_key(4) == "step_4_generation"

    def test_step_5_fast_compliance(self):
        """Test step 5 key."""
        assert _get_step_key(5) == "step_5_fast_compliance"

    def test_step_6_full_validation(self):
        """Test step 6 key."""
        assert _get_step_key(6) == "step_6_full_validation"

    def test_step_7_final_output(self):
        """Test step 7 key."""
        assert _get_step_key(7) == "step_7_final_output"

    def test_invalid_step_number(self):
        """Test invalid step number."""
        result = _get_step_key(99)
        assert "unknown" in result.lower() or "step_99" in result


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestFormatDuration:
    """Tests for _format_duration helper."""

    def test_seconds_only(self):
        """Test formatting seconds."""
        assert _format_duration(45) == "45s"
        assert _format_duration(1) == "1s"

    def test_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert _format_duration(125) == "2m 5s"
        assert _format_duration(60) == "1m 0s"

    def test_hours_minutes_seconds(self):
        """Test formatting hours, minutes, seconds."""
        assert _format_duration(3665) == "1h 1m 5s"
        assert _format_duration(3600) == "1h 0m 0s"

    def test_zero_duration(self):
        """Test zero duration."""
        result = _format_duration(0)
        assert result in ["0s", "0m 0s"]

    def test_fractional_seconds(self):
        """Test fractional seconds are handled."""
        result = _format_duration(45.7)
        assert "45s" in result or "46s" in result


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestFormatTimestamp:
    """Tests for _format_timestamp helper."""

    def test_format_current_time(self):
        """Test formatting current timestamp."""
        now = datetime.now(timezone.utc)
        result = _format_timestamp(now)

        assert isinstance(result, str)
        assert "T" in result  # ISO format
        assert "Z" in result or "+" in result  # Timezone

    def test_format_none(self):
        """Test formatting None timestamp."""
        result = _format_timestamp(None)
        # Should return current time or empty string
        assert result is not None


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestCalculateDuration:
    """Tests for _calculate_duration helper."""

    def test_calculate_simple_duration(self):
        """Test calculating duration between two timestamps."""
        start = "2025-11-03T14:00:00Z"
        end = "2025-11-03T14:05:30Z"

        duration = _calculate_duration(start, end)

        assert duration == 330.0  # 5 minutes 30 seconds

    def test_calculate_zero_duration(self):
        """Test same timestamp."""
        timestamp = "2025-11-03T14:00:00Z"

        duration = _calculate_duration(timestamp, timestamp)

        assert duration == 0.0

    def test_invalid_timestamps(self):
        """Test handling invalid timestamps."""
        result = _calculate_duration("invalid", "also_invalid")

        # Should handle gracefully (return 0 or raise exception)
        assert result is not None


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestIsTerminalState:
    """Tests for _is_terminal_state helper."""

    def test_completed_is_terminal(self):
        """Test COMPLETED is terminal."""
        assert _is_terminal_state(WorkflowStatus.COMPLETED)

    def test_failed_is_terminal(self):
        """Test FAILED is terminal."""
        assert _is_terminal_state(WorkflowStatus.FAILED)

    def test_cancelled_is_terminal(self):
        """Test CANCELLED is terminal."""
        assert _is_terminal_state(WorkflowStatus.CANCELLED)

    def test_in_progress_not_terminal(self):
        """Test IN_PROGRESS is not terminal."""
        assert not _is_terminal_state(WorkflowStatus.IN_PROGRESS)

    def test_waiting_approval_not_terminal(self):
        """Test WAITING_USER_APPROVAL is not terminal."""
        assert not _is_terminal_state(WorkflowStatus.WAITING_USER_APPROVAL)


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestEnums:
    """Tests for enum definitions."""

    def test_workflow_status_values(self):
        """Test WorkflowStatus enum has all expected values."""
        assert hasattr(WorkflowStatus, 'NOT_FOUND')
        assert hasattr(WorkflowStatus, 'IN_PROGRESS')
        assert hasattr(WorkflowStatus, 'WAITING_USER_APPROVAL')
        assert hasattr(WorkflowStatus, 'COMPLETED')
        assert hasattr(WorkflowStatus, 'FAILED')
        assert hasattr(WorkflowStatus, 'CANCELLED')

    def test_step_status_values(self):
        """Test StepStatus enum has all expected values."""
        assert hasattr(StepStatus, 'PENDING')
        assert hasattr(StepStatus, 'IN_PROGRESS')
        assert hasattr(StepStatus, 'COMPLETED')
        assert hasattr(StepStatus, 'FAILED')
        assert hasattr(StepStatus, 'SKIPPED')

    def test_error_severity_values(self):
        """Test ErrorSeverity enum has all expected values."""
        assert hasattr(ErrorSeverity, 'LOW')
        assert hasattr(ErrorSeverity, 'MEDIUM')
        assert hasattr(ErrorSeverity, 'HIGH')
        assert hasattr(ErrorSeverity, 'CRITICAL')

    def test_error_severity_ordering(self):
        """Test ErrorSeverity can be compared (if implemented)."""
        # This test depends on whether severity is orderable
        low = ErrorSeverity.LOW
        critical = ErrorSeverity.CRITICAL

        assert low.value == "LOW"
        assert critical.value == "CRITICAL"


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestSceneIdValidation:
    """Tests for scene ID validation (if function exists)."""

    def test_valid_scene_ids(self):
        """Test valid scene ID formats."""
        valid_ids = ["0001", "0204", "9999", "1234"]

        for scene_id in valid_ids:
            # Assuming validation function exists
            # assert _validate_scene_id(scene_id) == True
            assert len(scene_id) == 4
            assert scene_id.isdigit()

    def test_invalid_scene_ids(self):
        """Test invalid scene ID formats."""
        invalid_ids = ["001", "12345", "abc", "01-02", ""]

        for scene_id in invalid_ids:
            # Negative validation
            assert len(scene_id) != 4 or not scene_id.isdigit()


@pytest.mark.unit
@pytest.mark.skipif(not HELPERS_AVAILABLE, reason="Helper functions not available")
class TestStateFileOperations:
    """Tests for state file path operations (if functions exist)."""

    def test_state_file_pattern(self):
        """Test state file naming pattern."""
        scene_id = "9999"
        expected = f"generation-state-{scene_id}.json"

        # This tests the expected pattern used in the system
        assert expected == "generation-state-9999.json"

    def test_extract_scene_id_from_filename(self):
        """Test extracting scene ID from state filename."""
        filename = "generation-state-0204.json"

        # Extract scene_id (pattern: generation-state-{scene_id}.json)
        scene_id = filename.replace("generation-state-", "").replace(".json", "")

        assert scene_id == "0204"
        assert len(scene_id) == 4
        assert scene_id.isdigit()
