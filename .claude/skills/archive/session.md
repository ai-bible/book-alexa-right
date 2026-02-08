# Session Management Skill

**Skill Name:** `session`
**Version:** 1.0.0
**Feature:** Session Management with Copy-on-Write
**Architecture:** Frontend component of Hybrid (MCP + Skill) system

---

## Purpose

User-friendly interface for managing isolated book writing sessions with Copy-on-Write file handling. Provides commands for:
- Creating isolated work sessions
- Switching between sessions
- Tracking human retry attempts
- Committing changes to book
- Rolling back experiments

**Backend:** Uses MCP Server `session_management_mcp` tools under the hood.

---

## Commands

### `/session start <name> [description]`

**Description:** Create new session and activate it (Copy-on-Write)

**Usage:**
```bash
/session start work-on-chapter-01
/session start experimental-scene-0102 "Trying alternative version"
/session start rewrite-ending "Revising act 1 ending"
```

**What It Does:**
1. Calls MCP tool `create_session`
2. Creates empty session directory structure (~10 KB)
3. Sets up Copy-on-Write file tracking
4. Updates `workspace/session.lock` with active session
5. All subsequent file writes will trigger CoW (copy from global on first write)

**Example Output:**

```markdown
✅ SESSION CREATED: work-on-chapter-01

📂 Session Path:
   workspace/sessions/work-on-chapter-01/

⚡ Copy-on-Write Mode:
   • Empty session created (~10 KB structure only)
   • Files will copy on first write
   • Read operations use global files by default

🔒 Session activated (written to session.lock)

💡 How CoW works:
   1. Read "acts/.../plan.md" → Reads from global (not yet modified)
   2. Write "acts/.../plan.md" → CoW: Copies to session, then modifies
   3. Read "acts/.../plan.md" → Reads from session (now modified)

🚀 Ready to work in session!
```

---

### `/session list`

**Description:** List all sessions (active, inactive, crashed)

**Usage:**
```bash
/session list
```

**What It Does:**
1. Calls MCP tool `list_sessions`
2. Scans `workspace/sessions/` directory
3. Loads metadata from each `session.json`
4. Formats as table with status indicators

**Example Output:**

```markdown
📋 SESSIONS (3 total)

┌────────────────────────────┬──────────┬────────────┬──────────┐
│ Name                       │ Status   │ Created    │ Changes  │
├────────────────────────────┼──────────┼────────────┼──────────┤
│ work-on-chapter-01         │ ACTIVE   │ 2025-11-09 │ 5 files  │
│ experimental-scene-0102    │ INACTIVE │ 2025-11-08 │ 1 file   │
│ rewrite-act-1-ending       │ CRASHED  │ 2025-11-06 │ unknown  │
└────────────────────────────┴──────────┴────────────┴──────────┘

🔒 Active: work-on-chapter-01

⚠️ Crashed sessions (1):
   • rewrite-act-1-ending
     Action required: /session cancel rewrite-act-1-ending

💡 Commands:
   - Switch: /session switch <name>
   - Commit: /session commit
   - Cancel: /session cancel
```

---

### `/session status`

**Description:** Show detailed status of active session

**Usage:**
```bash
/session status
```

**What It Does:**
1. Calls MCP tool `get_active_session`
2. Shows session metadata
3. Lists all modified/created files (CoW tracking)
4. Shows human retry count
5. Displays session size

**Example Output:**

```markdown
📂 ACTIVE SESSION: work-on-chapter-01

Status: ACTIVE
Created: 2 hours ago
Description: Generating all scenes for chapter 01

📊 Changes (uncommitted):
   • Modified: 3 files
   • Created: 2 files
   • Deleted: 0 files

🔄 Human Retries: 2
   • scene-0101.md: 2 retries
     - Retry 1: "Too much exposition"
     - Retry 2: "Character voice inconsistent"

💾 Session Size: 2.3 MB

📁 Paths:
   • Session: workspace/sessions/work-on-chapter-01/
   • Context: workspace/sessions/work-on-chapter-01/context/
   • Acts: workspace/sessions/work-on-chapter-01/acts/
```

---

### `/session switch <name>`

**Description:** Switch to different session

**Usage:**
```bash
/session switch experimental-scene-0102
```

