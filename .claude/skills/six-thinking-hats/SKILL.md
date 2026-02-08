---
name: six-thinking-hats
description: Multi-perspective problem analysis using Edward de Bono's Six Thinking Hats methodology.
  This skill spawns parallel Claude Code agents, each representing a distinct cognitive
  perspective (hat), then synthesizes results for comprehensive analysis. Use when facing
  complex decisions, strategic planning, creative problem-solving, or when explicit
  multi-dimensional thinking is needed. Triggers on phrases like "analyze from multiple
  perspectives", "six hats", "think through this comprehensively", or complex problems
  requiring balanced viewpoints.
---

# Six Thinking Hats - Parallel Multi-Perspective Analysis

A skill for comprehensive problem analysis using Edward de Bono's Six Thinking Hats methodology, implemented through parallel Claude Code agents.

## When to Use This Skill

Invoke this skill when:
- Facing complex decisions requiring multiple viewpoints
- Performing strategic planning or risk assessment
- Evaluating ideas comprehensively (pros/cons/alternatives)
- User explicitly requests "six hats", "multiple perspectives", or "comprehensive analysis"
- A problem would benefit from separating facts from emotions, risks from opportunities

## The Six Thinking Hats

Each hat represents a distinct cognitive mode. Five hats analyze in parallel, then Blue Hat synthesizes:

| Hat | Color | Cognitive Focus | Key Question |
|-----|-------|-----------------|--------------|
| White | Facts | Objective data, verified information | "What do we know? What don't we know?" |
| Red | Emotions | Intuition, gut feelings, emotional reactions | "How do I feel about this? What's my instinct?" |
| Black | Caution | Risks, problems, critical analysis | "What could go wrong? What are the dangers?" |
| Yellow | Optimism | Benefits, value, feasibility | "What are the advantages? Why will this work?" |
| Green | Creativity | Alternatives, innovations, new ideas | "What else is possible? What if we tried...?" |
| Blue | Synthesis | Integration, process management, final answer | "What does it all mean? What's the conclusion?" |

## Execution Workflow

### Phase 1: Parallel Analysis (5 Hats)

Launch 5 Task agents simultaneously in a SINGLE message with multiple tool calls:

```
Task(subagent_type="general-purpose", prompt=WHITE_HAT_PROMPT)
Task(subagent_type="general-purpose", prompt=RED_HAT_PROMPT)
Task(subagent_type="general-purpose", prompt=BLACK_HAT_PROMPT)
Task(subagent_type="general-purpose", prompt=YELLOW_HAT_PROMPT)
Task(subagent_type="general-purpose", prompt=GREEN_HAT_PROMPT)
```

### Phase 2: Synthesis (Blue Hat)

After receiving all 5 results, run synthesis:

```
Task(subagent_type="general-purpose", prompt=BLUE_HAT_PROMPT_WITH_ALL_RESULTS)
```

### Phase 3: Report to User

Present the synthesized conclusion with key insights from each perspective.

## Hat Agent Prompts

Load detailed prompts from `references/hat-prompts.md` when executing.

### Quick Reference Prompts

**White Hat (Facts):**
```
You are operating in FACTUAL ANALYSIS mode.
Focus ONLY on objective facts and data. Present neutral information without interpretation.
- What facts do we have?
- What information is missing?
- What sources can we verify?
FORBIDDEN: opinions, judgments, emotional reactions, speculation
```

**Red Hat (Emotions):**
```
You are operating in EMOTIONAL/INTUITIVE mode.
Express gut feelings and intuition. No justification needed.
- What's your immediate reaction?
- What feels right or wrong?
- What concerns or excites you intuitively?
Keep responses brief (30-second emotional snapshot).
FORBIDDEN: logical analysis, fact-checking, lengthy explanations
```

**Black Hat (Caution):**
```
You are operating in CRITICAL ANALYSIS mode.
Identify risks, problems, and potential failures. Be the devil's advocate.
- What could go wrong?
- What are the weaknesses?
- What obstacles exist?
Be constructive - identify real problems, not just pessimism.
```

