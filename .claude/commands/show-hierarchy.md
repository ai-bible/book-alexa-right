# Command: /show-hierarchy

Display visual hierarchy tree for acts, chapters, and scenes.

**Usage**: `/show-hierarchy [act_id] [--status]`

**Examples**:
- `/show-hierarchy` - Show all acts with their hierarchies
- `/show-hierarchy act-1` - Show hierarchy for Act 1 only
- `/show-hierarchy act-1 --status` - Include status for each entity (default)
- `/show-hierarchy act-2 --no-status` - Show structure without status

---

## Purpose

Visualizes the hierarchical structure of planning entities with status indicators.

**Use cases**:
- Understanding project structure
- Checking approval progress
- Identifying entities needing revalidation
- Verifying hierarchy after rebuild
- Planning workflow visualization

---

## Workflow

### Step 1: Parse parameters

Extract optional parameters:
- `act_id` - Optional filter (e.g., 'act-1')
- `--status` / `--no-status` - Include status (default: true)

### Step 2: Determine scope

**If act_id specified**:
- Show hierarchy for that act only
- Validate act exists

**If no act_id**:
- Show hierarchies for all acts
- List acts first, then expand each

### Step 3: Fetch hierarchy data

Use MCP tool `get_hierarchy_tree(act_id=..., include_status=...)` for each act.

### Step 4: Display hierarchy tree

Show formatted tree with box-drawing characters:

```
📊 HIERARCHICAL PLANNING STRUCTURE

═══════════════════════════════════════════════════════════
ACT 1
═══════════════════════════════════════════════════════════

act-1 [approved]
├── chapter-01 [approved]
│   ├── scene-0101 [approved]
│   ├── scene-0102 [approved]
│   └── scene-0103 [requires-revalidation] ⚠️
├── chapter-02 [approved]
│   ├── scene-0201 [approved]
│   └── scene-0202 [draft] 📝
└── chapter-03 [draft] 📝
    ├── scene-0301 [draft] 📝
    └── scene-0302 [draft] 📝

═══════════════════════════════════════════════════════════
ACT 2
═══════════════════════════════════════════════════════════

act-2 [draft] 📝
└── chapter-04 [draft] 📝
    ├── scene-0401 [draft] 📝
    ├── scene-0402 [draft] 📝
    └── scene-0403 [invalid] ❌

═══════════════════════════════════════════════════════════
LEGEND
═══════════════════════════════════════════════════════════

Status indicators:
  ✓ approved - Ready for next level / prose generation
  📝 draft - Being worked on, not yet approved
  ⚠️  requires-revalidation - Parent changed, needs review
  ❌ invalid - Deprecated, should be regenerated

Hierarchy symbols:
  ├── - Child entity (more siblings follow)
  └── - Last child entity
  │   - Continuation of parent branch

═══════════════════════════════════════════════════════════
SUMMARY
═══════════════════════════════════════════════════════════

Total entities: 15
  - Acts: 2 (1 approved, 1 draft)
  - Chapters: 3 (2 approved, 1 draft)
  - Scenes: 10 (5 approved, 4 draft, 1 requires-revalidation)

Approval progress:
  - Act 1: 100% chapters approved, 75% scenes approved
  - Act 2: 0% chapters approved, 0% scenes approved

Next actions:
  - Revalidate scene-0103 (parent changed)
  - Approve chapter-03 and its scenes
  - Approve act-2 and its descendants
```

### Step 5: Highlight issues (if any)

If entities need attention, show warnings:

```
⚠️  ATTENTION NEEDED

Requires revalidation:
  - scene-0103 (chapter-01)
    Reason: parent_chapter_modified
    Invalidated: 2 hours ago
    Action: /revalidate-scene 0103

Invalid entities:
  - scene-0403 (chapter-04)
    Should be regenerated or removed
    Action: /plan-scene 0403 (regenerate)

Draft entities blocking children:
  - act-2 (blocks chapter-04 approval)
    Action: /approve-plan act 2
```

---

## Display Modes

### Compact Mode (without status)

```
act-1
├── chapter-01
│   ├── scene-0101
│   ├── scene-0102
│   └── scene-0103
├── chapter-02
│   ├── scene-0201
│   └── scene-0202
└── chapter-03
    ├── scene-0301
    └── scene-0302
```

### Detailed Mode (with status - default)

Includes status indicators and icons (shown in Step 4 above).

### Single Act Mode

When `act_id` specified:

