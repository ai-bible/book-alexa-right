---
name: storyline
description: >-
  This skill should be used when the user asks to "manage storyline",
  "storyline status", "develop storyline", "create storyline", "update storyline",
  "storyline connections", "character arc", "арка персонажа", "сюжетная линия",
  "статус сюжетной линии", "развитие персонажа", or mentions tracking character
  development across the narrative. Provides subcommands for status, develop,
  new, update, and connections.
---

# Storyline - Character Storyline Management

Launch the `storyline-developer` agent to manage character storylines, track arcs,
and develop character journeys across the narrative.

## When to Use

- Writer wants to check, create, or develop a character's storyline
- Writer needs to update a storyline after a story event
- Writer wants to see connections between character arcs

## Subcommands

### Parse Arguments

Extract subcommand, character name, and optional parameters:

```
/storyline status Mara              → subcommand: status, character: Mara
/storyline develop Mara             → subcommand: develop, character: Mara
/storyline new Kael                 → subcommand: new, character: Kael
/storyline update Mara "discovered the truth about Project Babylon"
                                    → subcommand: update, character: Mara, event: "..."
/storyline connections Mara         → subcommand: connections, character: Mara
/storyline                          → no subcommand, agent will ask
```

Argument format: `/storyline [subcommand] [character-name] [description...]`

### Subcommand Reference

| Subcommand | Purpose | Dialogue Style |
|------------|---------|---------------|
| `status` | Show current state of character's storyline | Direct execution, clear report |
| `develop` | Collaborative storyline exploration | Full creative dialogue |
| `new` | Create new storyline for character | Structured questions + exploration |
| `update` | Update storyline after story event | Quick verification, then update |
| `connections` | Show storyline connections to other characters | Direct execution + optional exploration |

### Launch Agent

Invoke the `storyline-developer` agent via the Task tool:

```
Task(
  subagent_type="storyline-developer",
  prompt="<subcommand, character name, and context>",
  description="Storyline management"
)
```

Pass to the agent:
1. The subcommand (status/develop/new/update/connections)
2. Character name
3. Event description or query (if provided)
4. If no arguments, instruct agent to ask the user

## File Locations

Storyline files are stored at: `context/storylines/{character-name}.md`

Alternative location (per act): `acts/act-{N}/storylines/{character-name}.md`

The agent reads and updates these files as needed.

## Key Behaviors

### status
Return structured report: arc position, emotional state, active threads,
recent developments, next key moments. No creative dialogue needed.

### develop
Full interactive exploration. Ask about writer's vision, explore motivations,
present multiple development paths, guide discovery of character growth.

### new
Understand character's role, explore goals and conflicts, define initial
arc trajectory. Mix of structured questions and creative exploration.

### update
Verify event impact on character, ask about emotional/psychological effects,
update storyline state, identify new threads. Quick and focused.

### connections
Map related character arcs, shared plot threads, potential conflicts or
synergies. Direct output with option to explore further.

## Session Awareness

The storyline-developer handles file reads/writes internally.
For write operations, verify an active session exists first.

## Examples

```
User: /storyline status Mara
→ Agent returns structured status report for Mara's storyline

User: /storyline develop Mara
→ Agent begins interactive dialogue about Mara's character development

User: /storyline update Mara "She discovered Chronos lied about Project Babylon"
→ Agent verifies impact, updates storyline file

User: /storyline connections Kael
→ Agent shows how Kael's arc connects to other characters

User: /storyline
→ Agent asks: "Which character's storyline would you like to work with?"
```
