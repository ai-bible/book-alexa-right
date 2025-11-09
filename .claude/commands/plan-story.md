---
name: plan-story
---

Start interactive story planning session. Usage:

**Planning Levels:**
- `/plan-story act [act-number]` - Plan entire act
- `/plan-story chapter [chapter-number]` - Plan specific chapter
- `/plan-story scene [scene-description]` - Plan specific scene

**Interactive Mode:**
- `/plan-story` - Start with guided questions about what you want to plan

**Process:**
The planning-coordinator will guide you through:
1. Understanding your vision (where are we, where are we going)
2. Exploring possibilities and consequences
3. Breaking down into concrete events/scenes
4. Creating detailed plans with dependencies

Invokes the planning-coordinator agent.

Outputs to `/workspace/planning-session-[ID]/`