**What It Does:**
1. Calls MCP tool `switch_session`
2. Updates `workspace/session.lock` to new active session
3. All subsequent operations now use the switched session

**Example Output:**

```markdown
🔄 SWITCHED SESSION

From: work-on-chapter-01
To:   experimental-scene-0102

📂 Active Session Directory:
   workspace/sessions/experimental-scene-0102/

📊 Progress:
   • Modified files: 1
   • Created files: 0
   • Session size: 487 KB
   • Human retries: 0

💡 Resume work or commit when ready
```

**Error Handling:**
- If session not found → "Session '{name}' not found. Run /session list"
- If session crashed → "Session is CRASHED. Cancel first: /session cancel {name}"

---

### `/session commit [name]`

**Description:** Commit session changes to global files (copy CoW files to book)

**Usage:**
```bash
/session commit                    # Commit active session
/session commit work-on-chapter-01 # Commit specific session
```

**What It Does:**
1. Calls MCP tool `commit_session` (first call shows preview)
2. Shows all files that will be overwritten
3. Requires force=True for actual commit
4. Copies all CoW files from session to global (context/, acts/)
5. Archives human retries to `workspace/retries-archive/`
6. Deletes session directory
7. Clears `session.lock`

**Example Output (First Call - Preview):**

```markdown
⚠️ COMMIT SESSION: work-on-chapter-01

📊 Changes to be committed:

   Modified files (3):
     • acts/act-1/chapters/chapter-01/content/scene-0101.md
     • acts/act-1/chapters/chapter-01/content/scene-0102.md
     • context/characters/alexa-romanova-timeline.json

   Created files (2):
     • acts/act-1/chapters/chapter-01/scenes/scene-0103-blueprint.md
     • acts/act-1/chapters/chapter-01/scenes/scene-0104-blueprint.md

   Human retries: 2
     • scene-0101.md: Too much exposition, needs more action
     • scene-0102.md: Character voice inconsistent

❓ This will OVERWRITE global files.
💡 To proceed: Use MCP tool commit_session(name='work-on-chapter-01', force=True)
```

**Example Output (After Force Commit):**

```markdown
✅ SESSION COMMITTED

Session: work-on-chapter-01

📁 Files copied to global:
   ✓ acts/act-1/chapters/chapter-01/content/scene-0101.md
   ✓ acts/act-1/chapters/chapter-01/content/scene-0102.md
   ✓ context/characters/alexa-romanova-timeline.json
   ✓ acts/act-1/chapters/chapter-01/scenes/scene-0103-blueprint.md
   ✓ acts/act-1/chapters/chapter-01/scenes/scene-0104-blueprint.md

📦 Human retries archived:
   workspace/retries-archive/work-on-chapter-01/

🗑️ Session directory removed
🔓 Session lock cleared

🎉 Changes committed to book!
```

---

### `/session cancel [name]`

**Description:** Cancel session and discard all changes (rollback)

**Usage:**
```bash
/session cancel                    # Cancel active session
/session cancel experimental-v2    # Cancel specific session
```

**What It Does:**
1. Calls MCP tool `cancel_session`
2. Optionally backs up human retries (default: true)
3. Deletes entire session directory
4. Clears `session.lock` if active
5. Global files (context/, acts/) remain unchanged

**Example Output:**

```markdown
🛑 SESSION CANCELLED

Session: work-on-chapter-01

📊 Discarded changes:
   • Modified files: 5
   • Created files: 2
   • Human retries: 2

📦 Human retries backed up:
   workspace/retries-archive/work-on-chapter-01-cancelled-20251109-143000/

🗑️ Session directory removed
🔓 Session lock cleared

💡 Global files (context/, acts/) unchanged
```

**Error Handling:**
- If no active session → "No active session. Specify: /session cancel <name>"
- If session not found → "Session '{name}' not found"

---

### `/retry <file> <reason>`

**Description:** Record human retry attempt for a file

**Usage:**
```bash
/retry scene-0101.md "Too much exposition, needs more action"
/retry acts/act-1/chapters/chapter-01/content/scene-0102.md "Character voice inconsistent"
```

**What It Does:**
1. Calls MCP tool `record_human_retry`
2. Resolves file path (session → global fallback)
3. Copies current version to `human-retries/`
4. Saves reason to `.reason.txt` file
5. Updates session.json with retry entry
6. Assigns retry number

