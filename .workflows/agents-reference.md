# Agents Reference

15 agents organized by workflow.

---

## Planning Agents (7)

| Agent | File | Purpose |
|-------|------|---------|
| planning-coordinator | `planning/planning-coordinator.md` | Orchestrates planning workflow, guides user through 5 phases |
| context-analyzer | `planning/context-analyzer.md` | Analyzes current world/character/plot state |
| scenario-generator | `planning/scenario-generator.md` | Generates 3-5 development scenarios |
| consequence-predictor | `planning/consequence-predictor.md` | Predicts consequences and implications of each scenario |
| arc-planner | `planning/arc-planner.md` | Breaks scenario into events/scenes + dependency mapping |
| beat-planner | `planning/beat-planner.md` | Plans scene beats + emotional arcs + dialogue |
| storyline-integrator | `planning/storyline-integrator.md` | Integrates with storylines + impact analysis |

## Generation Agents (6)

| Agent | File | Purpose |
|-------|------|---------|
| generation-coordinator | `generation/generation-coordinator.md` | Orchestrates 7-step generation workflow with retry logic |
| prose-writer | `generation/prose-writer.md` | Generates literary prose from blueprint constraints |
| blueprint-validator | `generation/blueprint-validator.md` | Validates blueprint completeness, extracts constraints |
| verification-planner | `generation/verification-planner.md` | Creates human-readable verification plan |
| blueprint-compliance-fast-checker | `generation/blueprint-compliance-fast-checker.md` | Fast constraint compliance check (<30 sec) |
| validation-aggregator | `generation/validation-aggregator.md` | Full validation: 7 checks in one pass |

## Shared Agents (2)

| Agent | File | Purpose |
|-------|------|---------|
| consistency-checker | `shared/consistency-checker.md` | Checks plan vs content consistency after changes |
| storyline-developer | `shared/storyline-developer.md` | Manages character storylines (/storyline command) |

---

## Agent Communication

Agents communicate through **files** (artifact system):
- Agent writes result to file in `workspace/artifacts/`
- Next agent receives path to file
- Prevents context overflow, ensures traceability

## Invocation

All agents are in `.claude/agents/` directory. Invoked as sub-agents by coordinators or directly by user commands.
