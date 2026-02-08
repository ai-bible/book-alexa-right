---
name: external-ai-export
description: Export generation context for external AI (Gemini, GPT, Claude API). Use when user chooses [E]xport after Step 3 verification plan approval, wants to generate scene with external AI instead of local Claude, or requests "/export-context" command. Creates self-contained package with all necessary context files for copy-paste into any AI chat interface.
---

# External AI Export

Export scene generation context as a portable package for use with any external AI (Gemini, GPT-4, Claude API, etc.).

## When to Use

After Step 3 (Verification Plan approval) in Generation Workflow:
1. User sees: `[G]enerate locally | [E]xport for external AI | [C]ancel`
2. User chooses `[E]`
3. This skill creates the export package

Or explicitly via `/export-context <scene_id>` command.

## Workflow

### Step 1: Show Package Configuration

```
Configure Export Package for Scene {SCENE_ID}:

Include in package:
[x] Blueprint (required)
[x] Constraints (required)
[x] Main prompt (required)
[x] Style guide
[ ] Character cards
[ ] Previous scene(s)
[ ] World bible excerpts

[P]roceed | [A]ll | [M]inimal | [C]ancel
```

User options:
- **P** = Proceed with selected
- **A** = Include all optional files
- **M** = Minimal (required only)
- **C** = Cancel, return to generation choice

### Step 2: Create Package

Create directory:
```
workspace/generation-runs/generation-scene-{ID}-{TIMESTAMP}/external/
```

Generate files from templates:
1. `00-QUICK-START.md` - From `assets/templates/00-quick-start.md.tmpl`
2. `01-MAIN-PROMPT.md` - From `assets/templates/01-main-prompt.md.tmpl`
3. `02-constraints.json` - Extract from blueprint verification section
4. `03-blueprint.md` - Copy scene blueprint
5. `04-style-guide.md` - From `.workflows/prose-style-guide.md`
6. `05-character-cards.md` - (if selected) From `context/characters/`
7. `06-previous-scenes.md` - (if selected) Previous scene content
8. `07-world-bible.md` - (if selected) Relevant world entries
9. `PACKAGE-INFO.txt` - Package metadata
10. `output/` - Empty directory for AI results

### Step 3: Show Success Message

```
Export package created!

Location:
workspace/generation-runs/.../external/

Files:
├── 00-QUICK-START.md     (start here)
├── 01-MAIN-PROMPT.md     (copy to AI)
├── 02-constraints.json
├── 03-blueprint.md
├── 04-style-guide.md
└── output/               (put result here)

Next steps:
1. Open 01-MAIN-PROMPT.md
2. Copy content to your AI
3. Get generated text
4. Save as output/scene-{SCENE_ID}-external.md
5. Return here and type "ready"

Type "ready" when result is in output/ folder
```

### Step 4: Wait for User

Workflow state changes to `waiting_for_external`.

When user types "ready":
1. Check `output/` folder for files
2. If no file: Show error, ask to save file
3. If empty file: Show error
4. If multiple files: Ask user to choose
5. If valid file: Proceed to Step 5 (Fast Compliance Check)

## Template Variables

Templates use `{{VARIABLE}}` placeholders:

| Variable | Source |
|----------|--------|
| `{{SCENE_ID}}` | Scene identifier (e.g., "0101") |
| `{{SCENE_TITLE}}` | Scene title from blueprint |
| `{{WORD_COUNT_TARGET}}` | From blueprint (e.g., "3,000-3,500") |
| `{{CONSTRAINTS_JSON}}` | Extracted constraints as JSON |
| `{{BEAT_STRUCTURE}}` | Beat summary from blueprint |
| `{{CHARACTER_NAMES}}` | POV and present characters |
| `{{TIMESTAMP}}` | Package creation timestamp |

## Resources

### assets/templates/

Template files for package generation:
- `00-quick-start.md.tmpl` - Quick start guide
- `01-main-prompt.md.tmpl` - Main generation prompt
- `package-info.txt.tmpl` - Package metadata

### references/

- `constraint-extraction.md` - How to extract constraints from blueprint

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No file in output/ | Error: "No file found. Save as scene-{ID}-external.md" |
| Multiple files | Ask: "Multiple files found. Which to use?" |
| Empty file | Error: "File is empty. Add generated content." |
| User cancels after export | State preserved, resume with `/generation-state resume` |
| Re-export same scene | Ask: "[O]verwrite \| [K]eep both \| [C]ancel" |
| Validation fails | Same flow as local generation (show issues, allow retry) |

## Integration Points

- **Generation Coordinator**: Add [E] option after Step 3
- **Workflow State MCP**: New status `waiting_for_external`
- **Validation Pipeline**: Reuse Step 5-6 for external results
