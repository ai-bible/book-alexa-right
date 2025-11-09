#!/usr/bin/env python3
"""
Stop Hook: Workflow Checkpoint Validator

This hook runs when a conversation STOPS to validate all active workflow states
and provide actionable summary.

Hook Type: Stop
Trigger: When conversation ends
Mode: Non-blocking (informational only)
"""

import sys
import json
import glob
from pathlib import Path
from datetime import datetime, timezone


def main():
    """
    Validate all active generation workflows on conversation stop.

    Provides summary of:
    - Active workflows (IN_PROGRESS)
    - Workflows awaiting user approval
    - Recent failures
    - Actionable next steps
    """
    try:
        workspace = Path("workspace")

        if not workspace.exists():
            # No workspace, nothing to check
            sys.exit(0)

        # Find all state files
        state_files = list(workspace.glob("generation-state-*.json"))

        if not state_files:
            # No state files, nothing to check
            sys.exit(0)

        # Categorize workflows
        active_workflows = []
        awaiting_approval = []
        recent_failures = []
        completed_today = []

        now = datetime.now(timezone.utc)

        for state_file in state_files:
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                scene_id = state.get('scene_id', 'unknown')
                workflow_status = state.get('workflow_status', 'UNKNOWN')
                current_step = state.get('current_step', 0)

                # Parse timestamps
                started_at = state.get('started_at', '')
                updated_at = state.get('updated_at', '')

                # Categorize
                if workflow_status == 'IN_PROGRESS':
                    active_workflows.append({
                        'scene_id': scene_id,
                        'step': current_step,
                        'phase': state.get('current_phase', 'Unknown'),
                        'started': started_at,
                        'updated': updated_at
                    })

                elif workflow_status == 'WAITING_USER_APPROVAL':
                    awaiting_approval.append({
                        'scene_id': scene_id,
                        'step': current_step,
                        'updated': updated_at
                    })

                elif workflow_status == 'FAILED':
                    # Check if recent (today)
                    if _is_today(updated_at):
                        recent_failures.append({
                            'scene_id': scene_id,
                            'step': current_step,
                            'reason': state.get('failure_reason', 'Unknown'),
                            'updated': updated_at
                        })

                elif workflow_status == 'COMPLETED':
                    # Check if completed today
                    if _is_today(updated_at):
                        completed_today.append({
                            'scene_id': scene_id,
                            'word_count': state.get('completion_metrics', {}).get('word_count', 0),
                            'completed': updated_at
                        })

            except Exception as e:
                # Skip corrupted state file
                print(
                    f"⚠️ [Checkpoint Hook] Skipped corrupted state: {state_file.name}",
                    file=sys.stderr
                )
                continue

        # Generate summary report
        if any([active_workflows, awaiting_approval, recent_failures, completed_today]):
            _print_summary(active_workflows, awaiting_approval, recent_failures, completed_today)

        # Always exit successfully
        sys.exit(0)

    except Exception as e:
        # Graceful degradation
        print(
            f"⚠️ [Checkpoint Hook] Error (non-blocking): {type(e).__name__}: {str(e)}",
            file=sys.stderr
        )
        sys.exit(0)


def _print_summary(active, awaiting, failures, completed):
    """Print formatted summary to stderr."""

    print("\n" + "="*60, file=sys.stderr)
    print("📊 WORKFLOW CHECKPOINT SUMMARY", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)

    # Active workflows
    if active:
        print(f"⏳ ACTIVE WORKFLOWS ({len(active)}):", file=sys.stderr)
        for wf in active:
            elapsed = _format_elapsed(wf['updated'])
            print(
                f"  • Scene {wf['scene_id']}: Step {wf['step']}/7 - {wf['phase']}",
                file=sys.stderr
            )
            print(
                f"    Last update: {elapsed} ago",
                file=sys.stderr
            )
        print("", file=sys.stderr)

        print("💡 Next steps:", file=sys.stderr)
        print("  - Continue generation when ready", file=sys.stderr)
        print(f"  - Check status: /generation-state status {active[0]['scene_id']}", file=sys.stderr)
        print("", file=sys.stderr)

    # Awaiting approval
    if awaiting:
        print(f"⏸️  AWAITING USER APPROVAL ({len(awaiting)}):", file=sys.stderr)
        for wf in awaiting:
            print(
                f"  • Scene {wf['scene_id']}: Step {wf['step']} waiting for approval",
                file=sys.stderr
            )
        print("", file=sys.stderr)

        print("💡 Next steps:", file=sys.stderr)
        print("  - Review and approve verification plan", file=sys.stderr)
        print("  - Continue generation after approval", file=sys.stderr)
        print("", file=sys.stderr)

    # Recent failures
    if failures:
        print(f"❌ RECENT FAILURES ({len(failures)}):", file=sys.stderr)
        for wf in failures:
            print(
                f"  • Scene {wf['scene_id']}: Failed at Step {wf['step']}",
                file=sys.stderr
            )
            print(
                f"    Reason: {wf['reason'][:80]}...",
                file=sys.stderr
            )
        print("", file=sys.stderr)

        print("💡 Next steps:", file=sys.stderr)
        print("  - Fix issues (blueprint, constraints, etc.)", file=sys.stderr)
        print(f"  - Resume: /generation-state resume {failures[0]['scene_id']}", file=sys.stderr)
        print("", file=sys.stderr)

    # Completed today
    if completed:
        print(f"✅ COMPLETED TODAY ({len(completed)}):", file=sys.stderr)
        for wf in completed:
            print(
                f"  • Scene {wf['scene_id']}: {wf['word_count']:,} words",
                file=sys.stderr
            )
        print("", file=sys.stderr)

    print("="*60 + "\n", file=sys.stderr)


def _is_today(iso_timestamp: str) -> bool:
    """Check if timestamp is from today."""
    if not iso_timestamp:
        return False

    try:
        ts = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return ts.date() == now.date()
    except Exception:
        return False


def _format_elapsed(iso_timestamp: str) -> str:
    """Format elapsed time from timestamp."""
    if not iso_timestamp:
        return "unknown"

    try:
        ts = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = (now - ts).total_seconds()

        if delta < 60:
            return f"{int(delta)}s"
        elif delta < 3600:
            return f"{int(delta // 60)}m"
        elif delta < 86400:
            return f"{int(delta // 3600)}h"
        else:
            return f"{int(delta // 86400)}d"
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