**Yellow Hat (Optimism):**
```
You are operating in OPTIMISTIC ANALYSIS mode.
Find benefits, value, and opportunities. Explore positive outcomes.
- What are the advantages?
- Why could this work?
- What value does this create?
Be realistic - find genuine benefits, not false hope.
```

**Green Hat (Creativity):**
```
You are operating in CREATIVE mode.
Generate alternatives, innovations, and new approaches.
- What else is possible?
- How might we do this differently?
- What unconventional ideas exist?
Quantity over quality - generate many ideas without judgment.
Techniques: lateral thinking, "what if" scenarios, analogies
```

**Blue Hat (Synthesis):**
```
You are the SYNTHESIS ORCHESTRATOR.
Integrate all perspectives into a unified, actionable answer.

INPUT: Results from White, Red, Black, Yellow, Green hats
TASK:
1. Extract key insights addressing the original question
2. Integrate perspectives into coherent response
3. Resolve conflicts between viewpoints
4. Provide clear, actionable conclusion

OUTPUT REQUIREMENTS:
- Write as unified voice (don't list hat results separately)
- Directly answer the original question
- Make it practical and actionable
```

## Implementation Example

When user asks: "Should we migrate our monolith to microservices?"

**Step 1: Launch 5 parallel agents:**

Use Task tool 5 times in ONE message:

```markdown
Task 1 (White): "Analyze the monolith-to-microservices migration from FACTUAL perspective only.
What data exists about such migrations? What metrics matter? What's unknown?
Question: Should we migrate our monolith to microservices?"

Task 2 (Red): "Give your EMOTIONAL/INTUITIVE reaction to migrating from monolith to microservices.
No analysis needed - just gut feelings, concerns, excitement. Keep it brief.
Question: Should we migrate our monolith to microservices?"

Task 3 (Black): "Perform CRITICAL ANALYSIS of migrating to microservices.
What could go wrong? What risks exist? What's been overlooked?
Question: Should we migrate our monolith to microservices?"

Task 4 (Yellow): "Perform OPTIMISTIC ANALYSIS of migrating to microservices.
What benefits exist? Why might this succeed? What value would it create?
Question: Should we migrate our monolith to microservices?"

Task 5 (Green): "Generate CREATIVE ALTERNATIVES for the microservices question.
What other approaches exist? What unconventional options? What if we did something different?
Question: Should we migrate our monolith to microservices?"
```

**Step 2: Synthesize results:**

After collecting all 5 results, launch Blue Hat:

```markdown
Task (Blue): "SYNTHESIZE these 5 perspectives into a unified answer:

WHITE (Facts): [paste White result]
RED (Emotions): [paste Red result]
BLACK (Caution): [paste Black result]
YELLOW (Optimism): [paste Yellow result]
GREEN (Creative): [paste Green result]

Original question: Should we migrate our monolith to microservices?

Provide ONE coherent answer integrating all perspectives. Don't list them separately."
```

**Step 3: Present to user:**

Deliver the synthesized conclusion, optionally highlighting key insights from each perspective if useful for context.

## Configuration Options

### Complexity Modes

| Mode | Hats Used | When to Use |
|------|-----------|-------------|
| Quick (2 hats) | Yellow + Black | Simple evaluation of a single idea |
| Balanced (3 hats) | White + Black + Yellow | Fact-based decision making |
| Full (6 hats) | All | Complex strategic decisions |

### Timing Guidelines

- Quick mode: ~30 seconds
- Balanced mode: ~1 minute
- Full mode: ~2-3 minutes

## Best Practices

1. **Always run non-synthesis hats in parallel** - Use single message with multiple Task calls
2. **Keep hat prompts focused** - Each hat should stay in its cognitive mode
3. **Let Blue Hat resolve conflicts** - Don't try to merge perspectives yourself
4. **State the question clearly** - Include original question in each hat prompt
5. **Use sonnet model for speed** - For faster execution, add `model: "sonnet"` to Task calls

## Integration with Existing Workflows

This skill complements:
- Strategic planning sessions
- Risk assessment workflows
- Creative brainstorming
- Decision documentation

For deeper analysis on any single perspective, invoke that hat individually with more context.
