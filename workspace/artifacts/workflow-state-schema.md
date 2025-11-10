# Workflow State Schema

## Overview

Unified state tracking для Generation и Planning workflows с поддержкой:
- Sequential enforcement (нельзя пропустить шаги)
- Human-in-the-loop checkpoints
- Retry logic (для Generation)
- Recovery/resume после падения
- Integration с session management

---

## JSON Schema

### Base Workflow State

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["workflow_id", "workflow_type", "status", "created_at", "updated_at"],
  "properties": {
    "workflow_id": {
      "type": "string",
      "description": "Unique identifier: {type}-{scene_id|context}-{timestamp}",
      "example": "generation-scene-0204-20251110-143000"
    },
    "workflow_type": {
      "type": "string",
      "enum": ["generation", "planning"],
      "description": "Type of workflow"
    },
    "session_name": {
      "type": "string",
      "description": "Active session name (if running within session)"
    },
    "status": {
      "type": "string",
      "enum": ["in_progress", "waiting_approval", "failed", "completed", "cancelled"],
      "description": "Overall workflow status"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp"
    },
    "generation": {
      "type": "object",
      "description": "Generation workflow state (if workflow_type == 'generation')"
    },
    "planning": {
      "type": "object",
      "description": "Planning workflow state (if workflow_type == 'planning')"
    }
  }
}
```

---

## Generation Workflow State

### Structure

```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "workflow_type": "generation",
  "session_name": "work-on-chapter-02",
  "status": "in_progress",
  "created_at": "2025-11-10T14:30:00Z",
  "updated_at": "2025-11-10T14:35:00Z",

  "generation": {
    "scene_id": "0204",
    "current_step": 3,
    "total_steps": 7,
    "steps": [
      {
        "step": 1,
        "name": "File Check",
        "status": "completed",
        "started_at": "2025-11-10T14:30:00Z",
        "completed_at": "2025-11-10T14:30:05Z",
        "artifacts": {}
      },
      {
        "step": 2,
        "name": "Blueprint Validation",
        "status": "completed",
        "started_at": "2025-11-10T14:30:05Z",
        "completed_at": "2025-11-10T14:31:00Z",
        "artifacts": {
          "constraints_list": "workspace/sessions/work-on-chapter-02/generation-runs/generation-scene-0204-20251110-143000/constraints-list.json"
        }
      },
      {
        "step": 3,
        "name": "Verification Plan",
        "status": "waiting_approval",
        "started_at": "2025-11-10T14:31:00Z",
        "completed_at": null,
        "artifacts": {
          "verification_plan": "workspace/sessions/work-on-chapter-02/generation-runs/generation-scene-0204-20251110-143000/verification-plan.md"
        },
        "human_approval": {
          "required": true,
          "approved": false,
          "approved_at": null
        }
      },
      {
        "step": 4,
        "name": "Generation",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "artifacts": {},
        "attempts": {
          "current": 0,
          "max": 3,
          "history": []
        }
      },
      {
        "step": 5,
        "name": "Fast Compliance Check",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "artifacts": {}
      },
      {
        "step": 6,
        "name": "Full Validation",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "artifacts": {}
      },
      {
        "step": 7,
        "name": "Final Output",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "artifacts": {}
      }
    ],
    "artifacts": {
      "blueprint_path": "acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md",
      "working_dir": "workspace/sessions/work-on-chapter-02/generation-runs/generation-scene-0204-20251110-143000"
    }
  }
}
```

### Generation Step Status Values

- **pending**: Шаг не начат (prerequisites не выполнены)
- **in_progress**: Шаг выполняется
- **waiting_approval**: Ожидание человеческого одобрения (Step 3)
- **completed**: Шаг завершён успешно
- **failed**: Шаг провален (после max_attempts)

### Generation Step Definitions

```json
{
  "generation_steps": [
    {
      "step": 1,
      "name": "File Check",
      "agent": "generation-coordinator",
      "description": "Verify blueprint exists",
      "prerequisites": [],
      "outputs": ["blueprint_path"],
      "human_approval": false,
      "retry_enabled": false
    },
    {
      "step": 2,
      "name": "Blueprint Validation",
      "agent": "blueprint-validator",
      "description": "Validate blueprint completeness and consistency",
      "prerequisites": [1],
      "outputs": ["constraints_list"],
      "human_approval": false,
      "retry_enabled": false
    },
    {
      "step": 3,
      "name": "Verification Plan",
      "agent": "verification-planner",
      "description": "Create human-readable plan for approval",
      "prerequisites": [2],
      "outputs": ["verification_plan"],
      "human_approval": true,
      "retry_enabled": false
    },
    {
      "step": 4,
      "name": "Generation",
      "agent": "prose-writer",
      "description": "Generate literary prose adhering to constraints",
      "prerequisites": [3],
      "outputs": ["draft", "compliance_echo"],
      "human_approval": false,
      "retry_enabled": true,
      "max_attempts": 3
    },
    {
      "step": 5,
      "name": "Fast Compliance Check",
      "agent": "blueprint-compliance-fast-checker",
      "description": "Fast surface-level compliance check (<30s)",
      "prerequisites": [4],
      "outputs": ["fast_compliance_result"],
      "human_approval": false,
      "retry_enabled": false,
      "triggers_retry": true
    },
    {
      "step": 6,
      "name": "Full Validation",
      "agent": "validation-aggregator",
      "description": "Deep validation with 7 validators in parallel",
      "prerequisites": [5],
      "outputs": ["final_validation_report"],
      "human_approval": false,
      "retry_enabled": false,
      "parallel_agents": 7
    },
    {
      "step": 7,
      "name": "Final Output",
      "agent": "generation-coordinator",
      "description": "Format final report for user",
      "prerequisites": [6],
      "outputs": ["final_report", "scene_content"],
      "human_approval": false,
      "retry_enabled": false
    }
  ]
}
```

---

## Planning Workflow State

### Structure

```json
{
  "workflow_id": "planning-scene-0204-20251110-150000",
  "workflow_type": "planning",
  "session_name": "work-on-chapter-02",
  "status": "in_progress",
  "created_at": "2025-11-10T15:00:00Z",
  "updated_at": "2025-11-10T15:05:00Z",

  "planning": {
    "level": "scene",
    "context": {
      "act": 1,
      "chapter": 2,
      "scene": 4
    },
    "current_phase": 3,
    "total_phases": 5,
    "phases": [
      {
        "phase": 1,
        "name": "Exploration",
        "status": "completed",
        "started_at": "2025-11-10T15:00:00Z",
        "completed_at": "2025-11-10T15:01:30Z",
        "agents": ["dialogue-analyst", "context-analyzer"],
        "artifacts": {
          "exploration_results": "workspace/sessions/work-on-chapter-02/planning-runs/planning-scene-0204-20251110-150000/exploration-results.md"
        }
      },
      {
        "phase": 2,
        "name": "Scenarios",
        "status": "completed",
        "started_at": "2025-11-10T15:01:30Z",
        "completed_at": "2025-11-10T15:03:00Z",
        "agents": ["scenario-generator", "consequence-predictor"],
        "artifacts": {
          "scenarios": "workspace/sessions/work-on-chapter-02/planning-runs/planning-scene-0204-20251110-150000/scenarios.md"
        },
        "human_approval": {
          "required": true,
          "approved": true,
          "approved_at": "2025-11-10T15:03:00Z",
          "selected_variant": "A"
        }
      },
      {
        "phase": 3,
        "name": "Path Planning",
        "status": "in_progress",
        "started_at": "2025-11-10T15:03:00Z",
        "completed_at": null,
        "agents": ["arc-planner", "dependency-mapper"],
        "artifacts": {}
      },
      {
        "phase": 4,
        "name": "Detailing",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "agents": ["emotional-arc-designer", "beat-planner", "dialogue-weaver"],
        "artifacts": {}
      },
      {
        "phase": 5,
        "name": "Integration",
        "status": "pending",
        "started_at": null,
        "completed_at": null,
        "agents": ["storyline-integrator", "impact-analyzer"],
        "artifacts": {}
      }
    ],
    "artifacts": {
      "working_dir": "workspace/sessions/work-on-chapter-02/planning-runs/planning-scene-0204-20251110-150000"
    }
  }
}
```

### Planning Phase Status Values

- **pending**: Фаза не начата
- **in_progress**: Фаза выполняется
- **waiting_approval**: Ожидание выбора варианта (Phase 2)
- **completed**: Фаза завершена

### Planning Phase Definitions

```json
{
  "planning_phases": {
    "scene": [
      {
        "phase": 1,
        "name": "Exploration",
        "agents": ["dialogue-analyst", "context-analyzer"],
        "parallel": true,
        "prerequisites": [],
        "outputs": ["exploration_results"],
        "human_approval": false
      },
      {
        "phase": 2,
        "name": "Scenarios",
        "agents": ["scenario-generator", "consequence-predictor"],
        "parallel": false,
        "prerequisites": [1],
        "outputs": ["scenarios"],
        "human_approval": true,
        "approval_type": "select_variant"
      },
      {
        "phase": 3,
        "name": "Path Planning",
        "agents": ["arc-planner", "dependency-mapper"],
        "parallel": false,
        "prerequisites": [2],
        "outputs": ["path_plan"],
        "human_approval": false
      },
      {
        "phase": 4,
        "name": "Detailing",
        "agents": ["emotional-arc-designer", "beat-planner", "dialogue-weaver"],
        "parallel": false,
        "prerequisites": [3],
        "outputs": ["detailed_plans"],
        "human_approval": false
      },
      {
        "phase": 5,
        "name": "Integration",
        "agents": ["storyline-integrator", "impact-analyzer"],
        "parallel": false,
        "prerequisites": [4],
        "outputs": ["integration_analysis"],
        "human_approval": false
      }
    ],
    "chapter": [
      "... similar structure ..."
    ],
    "act": [
      "... similar structure ..."
    ]
  }
}
```

---

## State Storage

### File Location

**Within Session** (if session active):
```
workspace/sessions/{session_name}/workflow-state/{workflow_id}.json
```

**Global** (if no session):
```
workspace/workflow-state/{workflow_id}.json
```

### Index File

For fast lookup and listing:

```json
{
  "workflows": [
    {
      "workflow_id": "generation-scene-0204-20251110-143000",
      "workflow_type": "generation",
      "status": "in_progress",
      "session_name": "work-on-chapter-02",
      "created_at": "2025-11-10T14:30:00Z",
      "updated_at": "2025-11-10T14:35:00Z",
      "state_file": "workspace/sessions/work-on-chapter-02/workflow-state/generation-scene-0204-20251110-143000.json"
    }
  ]
}
```

**Location**:
- Session index: `workspace/sessions/{session_name}/workflow-state/index.json`
- Global index: `workspace/workflow-state/index.json`

---

## MCP Tools API

### 1. get_workflow_status

**Description**: Get current workflow state

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000"
}
```