```
📊 HIERARCHY: act-1

act-1 [approved]
├── chapter-01 [approved]
│   ├── scene-0101 [approved]
│   ├── scene-0102 [approved]
│   └── scene-0103 [requires-revalidation] ⚠️
├── chapter-02 [approved]
│   ├── scene-0201 [approved]
│   └── scene-0202 [draft] 📝
└── chapter-03 [draft] 📝
    ├── scene-0301 [draft] 📝
    └── scene-0302 [draft] 📝

Summary for act-1:
  - Chapters: 3 (2 approved, 1 draft)
  - Scenes: 8 (5 approved, 2 draft, 1 requires-revalidation)

Approval progress: 66% chapters, 62% scenes
```

---

## Error Handling

### No entities found

```
ℹ️  No planning entities found

The planning state database is empty.

Possible reasons:
  1. No planning files created yet
  2. State database not initialized
  3. State out of sync with files

Actions:
  - Create planning files: /plan-act 1
  - Rebuild state from files: /rebuild-state
  - Check database: workspace/planning-state.db
```

### Act not found

```
❌ ERROR: Act not found

Act: act-3

No entity found with ID 'act-3' in planning state.

Available acts:
  - act-1 (approved, 3 chapters)
  - act-2 (draft, 1 chapter)

Usage: /show-hierarchy <act_id>
Example: /show-hierarchy act-1
```

### MCP unavailable

```
❌ ERROR: Planning state system unavailable

The MCP planning state module is not available.

This command requires:
  - MCP server running
  - planning_state_utils.py available
  - SQLite database initialized

Action required:
  1. Verify MCP server status
  2. Run /rebuild-state if database missing
  3. Check MCP server logs
```

---

## Use Cases

### Workflow Planning

Before starting work, check structure:

```bash
/show-hierarchy act-1
# See which scenes need approval
# Plan which scenes to generate next
```

### Progress Tracking

Monitor approval progress across acts:

```bash
/show-hierarchy
# View all acts with approval percentages
# Identify bottlenecks (unapproved parents blocking children)
```

### Post-Regeneration Check

After regenerating a chapter, check affected scenes:

```bash
# Regenerate chapter
/plan-chapter 2  # choose "regenerate"

# Check hierarchy
/show-hierarchy act-1
# See which scenes marked requires-revalidation

# Batch revalidate
/revalidate-all --chapter 02
```

### Migration Verification

After rebuilding state from files:

```bash
/rebuild-state
/show-hierarchy
# Verify all entities detected correctly
# Check hierarchy structure matches expectations
```

---

## Advanced Features

### Filtering by Status

To find all entities with specific status:

```bash
# Show hierarchy
/show-hierarchy act-1

# Look for status indicators in output:
# - ⚠️  = requires-revalidation
# - 📝 = draft
# - ✓ = approved
# - ❌ = invalid
```

### Approval Path Visualization

Shows which entities must be approved before others:

```
Approval path to generate scene-0301:
  1. Approve act-1 ✓ (already approved)
  2. Approve chapter-03 ✗ (draft)
  3. Approve scene-0301 ✗ (draft)

Cannot generate scene-0301 until chapter-03 is approved.
```

### Diff Between Acts

Compare structure of different acts:

```bash
/show-hierarchy act-1 --no-status
/show-hierarchy act-2 --no-status

# Visual comparison of structure
```

---

## Notes

- **Read-only**: Does not modify any state
- **Real-time**: Shows current state from database
- **Color-coded**: Uses status indicators for quick scanning (if terminal supports)
- **Hierarchical sorting**: Entities sorted naturally (chapter-2 before chapter-10)
- **Performance**: Fast even for large projects (database query)

---

## Related Commands

- `/rebuild-state` - Rebuild state before showing hierarchy
- `get_hierarchy_tree()` - Underlying MCP tool
- `get_entity_state()` - Check individual entity details
- `/revalidate-all` - Batch revalidate scenes shown in tree
- `/approve-plan` - Approve entities shown in tree

---

## Output Format

**Box Drawing Characters**:
- `├──` - Branch with more siblings
- `└──` - Last branch (no more siblings)
- `│   ` - Vertical continuation
- `    ` - Empty space (after last branch)

**Status Indicators**:
- `✓` - Approved (green if color supported)
- `📝` - Draft (yellow if color supported)
- `⚠️` - Requires revalidation (yellow if color supported)
- `❌` - Invalid (red if color supported)

**Sections**:
- Header: Command title and scope
- Tree: Visual hierarchy
- Legend: Status and symbol meanings
- Summary: Statistics and progress
- Attention: Issues requiring action (if any)

---

## Technical Details

**Data Source**: SQLite planning_entities table
**Query**: Recursive CTE for hierarchy traversal
**Sorting**: Natural numeric sorting (chapter-2 before chapter-10)
**Performance**: O(n) where n = number of entities
**Memory**: Loads entire hierarchy tree into memory (negligible for typical sizes)

**MCP Tool**: `get_hierarchy_tree(act_id, include_status=True)`
