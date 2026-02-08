# Agent Architect Skill - Usage Examples

## Example 1: Quick Mode - Performance Optimization

### User Input
```
/agent-architect

"I have 7 validators checking content against different constraints.
They run sequentially and take 8 minutes total. How can I speed this up?"
```

### Claude Response Flow

**Step 1: Acknowledge**
```
I understand you have a validation pipeline with 7 sequential validators
taking 8 minutes. Let me fetch the latest Anthropic documentation on
parallelization and launch the agent-architect to analyze this.
```

**Step 2: Fetch Documentation** (automatic, transparent to user)
```
[WebFetch: docs.anthropic.com/agent-patterns]
[WebFetch: docs.anthropic.com/multi-agent-systems]
```

**Step 3: Launch Agent** (shows loading indicator)
```
Launching agent-architect with your requirements...
```

**Step 4: Present Results**
```
Based on analysis and Anthropic best practices, here are recommendations:

### Recommended Architecture: Parallel Validation with Aggregator

┌─────────────┐
│   Content   │
└──────┬──────┘
       │
   ┌───┴────┐
   │Dispatch│
   └───┬────┘
       │
   ┌───┼──────────────────┐
   │   │                  │
   ▼   ▼                  ▼
[Val1][Val2] ... [Val7]
   │   │                  │
   └───┼──────────────────┘
       │
   ┌───▼────┐
   │Aggregate│
   └────────┘

### Key Changes:
1. **Parallelize validators** - Run all 7 concurrently (LIFT-COT research
   shows up to 7 validators can run efficiently in parallel)

2. **Add aggregator agent** - Synthesizes results from all validators

3. **Expected improvement** - 8 minutes → ~1-2 minutes (time of slowest
   validator + aggregation overhead)

### Implementation Guidance:
[... detailed steps ...]

### Research Justification:
- LIFT-COT research demonstrates 7-agent parallel validation is optimal
- Anthropic docs recommend aggregator pattern for parallel outputs
- CoS research shows independent constraint checks can be parallelized

Would you like me to help implement this architecture?
```

---

## Example 2: Guided Mode - Agent vs Skill Decision

### User Input
```
/agent-architect

[Questionnaire appears]

1. Problem: "I need to validate file names follow our naming convention"
2. Type: Deciding between agent vs. skill
3. Requirements:
   - Input: file path
   - Output: valid/invalid + error message
   - Error tolerance: High (easy to fix)
   - Steps: Check regex pattern, return result
4. Current setup: Manual checking
```

### Claude Response Flow

**Step 1: Acknowledge and Clarify**
```
Got it. You need automated file naming validation. Quick clarification:
- How complex is the naming convention? (simple regex or complex rules?)
- Is there any context needed? (e.g., checking against existing files?)
```

**User clarifies:**
```
Simple regex: ^chapter-\d{2}-scene-\d{4}\.md$
No context needed.
```

**Step 2-3: Fetch docs and launch agent** (automatic)

**Step 4: Present Results**
```
### Recommendation: Use a Claude Skill, NOT an Agent

**Reasoning:**
✓ Simple, repetitive task (regex validation)
✓ High error tolerance (naming mistakes easy to fix)
✓ Minimal context (<100 tokens)
✓ Single clear constraint (naming pattern)
✓ Algorithmic steps (check regex, return boolean)

This matches ALL criteria for a Skill (per Anthropic guidelines).

### Skill Structure:
```markdown
---
name: validate-filename
description: Validates file names match chapter-scene pattern
---

You are a filename validator. Check if the provided filename matches:
`^chapter-\d{2}-scene-\d{4}\.md$`

Return:
- ✓ Valid: [filename]
- ✗ Invalid: [filename] - [error reason]
```

### Usage:
```bash
/validate-filename chapter-01-scene-0001.md
# Output: ✓ Valid: chapter-01-scene-0001.md

/validate-filename scene-1.md
# Output: ✗ Invalid: scene-1.md - Missing chapter prefix
```

### Why NOT an agent:
- Overkill for simple validation
- Wastes tokens on agent scaffolding
- Adds unnecessary complexity
- Skills are 10x faster for this use case

Want me to create the skill file for you?
```

---

## Example 3: Design New System

