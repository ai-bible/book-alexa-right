---
name: agent-architect
description: Design, optimize, and refactor AI agent systems based on Anthropic best practices and latest research. Guides you through architectural decisions with interactive questionnaire, loads current documentation, and launches specialized agent-architect for detailed analysis.
---

# AI Agent Architecture Design Assistant

I'll help you design optimal agent systems based on Anthropic's best practices and latest research (CoS, LIFT-COT).

## Quick Start (For Experienced Users)

If you already know what you need, just provide your requirements directly:

**Example:**
> "I have 7 validators that check content against different constraints. They run sequentially and it's slow. How should I restructure this?"

I'll fetch the latest docs and launch the agent-architect immediately.

---

## Guided Mode (For Detailed Analysis)

If you prefer a structured approach, answer these questions:

## Step 1: Understanding Your Needs

Let me ask you a few questions to understand your requirements:

**1. What problem are you trying to solve?**
   - Describe the task/workflow you want to automate or optimize

**2. Is this about:**
   - [ ] Designing a new agent system from scratch
   - [ ] Optimizing existing agent architecture
   - [ ] Deciding between agent vs. skill
   - [ ] Fixing agent communication/performance issues
   - [ ] Other (please specify)

**3. Key Requirements (if known):**
   - Expected inputs and outputs?
   - Performance constraints (time, tokens, etc.)?
   - Error tolerance (high/low)?
   - Number of steps/complexity?

**4. Current Setup (if optimizing existing system):**
   - Brief description of current agent structure
   - What's not working well?
   - Performance bottlenecks?

---

Please answer these questions, and I'll:
1. Fetch the latest Anthropic documentation on agent design
2. Launch the specialized agent-architect with your requirements
3. Get you research-backed architectural recommendations

**Note:** If you already have a clear description, you can skip the questionnaire and provide it directly. I'll proceed with fetching documentation and launching the agent.

---

## Common Scenarios

Here are typical use cases where agent-architect can help:

### 🔧 Optimization
- "Our agents are hitting token limits from passing too much context"
- "Sequential workflow is slow, can we parallelize?"
- "Agent responses don't follow constraints consistently"

### 🏗️ Design
- "Should this be an agent or a skill?"
- "How to structure multi-agent content generation pipeline?"
- "What's the best way to validate outputs against multiple rules?"

### 🐛 Debugging
- "Agents keep losing information in handoffs"
- "Context window fills up too fast"
- "System doesn't handle failures gracefully"

### 📚 Learning
- "What are Anthropic's best practices for agent communication?"
- "How to implement human-in-the-loop approval?"
- "What does research say about multi-constraint tasks?"

---

## Quick Decision Framework (Reference)

While you think about your answers, here's a quick reference:

**Use Agent when:**
- Multiple constraints (>1) need balancing
- Domain knowledge required
- Multi-step reasoning needed
- Iterative refinement beneficial
- Low error tolerance

**Use Skill when:**
- Simple, repetitive task
- Single clear constraint
- High error tolerance
- Minimal context needed (<1000 tokens)
- Algorithmic, well-defined steps

**Ready?** Provide your answers above (or describe your problem directly), and I'll launch the full architectural analysis!

---

## Instructions for Claude (Internal)

When the user responds (either with direct problem description OR questionnaire answers):

### Step 0: Detect Mode
- **Quick Mode:** User provided direct problem description → Skip to Step 1
- **Guided Mode:** User is answering questionnaire → Ask follow-up questions if needed
- **Silent:** User is still reading → Wait for their input

### Step 1: Acknowledge and Summarize
Briefly summarize the user's requirements to confirm understanding.

If information is incomplete, ask 1-2 clarifying questions maximum.

### Step 2: Fetch Anthropic Documentation
Use WebFetch to load the latest documentation on agent design patterns:

1. **Agent Best Practices:**
   - URL: `https://docs.anthropic.com/en/docs/build-with-claude/agent-patterns`
   - Focus: Agent design patterns, decomposition, communication

2. **Multi-Agent Systems:**
   - URL: `https://docs.anthropic.com/en/docs/build-with-claude/multi-agent-systems`
   - Focus: Orchestration, parallelization, context management

3. **Prompt Engineering:**
   - URL: `https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering`
   - Focus: Constraint handling, iterative refinement

### Step 3: Launch Agent-Architect
Use the Task tool with `subagent_type: agent-architect` and provide:

```
User Requirements:
[Summarized user input from questionnaire]

Relevant Anthropic Documentation:
[Key excerpts from fetched docs]

Task:
[Based on user's problem type: design new system / optimize existing / agent vs skill decision / fix issues]

Please analyze the requirements, apply research principles (CoS, LIFT-COT), and provide:
1. Recommended architecture
2. Research justification
3. Implementation guidance
4. Potential issues and mitigations
```

### Step 4: Present Results
When agent-architect returns its analysis:
- Summarize key recommendations
- Highlight critical decisions
- Ask if user needs clarification or wants to explore specific aspects

---

## Example Usage Flow

**User:** `/agent-architect`
**Skill expands:** [Questionnaire appears]
**User:** "I need to validate generated content against 7 different constraints..."
**Claude:** [Fetches docs] → [Launches agent] → [Returns architectural recommendations]
