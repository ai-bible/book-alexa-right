---
name: plan-story
description: >-
  This skill should be used when the user asks to "plan story", "plan-story",
  "plan a chapter", "plan a scene", "plan act", "strategic planning",
  or says "спланировать сюжет", "планирование главы", "планирование сцены",
  "спланировать акт", "plan next chapter", "plan scene blueprint".
  Launches interactive multi-phase planning workflow for any narrative level
  (act, storyline, chapter, scene, event).
---

# Plan Story - Interactive Planning Workflow

Launch the `planning-coordinator` agent to guide the writer through multi-phase
story planning. The agent handles the full interactive dialogue, scenario generation,
and plan creation.

## When to Use

- Writer wants to plan new content at any level (act, chapter, scene, event)
- Writer needs to develop a strategic plan or scene blueprint
- Writer says anything about planning story content

## Invocation

### Parse Arguments

Extract optional arguments from the user's command:

```
/plan-story                          → No arguments, agent will ask
/plan-story scene 0205               → Level: scene, context: act-2 ch-05 scene-05
/plan-story chapter 03               → Level: chapter, context: chapter 03
/plan-story strategic act 2          → Level: strategic, context: act 2
/plan-story event "Mara discovers"   → Level: event, context: description
```

Argument format: `/plan-story [level] [context...]`

- **level** (optional): `strategic` | `storyline` | `chapter` | `scene` | `event`
- **context** (optional): Act/chapter/scene numbers or description

### Launch Agent

Invoke the `planning-coordinator` agent via the Task tool:

```
Task(
  subagent_type="planning-coordinator",
  prompt="<parsed arguments and user request>",
  description="Interactive story planning"
)
```

Pass to the agent:
1. The planning level (if specified)
2. The context identifiers (act/chapter/scene numbers)
3. Any additional user notes or goals
4. If no arguments provided, instruct agent to ask the user interactively

## Planning Levels

| Level | Output | Saved To |
|-------|--------|----------|
| Strategic | Act plan | `acts/act-{N}/strategic-plan.md` |
| Storyline | Character arc | `acts/act-{N}/storylines/{character}.md` |
| Chapter | Chapter plan | `acts/act-{N}/chapters/chapter-{NN}/plan.md` |
| Scene | Scene blueprint | `acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{NNNN}-blueprint.md` |
| Event | Event within scene | Integrated into scene blueprint |

## What the Agent Does (5 Phases)

1. **Exploration** - Gather context, ask clarifying questions
2. **Scenarios** - Generate 3-5 development options (**requires human approval**)
3. **Path Planning** - Break chosen path into events/scenes
4. **Detailing** - Emotional arcs, beats, dialogue plans
5. **Integration** - Integrate with existing storylines, assess impact

Phase 2 always requires writer approval before proceeding.

## Session Awareness

The planning-coordinator agent handles session management internally.
Verify an active session exists before launching if the result will write files.

## Examples

```
User: /plan-story
→ Agent asks: "What would you like to plan? (act/chapter/scene/event)"

User: /plan-story scene 0204
→ Agent begins scene-level planning for scene 0204

User: /plan-story chapter 03
→ Agent begins chapter-level planning for chapter 03

User: Спланируй следующую главу акта 2
→ Triggers this skill, agent plans next chapter of act 2
```
