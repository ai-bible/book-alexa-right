# Planning Workflow

Интерактивная система планирования сюжета на четырёх уровнях иерархии.

---

## Overview

Planning Workflow создаёт детальные планы на всех уровнях: от стратегических планов акта до blueprints сцен.

**Orchestrator**: `planning-coordinator` agent
**Command**: `/plan-story`

---

## Planning Levels

```
Level 1: Strategic (Act)     → acts/act-{N}/strategic-plan.md
Level 2: Storylines          → context/characters/{name}/storyline.md
Level 3: Chapter             → acts/.../chapter-{NN}/plan.md
Level 4: Scene (Blueprint)   → acts/.../scenes/scene-{NNNN}-blueprint.md
```

---

## 5-Phase Flow

### Phase 1: Exploration
- Ask clarifying questions about writer's vision
- **Agent**: `context-analyzer` reads current world/character states
- Identify gaps and opportunities

### Phase 2: Scenarios (HUMAN APPROVAL)
- **Agent**: `scenario-generator` creates 3-5 development options
- **Agent**: `consequence-predictor` predicts outcomes for each
- Present options with pros/cons
- **WAIT for user selection**

### Phase 3: Path Planning
- **Agent**: `arc-planner` breaks chosen scenario into events/scenes
- Includes dependency mapping between events
- Present structured plan for feedback

### Phase 4: Detailing
- **Agent**: `beat-planner` creates scene beats
- Includes emotional arcs and dialogue planning
- Present detailed beats for review

### Phase 5: Integration
- **Agent**: `storyline-integrator` integrates with existing storylines
- Includes impact analysis (plot, character, world, theme)
- Present integration report

### Final: Synthesize
- Collect all phase artifacts
- Create output file at appropriate level
- Present summary, ask for confirmation

---

## Agents

| Agent | Phase | Purpose |
|-------|-------|---------|
| planning-coordinator | All | Orchestration, user dialogue |
| context-analyzer | 1 | Current state analysis |
| scenario-generator | 2 | Generate 3-5 options |
| consequence-predictor | 2 | Predict outcomes |
| arc-planner | 3 | Events, scenes, dependencies |
| beat-planner | 4 | Beats, emotions, dialogue |
| storyline-integrator | 5 | Storylines, impact |

---

## Human Approval Points

1. **Phase 2**: User selects scenario from options
2. **Final**: User confirms completed plan

Writer can redirect at any point during the interactive process.

---

## Output Formats

### Scene Blueprint
```markdown
# Scene {ID} Blueprint

## Overview
POV, location, time, participants

## Scene Goal
What this scene accomplishes

## Beats
1. Opening hook
2. Development beats
3. Turning point
4. Closing hook

## Constraints
- Required elements
- Forbidden elements
- World mechanics to respect

## Character States
- Before/after for each character
```

### Chapter Plan
```markdown
# Chapter {NN} Plan

## Overview
Theme, timespan, POV characters

## Scene Sequence
1. Scene {NNNN}: purpose, key events
2. Scene {NNNN}: purpose, key events

## Character Arcs
Per-character development in this chapter

## Plot Threads
Active threads and their progression
```

---

## File Locations

```
Artifacts: workspace/artifacts/planning-{timestamp}/phase-{N}/
Output:    acts/.../plan.md or scenes/scene-{ID}-blueprint.md
```