**Example Output:**

```markdown
✅ HUMAN RETRY RECORDED

📁 File: acts/act-1/chapters/chapter-01/content/scene-0101.md
🔢 Retry Number: 1
📝 Reason: Too much exposition, needs more action
🤖 Source: User command

💾 Saved to:
   • workspace/sessions/work-on-chapter-01/human-retries/scene-0101.md-retry-1.md
   • workspace/sessions/work-on-chapter-01/human-retries/scene-0101.md-retry-1.md.reason.txt

💡 Previous version preserved for review
```

**AI Auto-Detection:**

AI can also auto-detect retry requests from user feedback:

```
User: "This is bad, rewrite scene 0101, too much dialogue"

AI internally calls:
  record_human_retry(
    file_path="scene-0101.md",
    reason="User feedback: Too much dialogue",
    auto_detected=True
  )

Then regenerates with feedback applied
```

---

## Implementation

### Skill Structure

```markdown
# When invoked, this skill:

## 1. Parses Command
- Extracts subcommand: start, list, status, switch, commit, cancel
- Extracts session name (if provided)
- Extracts description/reason (if provided)

## 2. Validates Input
- Session name format (alphanumeric, hyphens, underscores)
- Subcommand is valid
- Required parameters present

## 3. Calls MCP Tool
- Maps subcommand to MCP tool (see table below)
- Passes parameters correctly
- Handles special cases (commit requires force=True on second call)

## 4. Formats Output
- Adds emoji icons for visual clarity
- Formats tables for readability
- Shows file paths clearly
- Adds actionable next steps
- Includes error guidance
```

### MCP Tool Mapping

| Skill Command | MCP Tool | Parameters |
|---------------|----------|------------|
| `/session start work-ch01` | `create_session` | `name="work-ch01", description=""` |
| `/session start work-ch01 "desc"` | `create_session` | `name="work-ch01", description="desc"` |
| `/session list` | `list_sessions` | (no parameters) |
| `/session status` | `get_active_session` | (no parameters) |
| `/session switch experimental` | `switch_session` | `name="experimental"` |
| `/session commit` | `commit_session` | `name=None, force=False` (preview) |
| `/session commit --force` | `commit_session` | `name=None, force=True` (execute) |
| `/session cancel` | `cancel_session` | `name=None, backup_retries=True` |
| `/retry file.md "reason"` | `record_human_retry` | `file_path="file.md", reason="reason", auto_detected=False` |

---

## User Interaction Patterns

### Pattern 1: Create Session and Work

```
User: /session start work-on-chapter-01
→ Session created (10 KB empty structure)

User: "Generate scene 0101"
→ generation-coordinator runs
→ CoW triggered: acts/.../scene-0101.md copied to session
→ Scene generated in session

User: /session status
→ Shows: 1 modified file, session size 487 KB
```

### Pattern 2: Human Retry Workflow

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

### Pattern 3: Experimental Sessions

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

### Pattern 4: Session Switching

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

### Pattern 5: Commit Workflow

```
User: /session status
→ Shows: 5 modified files, 2 human retries

User: /session commit
→ Preview of changes shown
→ "To proceed: use force=True"

User decides changes are good

AI: commit_session(name='work-on-chapter-01', force=True)
→ Files copied to global
→ Retries archived
→ Session removed
→ Changes committed to book!
```

---

## Copy-on-Write Details

### How CoW Works

**Session Creation:**
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

**First Write (CoW Trigger):**
```
AI writes to: acts/act-1/chapters/chapter-01/plan.md

CoW Logic:
1. Check if file exists in session: NO
2. Check if file exists in global: YES
3. Copy global → session (CoW triggered)
4. Add to session.json["cow_files"]
5. Write new content to session copy
```

**Subsequent Writes:**
```
AI writes to: acts/act-1/chapters/chapter-01/plan.md (again)

CoW Logic:
1. Check if file exists in session: YES (from previous CoW)
2. Skip copy (already in session)
3. Write new content directly to session copy
```

**Reading:**
```
AI reads: acts/act-1/chapters/chapter-01/plan.md

Resolution:
1. Check session: workspace/sessions/my-work/acts/.../plan.md
2. If exists → Read from session (modified copy)
3. If not exists → Read from global (original)
```

**Commit:**
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

---

## Error Messages

