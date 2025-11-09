"""
Unit Tests for Test Reporter

Tests report generation functionality from tests/helpers/reporter.py.
"""

import pytest
from pathlib import Path
from tests.helpers.reporter import TestReporter, create_summary_report
from tests.helpers.workflow_runner import WorkflowResult


@pytest.mark.unit
class TestReportGeneration:
    """Tests for TestReporter.generate_report."""

    def test_generate_report_completed(self):
        """Test report generation for completed workflow."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=324.5,
            mcp_calls_count=16
        )

        mcp_calls = [
            {"tool_name": "start_generation", "arguments": {"scene_id": "9999"}},
            {"tool_name": "complete_generation", "arguments": {"scene_id": "9999"}}
        ]

        report = reporter.generate_report(
            test_name="test_happy_path",
            result=result,
            mcp_calls=mcp_calls
        )

        # Verify report structure
        assert "# Test Report: test_happy_path" in report
        assert "Scene ID**: 9999" in report
        assert "✅ COMPLETED" in report
        assert "Steps Completed**: 7/7" in report
        assert "MCP Call Sequence" in report
        assert "start_generation" in report
        assert "complete_generation" in report

    def test_generate_report_failed(self):
        """Test report generation for failed workflow."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="FAILED",
            total_steps=3,
            retry_count=3,
            duration_seconds=45.2,
            failed_step=4,
            failure_reason="Max retries exhausted (3/3)",
            mcp_calls_count=21,
            errors=[
                {
                    "error_type": "constraint_violation",
                    "severity": "CRITICAL",
                    "error_message": "Location constraint violated"
                }
            ]
        )

        mcp_calls = []

        report = reporter.generate_report(
            test_name="test_max_retries",
            result=result,
            mcp_calls=mcp_calls
        )

        # Verify failure details
        assert "❌ FAILED" in report
        assert "❌ Failure Details" in report
        assert "Failed at Step**: 4" in report
        assert "Max retries exhausted" in report
        assert "Errors Logged" in report
        assert "constraint_violation" in report
        assert "CRITICAL" in report

    def test_generate_report_with_state_comparison(self):
        """Test report with state comparison."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300,
            mcp_calls_count=16
        )

        expected_state = {
            "workflow_status": "COMPLETED",
            "current_step": 7,
            "current_phase": "Final Output"
        }

        actual_state = {
            "workflow_status": "COMPLETED",
            "current_step": 6,  # Differs
            "current_phase": "Final Output"
        }

        report = reporter.generate_report(
            test_name="test_state_check",
            result=result,
            mcp_calls=[],
            expected_state=expected_state,
            actual_state=actual_state
        )

        # Verify state comparison section
        assert "State Comparison" in report
        assert "Differences" in report
        assert "current_step" in report
        assert "Expected: `7`" in report
        assert "Actual: `6`" in report

    def test_format_status(self):
        """Test status formatting with emojis."""
        reporter = TestReporter()

        assert "✅" in reporter._format_status("COMPLETED")
        assert "❌" in reporter._format_status("FAILED")
        assert "🚫" in reporter._format_status("CANCELLED")
        assert "⏳" in reporter._format_status("IN_PROGRESS")

    def test_format_duration(self):
        """Test duration formatting."""
        reporter = TestReporter()

        assert reporter._format_duration(0.5) == "500ms"
        assert reporter._format_duration(45) == "45.0s"
        assert reporter._format_duration(125) == "2m 5s"
        assert reporter._format_duration(3665) == "1h 1m"

    def test_format_args(self):
        """Test argument formatting."""
        reporter = TestReporter()

        # Simple args
        args = {"scene_id": "9999", "step_number": 1}
        formatted = reporter._format_args(args)

        assert "scene_id=9999" in formatted
        assert "step_number=1" in formatted

        # Long args (should truncate)
        long_args = {"key" * 20: "value" * 20}
        formatted = reporter._format_args(long_args, max_length=50)

        assert len(formatted) <= 53  # 50 + "..."

    def test_compare_states(self):
        """Test state comparison logic."""
        reporter = TestReporter()

        expected = {
            "workflow_status": "COMPLETED",
            "current_step": 7,
            "current_phase": "Final Output"
        }

        actual = {
            "workflow_status": "COMPLETED",
            "current_step": 6,
            "current_phase": "Full Validation"
        }

        diffs = reporter._compare_states(expected, actual)

        assert len(diffs) == 2  # Two fields differ
        assert any(d["field"] == "current_step" for d in diffs)
        assert any(d["field"] == "current_phase" for d in diffs)


@pytest.mark.unit
class TestReportSaving:
    """Tests for saving reports to files."""

    def test_save_report(self, tmp_path):
        """Test saving report to file."""
        reporter = TestReporter(output_dir=tmp_path)

        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300,
            mcp_calls_count=16
        )

        report_path = reporter.save_report(
            test_name="test_example",
            result=result,
            mcp_calls=[]
        )

        # Verify file created
        assert report_path.exists()
        assert report_path.parent == tmp_path
        assert "test_example" in report_path.name
        assert report_path.suffix == ".md"

        # Verify content
        content = report_path.read_text()
        assert "test_example" in content
        assert "Scene ID**: 9999" in content


@pytest.mark.unit
class TestSummaryReport:
    """Tests for create_summary_report function."""

    def test_summary_all_passed(self):
        """Test summary with all tests passing."""
        test_results = [
            {
                "name": "test_1",
                "status": "passed",
                "duration": 10.5
            },
            {
                "name": "test_2",
                "status": "passed",
                "duration": 15.3
            }
        ]

        summary = create_summary_report(test_results)

        # Verify summary content
        assert "Test Suite Summary" in summary
        assert "Total Tests**: 2" in summary
        assert "Passed**: ✅ 2" in summary
        assert "Failed**: ❌ 0" in summary
        assert "Pass Rate**: 100.0%" in summary
        assert "test_1" in summary
        assert "test_2" in summary

    def test_summary_with_failures(self):
        """Test summary with failed tests."""
        test_results = [
            {
                "name": "test_1",
                "status": "passed",
                "duration": 10.5
            },
            {
                "name": "test_2",
                "status": "failed",
                "duration": 5.2,
                "error": "AssertionError: Expected 7, got 6"
            }
        ]

        summary = create_summary_report(test_results)

        # Verify failure details
        assert "Failed**: ❌ 1" in summary
        assert "Pass Rate**: 50.0%" in summary
        assert "Failed Tests Details" in summary
        assert "test_2" in summary
        assert "AssertionError" in summary

    def test_summary_save_to_file(self, tmp_path):
        """Test saving summary to file."""
        test_results = [
            {"name": "test_1", "status": "passed", "duration": 10}
        ]

        output_path = tmp_path / "summary.md"

        summary = create_summary_report(
            test_results,
            output_path=output_path
        )

        # Verify file created
        assert output_path.exists()

        # Verify content matches
        content = output_path.read_text()
        assert content == summary

    def test_summary_empty_results(self):
        """Test summary with no results."""
        summary = create_summary_report([])

        assert "Total Tests**: 0" in summary


@pytest.mark.unit
class TestReporterEdgeCases:
    """Tests for edge cases in reporter."""

    def test_empty_mcp_calls(self):
        """Test report with no MCP calls."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="FAILED",
            total_steps=0,
            retry_count=0,
            duration_seconds=1.0,
            failure_reason="Immediate failure",
            mcp_calls_count=0
        )

        report = reporter.generate_report(
            test_name="test_immediate_fail",
            result=result,
            mcp_calls=[]
        )

        assert "No MCP calls recorded" in report

    def test_no_artifacts(self):
        """Test report without artifacts."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300,
            mcp_calls_count=16,
            artifacts=None
        )

        report = reporter.generate_report(
            test_name="test_no_artifacts",
            result=result,
            mcp_calls=[]
        )

        # Should not have Artifacts section
        assert "Artifacts Created" not in report

    def test_large_mcp_call_list(self):
        """Test report with many MCP calls."""
        reporter = TestReporter()

        result = WorkflowResult(
            scene_id="9999",
            status="COMPLETED",
            total_steps=7,
            retry_count=0,
            duration_seconds=300,
            mcp_calls_count=100
        )

        # Create 100 MCP calls
        mcp_calls = [
            {"tool_name": f"tool_{i}", "arguments": {"scene_id": "9999"}}
            for i in range(100)
        ]

        report = reporter.generate_report(
            test_name="test_many_calls",
            result=result,
            mcp_calls=mcp_calls
        )

        # Should handle large list
        assert "Total calls: 100" in report
        assert "tool_0" in report
        assert "tool_99" in report
