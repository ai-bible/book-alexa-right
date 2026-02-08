# Session Interaction Patterns

## Pattern 1: Full Session Lifecycle

```
User: /session start work-on-chapter-01
→ Session created (10 KB empty structure)

User: "Generate scene 0101"
→ generation-coordinator runs
→ CoW triggered: acts/.../scene-0101.md copied to session
→ Scene generated in session

User: /session status
→ Shows: 1 modified file, session size 487 KB

User: /session commit
→ Preview shown
→ AI calls commit_session(force=True) after confirmation
→ Files copied to global, session removed
```

## Pattern 2: Human Retry Workflow

```
User: "Generate scene 0101"
→ Scene generated

User: /retry scene-0101.md "Too much exposition"
→ Retry #1 recorded in human-retries/

User: "Regenerate scene 0101 with less exposition"
→ Regenerated (modifies session copy)

User: /retry scene-0101.md "Character voice still off"
→ Retry #2 recorded

User: "Regenerate scene 0101 with authentic character voice"
→ Regenerated (third attempt)

User: /session status
→ Shows: 2 human retries for scene-0101.md
```

## Pattern 3: Experimental Sessions

```
User: /session start experimental-scene-0102 "Trying darker tone"
→ Session created

User: "Generate scene 0102 with darker tone"
→ Scene generated in experimental session

User: "Not good, darker doesn't work"
→ User decides to discard

User: /session cancel
→ All changes discarded, retries backed up
→ Global files unchanged (rollback complete)
```

## Pattern 4: Session Switching

```
User: /session start main-work
→ Working on main content

User: /session start experimental-v2
→ Trying alternative approach

User: /session list
→ Shows: main-work (INACTIVE), experimental-v2 (ACTIVE)

User: /session switch main-work
→ Back to main work

User: /session commit
→ Commits main work to book

User: /session switch experimental-v2
→ Back to experiment

User: /session cancel
→ Discards experiment
```

## Pattern 5: Commit Workflow (Two-Step)

```
User: /session status
→ Shows: 5 modified files, 2 human retries

User: /session commit
→ Preview of changes shown:
  Modified files (3):
    • acts/act-1/.../scene-0101.md
    • acts/act-1/.../scene-0102.md
    • context/characters/alexa-romanova-timeline.json
  Created files (2):
    • acts/act-1/.../scene-0103-blueprint.md
    • acts/act-1/.../scene-0104-blueprint.md
  Human retries: 2

→ "To proceed: use force=True"

User decides changes are good

AI: commit_session(name='work-on-chapter-01', force=True)
→ Files copied to global
→ Retries archived
→ Session removed
```

## Example Output Formats

### Session Created

```markdown
SESSION CREATED: work-on-chapter-01

Session Path:
   workspace/sessions/work-on-chapter-01/

Copy-on-Write Mode:
   - Empty session created (~10 KB structure only)
   - Files will copy on first write
   - Read operations use global files by default

Session activated (written to session.lock)

How CoW works:
   1. Read "acts/.../plan.md" → Reads from global (not yet modified)
   2. Write "acts/.../plan.md" → CoW: Copies to session, then modifies
   3. Read "acts/.../plan.md" → Reads from session (now modified)
```

### Session Status

```markdown
ACTIVE SESSION: work-on-chapter-01

Status: ACTIVE
Created: 2 hours ago
Description: Generating all scenes for chapter 01

Changes (uncommitted):
   - Modified: 3 files
   - Created: 2 files
   - Deleted: 0 files

Human Retries: 2
   - scene-0101.md: 2 retries
     - Retry 1: "Too much exposition"
     - Retry 2: "Character voice inconsistent"

Session Size: 2.3 MB
```

### Human Retry Recorded

```markdown
HUMAN RETRY RECORDED

File: acts/act-1/chapters/chapter-01/content/scene-0101.md
Retry Number: 1
Reason: Too much exposition, needs more action

Saved to:
   - workspace/sessions/.../human-retries/scene-0101.md-retry-1.md
   - workspace/sessions/.../human-retries/scene-0101.md-retry-1.md.reason.txt
```