**Output**:
```json
{
  "workflow_id": "...",
  "workflow_type": "generation",
  "status": "in_progress",
  "current_step": 3,
  "current_step_name": "Verification Plan",
  "waiting_for_approval": true,
  "progress_percentage": 42,
  "artifacts": {
    "verification_plan": "workspace/.../verification-plan.md"
  }
}
```

### 2. get_next_step

**Description**: Get next step info (sequential enforcement)

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000"
}
```

**Output**:
```json
{
  "can_proceed": false,
  "current_step": 3,
  "current_step_name": "Verification Plan",
  "current_status": "waiting_approval",
  "blocking_reason": "Human approval required for verification plan",
  "required_action": "User must approve or modify verification plan",
  "next_step": 4,
  "next_step_name": "Generation",
  "prerequisites_met": false
}
```

### 3. validate_prerequisites

**Description**: Check if prerequisites met for specific step

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "step": 4
}
```

**Output**:
```json
{
  "prerequisites_met": true,
  "required_steps": [1, 2, 3],
  "completed_steps": [1, 2, 3],
  "missing_steps": [],
  "can_start_step": true,
  "blocking_issues": []
}
```

### 4. approve_step

**Description**: Approve human checkpoint (Step 3, Phase 2/10)

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "step": 3,
  "approved": true,
  "modifications": {
    "emotional_tone": "professional detachment with cracks"
  }
}
```

**Output**:
```json
{
  "success": true,
  "workflow_id": "generation-scene-0204-20251110-143000",
  "step": 3,
  "status": "completed",
  "next_step": 4,
  "next_step_name": "Generation"
}
```

### 5. update_workflow_state

**Description**: Update workflow state (internal tool for agents)

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "step": 4,
  "status": "in_progress",
  "artifacts": {
    "draft": "workspace/.../scene-0204-draft.md"
  }
}
```

