# AI-Assisted Book Writing System

Система создания литературного текста с ИИ-агентами для научно-фантастического романа.

---

## File Naming (STRICT)

```
acts/act-{N}/chapters/chapter-{NN}/plan.md
acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{NNNN}-blueprint.md
acts/act-{N}/chapters/chapter-{NN}/content/scene-{NNNN}.md
```

- NO version suffixes: `-v2`, `-revised`, `-final` = WRONG
- Old versions go to `backups/` with timestamps
- If multiple files found (plan.md AND plan-v2.md) → STOP, move old to backups/

---

## Workflow Router

| User says | Action |
|-----------|--------|
| "Generate scene XXXX" / "Сгенерируй сцену" | Use `generation-coordinator` agent |
| `/plan-story` | Use `planning-coordinator` agent |
| `/check-consistency` | Use `consistency-checker` agent |
| `/storyline` | Use `storyline-developer` agent |
| `/generation-state` | Use generation-state skill |
| `/ai-prose-detector` | Use ai-prose-detector skill |

---

## Generation Workflow (7 steps)

**Always use `generation-coordinator`** - never generate directly.

1. **File Check** - blueprint exists?
2. **Validate** - blueprint-validator checks constraints
3. **Verify** - show verification plan, **WAIT FOR USER APPROVAL**
4. **Generate** - prose-writer creates text (up to 3 retry attempts)
5. **Fast Check** - compliance check (embedded in step 4)
6. **Full Validate** - validation-aggregator runs 7 checks
7. **Output** - save to file, return metadata (NOT full text)

**Rules:**
- Never skip Step 3 (human approval)
- Never generate without blueprint
- Save to file, return only path + summary
- See `.workflows/generation.md` for details

---

## Planning Workflow (5 phases)

**Use `planning-coordinator`** via `/plan-story`.

1. **Explore** - context-analyzer gathers current state
2. **Scenarios** - generate options, **USER CHOOSES**
3. **Plan** - arc-planner breaks into events/scenes
4. **Detail** - beat-planner creates scene beats
5. **Integrate** - storyline-integrator updates storylines

See `.workflows/planning.md` for details.

---

## Key Rules

### Artifacts
- Pass files, not data (>100 lines → always file)
- Save agent output to file, pass path to next agent
- Never ask agent to return full generated text

### Context Management
- Keep context <60% of limit
- Use `/compact` between phases, `/clear` before new workflow
- Agent prompts should be <3k tokens (reference external docs)

### Language
- All final text (prose, plans, blueprints) in Russian
- Prompts and technical docs can be English
- All book-specific terms in Russian

### Analysis
- Use hat-thinks MCP for multi-perspective analysis on complex decisions
- hat-thinks is for finding blind spots, not for planning itself
- Always provide hat-thinks with clear questions and context

---

## Commands

```
/plan-story              # Interactive story planning
/storyline               # Character storyline management
/check-consistency       # Find contradictions after changes
/generation-state        # Monitor/resume/cancel generation
/ai-prose-detector       # Check prose for AI patterns
```

---

## Project Structure

```
acts/                    # Book content
  act-1/
    strategic-plan.md
    chapters/
      chapter-NN/
        plan.md          # Chapter plan
        scenes/          # Blueprints
        content/         # Generated text
        backups/         # Old versions

context/                 # World context
  characters/            # Character profiles
  world/                 # World building
  plot-graph/            # Plot connections
  events/                # Key events

canon/                   # Canon levels (0-4)

.claude/agents/          # 15 agents
  planning/              # 7 planning agents
  generation/            # 6 generation agents
  shared/                # 2 shared agents

.workflows/              # Workflow documentation
  generation.md
  planning.md
  agents-reference.md

workspace/               # Temporary files, logs, artifacts
```

---

## Agents (15 total)

**Planning (7):** planning-coordinator, context-analyzer, scenario-generator, consequence-predictor, arc-planner, beat-planner, storyline-integrator

**Generation (6):** generation-coordinator, prose-writer, blueprint-validator, verification-planner, blueprint-compliance-fast-checker, validation-aggregator

**Shared (2):** consistency-checker, storyline-developer
