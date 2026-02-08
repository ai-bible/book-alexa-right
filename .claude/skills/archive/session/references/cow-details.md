# Copy-on-Write Details

## How CoW Works

### Session Creation

```
/session start my-work
→ Creates only directory structure:
  workspace/sessions/my-work/
  workspace/sessions/my-work/context/
  workspace/sessions/my-work/acts/
  workspace/sessions/my-work/artifacts/
  workspace/sessions/my-work/human-retries/
→ Size: ~10 KB (just directories, no files)
```

### First Write (CoW Trigger)

```
AI writes to: acts/act-1/chapters/chapter-01/plan.md

CoW Logic:
1. Check if file exists in session: NO
2. Check if file exists in global: YES
3. Copy global → session (CoW triggered)
4. Add to session.json["cow_files"]
5. Write new content to session copy
```

### Subsequent Writes

```
AI writes to: acts/act-1/chapters/chapter-01/plan.md (again)

CoW Logic:
1. Check if file exists in session: YES (from previous CoW)
2. Skip copy (already in session)
3. Write new content directly to session copy
```

### File Resolution (Reading)

```
AI reads: acts/act-1/chapters/chapter-01/plan.md

Resolution:
1. Check session: workspace/sessions/my-work/acts/.../plan.md
2. If exists → Read from session (modified copy)
3. If not exists → Read from global (original)
```

### Commit

```
/session commit

Commit Logic:
1. Read session.json["cow_files"] (list of modified files)
2. For each CoW file:
   - Copy session/path → global/path (overwrite)
3. Archive human-retries/
4. Delete session directory
5. Clear session.lock
```

### Cancel

```
/session cancel

Cancel Logic:
1. Optionally backup human-retries/ to retries-archive/
2. Delete entire session directory
3. Clear session.lock if this was active session
4. Global files remain completely untouched
```

## Session Directory Structure

```
workspace/sessions/{name}/
├── session.json          # Metadata, cow_files list, retry log
├── context/              # CoW copies of context files
├── acts/                 # CoW copies of act/chapter/scene files
├── artifacts/            # Generation artifacts for this session
└── human-retries/        # Archived retry versions
    ├── scene-0101.md-retry-1.md
    ├── scene-0101.md-retry-1.md.reason.txt
    ├── scene-0101.md-retry-2.md
    └── scene-0101.md-retry-2.md.reason.txt
```

## session.json Schema

```json
{
  "name": "work-on-chapter-01",
  "description": "Generating all scenes for chapter 01",
  "status": "active",
  "created_at": "2025-11-09T14:30:00Z",
  "cow_files": [
    "acts/act-1/chapters/chapter-01/content/scene-0101.md",
    "acts/act-1/chapters/chapter-01/content/scene-0102.md",
    "context/characters/alexa-romanova-timeline.json"
  ],
  "created_files": [
    "acts/act-1/chapters/chapter-01/scenes/scene-0103-blueprint.md"
  ],
  "retries": [
    {
      "file": "scene-0101.md",
      "retry_number": 1,
      "reason": "Too much exposition",
      "auto_detected": false,
      "timestamp": "2025-11-09T15:10:00Z"
    }
  ]
}
```