**Output**:
```json
{
  "success": true,
  "workflow_id": "generation-scene-0204-20251110-143000",
  "updated_at": "2025-11-10T14:40:00Z"
}
```

### 6. list_workflows

**Description**: List all workflows (optionally filter by status)

**Input**:
```json
{
  "status": "in_progress",
  "workflow_type": "generation",
  "session_name": "work-on-chapter-02"
}
```

**Output**:
```json
{
  "workflows": [
    {
      "workflow_id": "generation-scene-0204-20251110-143000",
      "workflow_type": "generation",
      "status": "in_progress",
      "current_step": 3,
      "progress_percentage": 42
    }
  ],
  "total": 1
}
```

### 7. resume_workflow

**Description**: Resume failed/cancelled workflow

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "from_step": 4
}
```

**Output**:
```json
{
  "success": true,
  "workflow_id": "generation-scene-0204-20251110-143000",
  "resumed_from_step": 4,
  "current_status": "in_progress"
}
```

### 8. cancel_workflow

**Description**: Cancel active workflow

**Input**:
```json
{
  "workflow_id": "generation-scene-0204-20251110-143000",
  "reason": "User requested cancellation"
}
```

**Output**:
```json
{
  "success": true,
  "workflow_id": "generation-scene-0204-20251110-143000",
  "status": "cancelled",
  "cleanup_performed": true
}
```

---

## Integration with Sessions

### Session CoW (Copy-on-Write)

When workflow runs within a session:

1. **Workflow state** stored in `workspace/sessions/{name}/workflow-state/{id}.json`
2. **Artifacts** stored in `workspace/sessions/{name}/{type}-runs/{id}/`
3. **On commit**:
   - Workflow state copied to global workspace
   - Artifacts copied to global workspace
   - State updated to mark session committed
4. **On cancel**:
   - Workflow state deleted
   - Artifacts deleted
   - No global impact

### Session Lifecycle Hooks

**On session create**:
- Initialize `workflow-state/` directory
- Create `workflow-state/index.json`

**On session commit**:
- Copy all workflow states to global
- Update global workflow index
- Mark workflows as "committed from session"

**On session cancel**:
- Delete all workflow states
- Delete all artifact directories

---

## Metrics and Observability

### Tracked Metrics

```json
{
  "workflow_metrics": {
    "workflow_id": "generation-scene-0204-20251110-143000",
    "total_time_seconds": 420,
    "step_times": [
      {"step": 1, "duration_seconds": 5},
      {"step": 2, "duration_seconds": 55},
      {"step": 3, "duration_seconds": 30},
      {"step": 4, "duration_seconds": 240}
    ],
    "retry_count": 1,
    "human_approval_time_seconds": 30,
    "agent_calls": 12,
    "parallel_executions": 7
  }
}
```

### Logs

Each workflow logs to:
```
workspace/logs/workflow-orchestration/{workflow_id}.log
```

---

## Error Handling

### Failed Step Recovery

1. **Automatic Retry** (Generation Step 4):
   - Attempt 1, 2, 3
   - Enhanced emphasis on each retry
   - After max_attempts → mark as failed

2. **Manual Intervention** (after failure):
   - User reviews error
   - User fixes blueprint/context
   - User resumes workflow with `resume_workflow()`

3. **Graceful Degradation**:
   - Workflow state persisted on every step
   - Can resume from any completed step
   - No data loss on crash

---

## Version

**Version**: 1.0
**Last Updated**: 2025-11-10
**Status**: Design Document
