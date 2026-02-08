---
name: check-consistency
description: >-
  This skill should be used when the user asks to "check consistency",
  "check-consistency", "verify consistency", "find contradictions",
  "impact analysis", "what changed", "проверить согласованность",
  "найти противоречия", "анализ изменений", "что сломалось после правок",
  or wants to compare plan changes against already written content.
  Identifies contradictions, generates prioritized revision TODO.
---

# Check Consistency - Plan vs. Content Verification

Launch the `consistency-checker` agent to detect contradictions between
updated plans and already written content. Generates a prioritized
revision checklist.

## When to Use

- Writer has modified plans (strategic, chapter, scene) and needs to check impact
- Writer wants to verify no contradictions exist in written content
- After any significant plan change that might affect existing scenes

## Invocation

### Parse Arguments

Extract optional scope filters:

```
/check-consistency                    → Full check, all acts/chapters
/check-consistency act 1              → Scope: only act 1
/check-consistency chapter 03         → Scope: only chapter 03
/check-consistency scene 0204         → Scope: only scene 0204
/check-consistency --characters       → Focus: character consistency only
/check-consistency --plot             → Focus: plot consistency only
/check-consistency --world            → Focus: world consistency only
```

Argument format: `/check-consistency [scope] [--focus]`

### Launch Agent

Invoke the `consistency-checker` agent via the Task tool:

```
Task(
  subagent_type="consistency-checker",
  prompt="<scope and focus parameters>",
  description="Consistency check"
)
```

Pass to the agent:
1. Scope filter (act/chapter/scene or all)
2. Focus filter (characters/plot/world or all)
3. If no arguments, run full check across all written content

## What the Agent Does

### Step 1: Detect Changes
- Read modified plan files
- Identify specific changes (character arcs, plot points, world elements)
- List all affected elements

### Step 2: Analyze Written Content
- Search written scenes for references to changed elements
- Identify contradictions with updated plans
- Flag scenes requiring attention

### Step 3: Assess Severity
- **CRITICAL**: Direct contradictions (character did X, plan now says never did)
- **HIGH**: Missing new elements (new thread not reflected in written scenes)
- **MEDIUM**: Tone/motivation misalignment
- **LOW**: Minor details (names, minor world details)

### Step 4: Generate TODO
- Group issues by chapter/scene
- Order by severity
- Provide specific revision guidance per item

## Output

Report saved to: `workspace/consistency-checks/todo-{timestamp}.md`

The agent returns a summary with:
- Total issues found by severity
- Chapters affected
- Top critical/high issues requiring immediate attention
- Path to the full report file

## Examples

```
User: /check-consistency
→ Agent runs full check, reports: "Found 3 critical, 5 high issues across 4 chapters"

User: /check-consistency act 1
→ Agent checks only act 1 content against act 1 plans

User: /check-consistency --characters
→ Agent focuses on character consistency (motivations, knowledge, arcs)

User: Я изменил план главы 3, проверь что не сломалось
→ Triggers this skill, agent checks chapter 3 and related content
```
