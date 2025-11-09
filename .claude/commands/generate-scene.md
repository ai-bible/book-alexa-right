---
name: generate-scene
---

Generate scene content through multi-stage workflow. Usage:

**Interactive Generation:**
- `/generate-scene` - Start interactive scene generation session

**From Blueprint:**
- `/generate-scene [blueprint-file]` - Generate from existing scene blueprint

**Process:**
1. Plot architecture (scene purpose & structure)
2. Parallel development (structure, timeline, world, characters, tension)
3. Prose architecture (prose plan)
4. Prose generation (beat-by-beat writing)
5. Validation & integration

Invokes the director agent to coordinate all generation stages.

Outputs to `/workspace/generation-session-[ID]/`