### User Input
```
/agent-architect

"Design a content generation system that:
- Takes scene blueprint as input
- Generates prose following 8 specific constraints
- Validates output against all constraints
- Allows human approval before finalizing
- Handles failures gracefully"
```

### Claude Response Flow

**Step 1: Acknowledge and Clarify**
```
Interesting! A constrained content generation system with validation.
Before I dive in, a few questions:

- How long is typical output? (affects resource management)
- Are the 8 constraints independent or interdependent?
- What's acceptable failure rate?
```

**User answers:**
```
- ~3000-5000 words per scene
- Constraints are independent (style, length, POV, tense, etc.)
- Very low failure rate acceptable (publishing context)
```

**Step 2-4: Fetch docs, launch agent, present results**
```
### Recommended Architecture: 6-Step Generation Workflow

Based on Chain-of-Specificity (CoS) research and Anthropic multi-agent patterns:

┌────────────────────────────────────────────────────────────┐
│ Step 1: Blueprint Validation                               │
│ Agent: blueprint-validator                                 │
│ Purpose: Pre-flight checks before expensive generation     │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ Step 2: Verification Plan (HUMAN APPROVAL REQUIRED)        │
│ Agent: verification-planner                                │
│ Purpose: Show user what will be validated, get approval    │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ Step 3: Iterative Generation (CoS Pattern)                 │
│ Agent: prose-writer                                        │
│ Iterations: 3 passes                                       │
│   Pass 1: General goal + 3 constraints                     │
│   Pass 2: Refine + next 3 constraints                      │
│   Pass 3: Final + last 2 constraints + integration         │
│ Justification: CoS research shows 65.4% improvement for    │
│                multi-constraint tasks with iteration       │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ Step 4: Fast Compliance Check (<30s)                       │
│ Agent: blueprint-compliance-fast-checker                   │
│ Purpose: Quick fail-fast before expensive validation       │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ Step 5: Parallel Full Validation                           │
│ Agents: 8 validators (one per constraint), parallel        │
│   - style-validator                                        │
│   - length-validator                                       │
│   - pov-validator                                          │
│   - tense-validator                                        │
│   - character-consistency-validator                        │
│   - world-consistency-validator                            │
│   - plot-continuity-validator                              │
│   - prose-quality-validator                                │
│ Aggregator: validation-aggregator                          │
│ Justification: LIFT-COT research - up to 7-8 validators    │
│                can run efficiently in parallel             │
└────────────────────────────────────────────────────────────┘
                         ↓
┌────────────────────────────────────────────────────────────┐
│ Step 6: Human Review & Finalization                        │
│ Present: Validation results + generated content            │
│ Action: Human approves or requests revisions               │
└────────────────────────────────────────────────────────────┘

### Key Design Decisions:

**1. Iterative Generation (CoS Research)**
- Multi-pass approach handles 8 constraints better than one-shot
- Each pass focuses on subset of constraints
- 65.4% improvement over direct prompting

**2. Resource Management (LIFT-COT Research)**
```python
# Pseudo-code for prose-writer agent
class LengthControlUnit:
    def monitor_output(self, current_tokens, max_tokens=5000):
        if current_tokens > max_tokens * 0.9:
            self.apply_penalty()
            self.simplify_reasoning()
```

**3. Fail-Fast Pattern (Anthropic Best Practice)**
- Fast check before expensive validation
- Saves ~5-7 minutes on obvious failures

**4. Parallel Validation (LIFT-COT Research)**
- 8 validators run concurrently
- Aggregator synthesizes results
- 8 minutes sequential → ~2 minutes parallel

**5. Human-in-the-Loop (Anthropic Guideline)**
- Critical: Verification plan approval (Step 2)
- Critical: Final content approval (Step 6)
- Graceful degradation if human delayed

### Artifact-Based Communication:
```json
{
  "blueprint_path": "/path/to/scene-0001-blueprint.md",
  "constraints": [
    {"id": 1, "type": "style", "spec": "..."},
    {"id": 2, "type": "length", "spec": "3000-5000 words"},
    ...
  ],
  "output_path": "/path/to/scene-0001.md",
  "validation_results_path": "/path/to/validation-report.json"
}
```

**Never pass >100 lines through prompts - always use file artifacts.**

### Error Handling:
```
Generation failure → Retry up to 3 times with adjusted constraints
Validation failure → Show detailed report, allow human override
Context overflow → Automatic artifact extraction and summarization
```

### Performance Estimates:
- Total time: 5-8 minutes per scene
  - Blueprint validation: 10s
  - Human approval: 30s
  - Generation: 3-5 min
  - Fast check: 20s
  - Full validation: 1-2 min
  - Human review: variable

Want me to help implement this architecture?
```