**Clear, actionable error messages:**

```markdown
❌ ERROR: No active session

💡 Next steps:
   - Create new session: /session start <name>
   - Switch to existing: /session list → /session switch <name>
```

```markdown
❌ ERROR: Session 'experimental-v2' not found

💡 Available sessions: /session list
```

```markdown
❌ ERROR: Session 'old-work' is CRASHED

Session process died unexpectedly.

💡 Action required:
   - Cancel corrupted session: /session cancel old-work
   - Or investigate manually: workspace/sessions/old-work/session.json
```

```markdown
❌ ERROR: File not found: scene-0101.md

Checked paths:
   • Session: workspace/sessions/my-work/acts/.../scene-0101.md
   • Global: acts/.../scene-0101.md

💡 Generate scene first: "Generate scene 0101"
```

---

## Integration with MCP Server

**This skill requires:** `session_management_mcp` MCP server

**Check MCP server is loaded:**
```bash
# List MCP servers
/mcp list

# Should show:
# - session_management_mcp (✓ loaded)
```

**If MCP server not loaded:**
1. Check `mcp-servers/session_management_mcp.py` exists
2. Add to MCP config if needed
3. Restart Claude Code

---

## Examples

### Example 1: Full Session Lifecycle

```bash
# Start session
/session start work-on-chapter-01

# Work on scenes
"Generate scene 0101"
"Generate scene 0102"

# Not satisfied with 0101
/retry scene-0101.md "Too much exposition"
"Regenerate scene 0101 with less exposition"

# Check progress
/session status

# Satisfied - commit changes
/session commit
# (shows preview)

# Confirm commit via MCP tool
commit_session(name='work-on-chapter-01', force=True)
```

### Example 2: Experimental Workflow

```bash
# Create experimental session
/session start experimental-darker-tone "Trying darker atmosphere"

# Generate alternative version
"Generate scene 0102 with darker, more oppressive atmosphere"

# Don't like it - cancel
/session cancel

# (all changes discarded, retries archived)
```

### Example 3: Parallel Sessions

```bash
# Main work
/session start chapter-01-work

# Generate scenes 0101-0105
"Generate scenes 0101 through 0105"

# Want to experiment with scene 0103
/session start experimental-0103 "Alternative version of 0103"

# Try alternative
"Generate scene 0103 with different approach"

# Compare versions
/session list

# Decide to keep experimental version
/session commit experimental-0103

# Back to main work
/session switch chapter-01-work

# Continue main work
"Generate scene 0106"
```

---

## Testing

### Manual Testing

```bash
# 1. Create session
/session start test-session

# 2. Check it's active
/session list
/session status

# 3. Make changes (trigger CoW)
"Generate scene 9999"

# 4. Record retry
/retry scene-9999.md "Testing retry recording"

# 5. Check status again
/session status

# 6. Try commit preview
/session commit

# 7. Cancel instead
/session cancel

# 8. Verify cleanup
/session list
# (should show no active session)
```

### Expected Behavior

- Session created with ~10 KB size
- CoW triggered on first write
- Retries recorded correctly
- Commit shows preview first
- Cancel removes session directory
- session.lock updated correctly

---

## Future Enhancements (Out of Scope for v1.0)

1. **Session templates**
   ```bash
   /session start my-work --template chapter-generation
   # Pre-configures cleanup rules, retry settings
   ```

2. **Session comparison**
   ```bash
   /session diff main-work experimental-v2
   # Shows differences between sessions
   ```

3. **Partial commit**
   ```bash
   /session commit --files scene-0101.md,scene-0102.md
   # Commits only specific files
   ```

4. **Session merge**
   ```bash
   /session merge experimental-v2 into main-work
   # Merges selected changes
   ```

---

## Documentation Links

- **MCP Server:** `mcp-servers/session_management_mcp.py`
- **Progress Tracking:** `PROGRESS.md` (Session Management section)
- **Architecture:** `CLAUDE.md` (Workflow Router)

---

## Version History

**v1.0.0** (2025-11-09)
- Initial release
- 6 commands: start, list, status, switch, commit, cancel
- 1 auxiliary command: retry
- MCP integration
- Copy-on-Write file handling
- Human retry tracking

---

**Last Updated:** 2025-11-09
**Author:** AI-Assisted Writing System
**Status:** Implemented