---

## Example 4: Debugging Existing System

### User Input
```
/agent-architect

"Our agent system keeps losing information when passing context between agents.
Currently we have:
- Planner agent → outputs 500-line plan
- Generator agent → reads plan, writes content
- Validator agent → reads content, validates

Generator seems to miss details from planner."
```

### Claude Response

```
Classic context overflow issue! Let me fetch Anthropic's guidance on
agent communication...

[Analysis from agent-architect]

### Problem Identified: Context Passing Anti-Pattern

**Current (problematic):**
```
Planner → [500 lines in prompt] → Generator
```

This violates Anthropic's guideline: **Never pass >100 lines in prompts**

**Why it fails:**
- LLM attention degrades with long context
- Information loss in middle (lost-in-the-middle phenomenon)
- Token limits approach quickly

### Recommended Fix: Artifact-Based Communication

**New architecture:**
```
Planner → [writes plan.md] → [passes file path] → Generator
                                                     ↓
                                            [reads file directly]
```

**Implementation:**
```markdown
<!-- In planner agent -->
1. Write full plan to workspace/plan-{id}.md
2. Return to orchestrator: {"plan_path": "workspace/plan-{id}.md"}

<!-- In orchestrator -->
3. Pass to generator: "Read the plan from {plan_path} and generate content"

<!-- In generator agent -->
4. First action: Read file at {plan_path}
5. Process full plan content
6. Generate based on complete information
```

### Additional Improvements:

**1. Add structured metadata:**
```json
{
  "plan_path": "workspace/plan-0001.md",
  "key_points": [
    "Scene starts at dawn",
    "Character discovers secret",
    "Ends with cliffhanger"
  ],
  "constraints": ["3000 words", "past tense", "3rd person limited"]
}
```
Pass metadata + path (not full content)

**2. Implement checkpointing:**
```
workspace/
├── plan-0001.md              ← Full plan
├── content-0001-draft.md     ← Generator output
└── validation-0001.json      ← Validation results
```

**3. Add validation:**
```markdown
<!-- In orchestrator -->
After planner completes:
- Check plan file exists
- Verify file size < 1MB
- Log file path for debugging
```

### Expected Improvements:
- ✓ No information loss
- ✓ Supports unlimited plan length
- ✓ Better token efficiency
- ✓ Debuggable (can inspect intermediate files)
- ✓ Follows Anthropic best practices

### Research Backing:
- Anthropic docs: "Use file-based artifacts for data >100 lines"
- LIFT-COT: Resource-aware generation prevents context overflow
- Best practice: Explicit handoff protocols

Want help implementing these changes?
```

---

## Common Patterns

### Pattern 1: "Should this be agent or skill?"
**Trigger:** `/agent-architect` + description of repetitive task
**Output:** Decision matrix + recommendation + example code

### Pattern 2: "How to parallelize?"
**Trigger:** `/agent-architect` + "slow sequential workflow"
**Output:** Parallel architecture + research justification + perf estimates

### Pattern 3: "How to handle constraints?"
**Trigger:** `/agent-architect` + "multiple constraints"
**Output:** CoS-based iterative architecture

### Pattern 4: "Context overflow"
**Trigger:** `/agent-architect` + "losing information"
**Output:** Artifact-based communication pattern

### Pattern 5: "Design from scratch"
**Trigger:** `/agent-architect` + detailed requirements
**Output:** Complete architecture + diagrams + implementation plan

---

## Tips for Best Results

1. **Be specific** - "7 validators, sequential, 8 minutes" vs "slow system"
2. **Mention constraints** - Number and type of constraints matter
3. **Include context** - What you've tried, what failed
4. **State goals** - Performance? Reliability? Maintainability?
5. **Ask follow-ups** - "Can you show me how to implement X?"

---

**Ready to try it?** Type `/agent-architect` in Claude Code!
