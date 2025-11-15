# FEAT-0003 Hierarchical Planning - Testing Checklist

**Feature**: Hierarchical Planning Architecture
**Status**: Awaiting Manual Testing
**Last Updated**: 2025-11-15

---

## Testing Overview

This document provides comprehensive manual testing procedures for FEAT-0003. All automated unit tests (16 tests) are passing. Manual testing is required to validate end-to-end workflows, hook interactions, and user experience.

**Testing Approach**:
- ✅ Unit tests: Automated (COMPLETE)
- ⚠️ Integration tests: Manual (THIS DOCUMENT)
- ⚠️ User acceptance: Manual (USER RESPONSIBILITY)

**Estimated Testing Time**: 2-3 hours for complete checklist

---

## Test Environment Setup

### Prerequisites

```bash
# 1. Verify you're on the feature branch
git branch --show-current
# Expected: claude/hierarchical-planning-architecture-011CV2dxWLGHBcHAkdYMKNFH

# 2. Verify all files are committed
git status
# Expected: working tree clean

# 3. Backup current workspace
cp -r workspace workspace.backup-before-testing

# 4. Clear any existing state (fresh start)
rm -f workspace/planning-state.db
rm -rf workspace/planning-state/

# 5. Start MCP server (if not running)
# Check Claude Code MCP server status
```

### Test Data Preparation

Create test directory structure:
```bash
mkdir -p acts/act-test/chapters/chapter-test/{scenes,content}
```

---

## Test Suite 1: Core MCP Tools (30 min)

### 1.1 Entity State Management

**Test**: Create and retrieve entity state

```bash
# Step 1: Create act state
# Use MCP tool: update_entity_state
update_entity_state(
    entity_type='act',
    entity_id='act-test',
    status='draft',
    file_path='acts/act-test/strategic-plan.md',
    version_hash='test_hash_001',
    parent_id=None,
    parent_version_hash=None
)
```

**Expected**:
- ✅ Returns success message
- ✅ Creates entry in `workspace/planning-state.db`
- ✅ Creates JSON fallback in `workspace/planning-state/act-test.json`

```bash
# Step 2: Retrieve state
get_entity_state(entity_type='act', entity_id='act-test')
```

**Expected**:
- ✅ Returns all fields correctly
- ✅ Status is 'draft'
- ✅ All hashes match

**Pass/Fail**: [ ]

---

### 1.2 Hierarchy Tree

**Test**: Display hierarchy tree

```bash
# Step 1: Create act, chapter, scene states
update_entity_state(entity_type='act', entity_id='act-test', ...)
update_entity_state(entity_type='chapter', entity_id='chapter-test',
                    parent_id='act-test', ...)
update_entity_state(entity_type='scene', entity_id='scene-test01',
                    parent_id='chapter-test', ...)

# Step 2: Get hierarchy
get_hierarchy_tree(entity_type='act', entity_id='act-test')
```

**Expected**:
- ✅ Returns tree structure with act → chapter → scene
- ✅ All statuses displayed
- ✅ Indentation correct
- ✅ Parent-child relationships accurate

**Pass/Fail**: [ ]

---

### 1.3 Approval Workflow

**Test**: Approve entity with parent validation

```bash
# Step 1: Try to approve chapter without approved parent (should fail)
approve_entity(entity_type='chapter', entity_id='chapter-test', force=False)
```

**Expected**:
- ❌ Returns error: "Parent act-test is not approved"

```bash
# Step 2: Approve parent first
approve_entity(entity_type='act', entity_id='act-test')

# Step 3: Approve chapter (should succeed)
approve_entity(entity_type='chapter', entity_id='chapter-test')
```

**Expected**:
- ✅ Act approval succeeds
- ✅ Chapter approval succeeds
- ✅ Status changes from 'draft' to 'approved'

**Pass/Fail**: [ ]

---

### 1.4 Cascade Invalidation

**Test**: Cascading status changes on parent modification

```bash
# Step 1: Set up approved hierarchy
approve_entity(entity_type='act', entity_id='act-test')
approve_entity(entity_type='chapter', entity_id='chapter-test')
approve_entity(entity_type='scene', entity_id='scene-test01')

# Step 2: Get current states
get_entity_state(entity_type='chapter', entity_id='chapter-test')
get_entity_state(entity_type='scene', entity_id='scene-test01')
# Both should be 'approved'

# Step 3: Trigger cascade (simulate parent version change)
cascade_invalidate(
    entity_type='act',
    entity_id='act-test',
    new_version_hash='test_hash_002',
    reason='Act plan revised for testing'
)

# Step 4: Check descendant statuses
get_entity_state(entity_type='chapter', entity_id='chapter-test')
get_entity_state(entity_type='scene', entity_id='scene-test01')
```

**Expected**:
- ✅ Chapter status changed to 'requires-revalidation'
- ✅ Scene status changed to 'requires-revalidation'
- ✅ invalidation_reason set to "Parent act-test version changed"
- ✅ invalidated_at timestamp set

**Pass/Fail**: [ ]

---

### 1.5 Children Status Summary

**Test**: Get summary of children statuses

```bash
# Using hierarchy from previous test
get_children_status(entity_type='act', entity_id='act-test')
```

**Expected**:
- ✅ Shows chapter count: 1
- ✅ Shows chapter-test with 'requires-revalidation' status
- ✅ Scene count: 1 (nested under chapter)

**Pass/Fail**: [ ]

---

## Test Suite 2: Backup System (25 min)

### 2.1 Create Backup

**Test**: Manual backup creation

```bash
# Step 1: Create test planning file
echo "# Act Test Plan\nThis is a test." > acts/act-test/strategic-plan.md

# Step 2: Create backup
create_backup(
    entity_type='act',
    entity_id='act-test',
    file_path='acts/act-test/strategic-plan.md',
    reason='manual'
)
```

**Expected**:
- ✅ Creates timestamped backup file (e.g., `strategic-plan-2025-11-15-14-30-45.md`)
- ✅ Logs backup in SQLite `planning_entity_backups` table
- ✅ Returns backup_id

**Pass/Fail**: [ ]

---

### 2.2 List Backups

**Test**: View backup history

```bash
# Step 1: Create multiple backups
create_backup(entity_type='act', entity_id='act-test', ...)  # backup 1
# Modify file
create_backup(entity_type='act', entity_id='act-test', ...)  # backup 2

# Step 2: List backups
list_backups(entity_type='act', entity_id='act-test')
```

**Expected**:
- ✅ Shows 2 backups
- ✅ Most recent first
- ✅ Shows backup_id, timestamp, reason, version_hash
- ✅ File existence indicated

**Pass/Fail**: [ ]

---

### 2.3 Restore Backup

**Test**: Restore previous version

```bash
# Step 1: Get backup list
backups = list_backups(entity_type='act', entity_id='act-test')
backup_id = backups[1]['backup_id']  # older backup

# Step 2: Restore
restore_backup(
    entity_type='act',
    entity_id='act-test',
    backup_id=backup_id,
    file_path='acts/act-test/strategic-plan.md'
)
```

**Expected**:
- ✅ Creates safety backup of current version (reason='restore')
- ✅ Restores old version content to file
- ✅ Returns success message
- ✅ File content matches old backup

**Verification**:
```bash
cat acts/act-test/strategic-plan.md
# Should match old backup content
```

**Pass/Fail**: [ ]

---

### 2.4 Backup Diff

**Test**: Compare two backup versions

```bash
# Step 1: Get backup list
backups = list_backups(entity_type='act', entity_id='act-test')
backup_id_1 = backups[0]['backup_id']
backup_id_2 = backups[1]['backup_id']

# Step 2: Get diff
get_backup_diff(backup_id_1=backup_id_1, backup_id_2=backup_id_2)
```

**Expected**:
- ✅ Returns unified diff format
- ✅ Shows additions (+) and deletions (-)
- ✅ Includes metadata (timestamps, version hashes)
- ✅ Readable output

**Pass/Fail**: [ ]

---

## Test Suite 3: Hooks (40 min)

### 3.1 Hierarchy Validation Hook (PreToolUse)

**Test**: Blocks planning without approved parent

```bash
# Step 1: Set up act (NOT approved)
update_entity_state(entity_type='act', entity_id='act-2', status='draft', ...)

# Step 2: Try to create chapter plan
# Use Write tool to create file
Write(file_path='acts/act-2/chapters/chapter-01/plan.md', content='# Chapter Plan')
```

**Expected**:
- ❌ Hook blocks operation
- ❌ Error message: "Cannot plan chapter-01 because parent act-2 is not approved"
- ❌ File NOT created

```bash
# Step 3: Approve parent
approve_entity(entity_type='act', entity_id='act-2')

# Step 4: Retry chapter plan creation
Write(file_path='acts/act-2/chapters/chapter-01/plan.md', content='# Chapter Plan')
```

**Expected**:
- ✅ Hook allows operation
- ✅ File created successfully

**Pass/Fail**: [ ]

---

### 3.2 State Sync Hook (PostToolUse)

**Test**: Auto-syncs file changes to MCP state

```bash
# Step 1: Create new scene blueprint (no MCP state exists yet)
Write(file_path='acts/act-2/chapters/chapter-01/scenes/scene-0201-blueprint.md',
      content='# Scene Blueprint\n\nTest content.')

# Step 2: Check if MCP state was auto-created
get_entity_state(entity_type='scene', entity_id='scene-0201')
```

**Expected**:
- ✅ MCP state created automatically
- ✅ entity_type = 'scene'
- ✅ entity_id = 'scene-0201'
- ✅ parent_id = 'chapter-01'
- ✅ status = 'draft' (default for new entities)
- ✅ version_hash calculated from file content
- ✅ file_path correct

```bash
# Step 3: Edit existing file
Edit(file_path='acts/act-2/chapters/chapter-01/scenes/scene-0201-blueprint.md',
     old_string='Test content.',
     new_string='Updated test content.')

# Step 4: Check if MCP state was updated
get_entity_state(entity_type='scene', entity_id='scene-0201')
```

**Expected**:
- ✅ version_hash changed (reflects new content)
- ✅ previous_version_hash set to old hash
- ✅ updated_at timestamp changed

**Pass/Fail**: [ ]

---

### 3.3 Consistency Check Hook (PostToolUse)

**Test**: Warns about parent version mismatches

```bash
# Step 1: Set up hierarchy with version mismatch
update_entity_state(entity_type='act', entity_id='act-3',
                    version_hash='hash_v1', ...)
update_entity_state(entity_type='chapter', entity_id='chapter-01',
                    parent_id='act-3',
                    parent_version_hash='hash_v_OLD_MISMATCH', ...)

# Step 2: Edit chapter plan (triggers hook)
Edit(file_path='acts/act-3/chapters/chapter-01/plan.md',
     old_string='old', new_string='new')
```

**Expected**:
- ⚠️ Warning displayed:
  "Warning: chapter-01 parent_version_hash doesn't match parent act-3 current version"
- ⚠️ Suggestion: "Consider revalidating this chapter"
- ✅ Operation allowed to proceed (non-blocking)

**Pass/Fail**: [ ]

---

### 3.4 Invalidation Cascade Hook (PostToolUse)

**Test**: Auto-cascades on parent version change

```bash
# Step 1: Set up approved hierarchy
approve_entity(entity_type='act', entity_id='act-4')
approve_entity(entity_type='chapter', entity_id='chapter-01')
approve_entity(entity_type='scene', entity_id='scene-0401')

# Step 2: Edit act plan (parent of chapter)
Edit(file_path='acts/act-4/strategic-plan.md',
     old_string='old content', new_string='new content')

# Step 3: Check descendant statuses
get_entity_state(entity_type='chapter', entity_id='chapter-01')
get_entity_state(entity_type='scene', entity_id='scene-0401')
```

**Expected**:
- ✅ Act version_hash updated (from file hash)
- ✅ Chapter status changed to 'requires-revalidation'
- ✅ Scene status changed to 'requires-revalidation'
- ✅ Both have invalidation_reason and invalidated_at set
- ✅ Cascade happens automatically (no manual trigger needed)

**Pass/Fail**: [ ]

---

## Test Suite 4: Slash Commands (50 min)

### 4.1 /plan-act

**Test**: Plan top-level act

```bash
# Execute command
/plan-act 5
```

**Expected**:
- ✅ Launches planning-coordinator agent
- ✅ Prompts for act 5 strategic plan
- ✅ Creates `acts/act-5/strategic-plan.md`
- ✅ MCP state auto-created via state_sync_hook
- ✅ Status = 'draft'
- ✅ No parent validation (acts are root level)

**Pass/Fail**: [ ]

---

### 4.2 /plan-chapter

**Test**: Plan chapter with parent validation

```bash
# Step 1: Try without approved parent (should be blocked)
/plan-chapter 1 --act 6
```

**Expected**:
- ❌ Error: "Cannot plan chapter because parent act-6 is not approved"
- ❌ Operation blocked by hierarchy_validation_hook

```bash
# Step 2: Approve parent and retry
approve_entity(entity_type='act', entity_id='act-6')
/plan-chapter 1 --act 6
```

**Expected**:
- ✅ Command proceeds
- ✅ Launches planning-coordinator with parent context injected
- ✅ Creates `acts/act-6/chapters/chapter-01/plan.md`
- ✅ MCP state created with parent_id='act-6'

**Pass/Fail**: [ ]

---

### 4.3 /plan-scene

**Test**: Plan scene blueprint with chapter validation

```bash
# Step 1: Try without approved chapter (should be blocked)
/plan-scene 0701 --chapter 1 --act 7
```

**Expected**:
- ❌ Error: "Cannot plan scene because parent chapter-01 is not approved"

```bash
# Step 2: Approve parent chain and retry
approve_entity(entity_type='act', entity_id='act-7')
approve_entity(entity_type='chapter', entity_id='chapter-01')
/plan-scene 0701 --chapter 1 --act 7
```

**Expected**:
- ✅ Command proceeds
- ✅ Chapter plan content injected as context
- ✅ Creates `acts/act-7/chapters/chapter-01/scenes/scene-0701-blueprint.md`
- ✅ Blueprint is 400-800 words (detailed)
- ✅ MCP state created with parent_id='chapter-01'

**Pass/Fail**: [ ]

---

### 4.4 /approve-plan

**Test**: Approve entities with validation

```bash
# Step 1: Approve act
/approve-plan act-8
```

**Expected**:
- ✅ Status changed to 'approved'
- ✅ Success message displayed

```bash
# Step 2: Try to approve chapter without approved parent
/approve-plan chapter-02 --act 8
```

**Expected**:
- ❌ Error: "Parent must be approved first"
- ❌ Suggests using --force to override

```bash
# Step 3: Approve with force flag
/approve-plan chapter-02 --act 8 --force
```

**Expected**:
- ⚠️ Warning: "Forcing approval without parent validation"
- ✅ Status changed to 'approved'

**Pass/Fail**: [ ]

---

### 4.5 /revalidate-scene

**Test**: Interactive scene revalidation

```bash
# Step 1: Set up scene requiring revalidation
approve_entity(entity_type='scene', entity_id='scene-0801')
# Trigger invalidation by changing parent
Edit(file_path='acts/act-8/chapters/chapter-01/plan.md', ...)

# Step 2: Run revalidation command
/revalidate-scene 0801 --chapter 1 --act 8
```

**Expected**:
- ✅ Shows invalidation reason ("Parent chapter-01 version changed")
- ✅ Shows invalidation timestamp
- ✅ Performs alignment analysis (scene vs chapter)
- ✅ Presents 5 options:
  1. Keep & approve
  2. Edit blueprint
  3. Regenerate (with backup)
  4. View files
  5. Abort
- ✅ Option 1: Updates status to 'approved'
- ✅ Option 3: Creates backup before regenerating

**Pass/Fail**: [ ]

---

### 4.6 /revalidate-all

**Test**: Batch revalidation

```bash
# Step 1: Set up multiple scenes requiring revalidation
# (cascade from parent change)
Edit(file_path='acts/act-9/strategic-plan.md', ...)
# This should cascade to all act-9 scenes

# Step 2: Run batch revalidation
/revalidate-all --act 9
```

**Expected**:
- ✅ Shows all scenes requiring revalidation
- ✅ Priority calculation displayed (HIGH/MEDIUM/LOW)
- ✅ Presents 6 operation modes
- ✅ Mode 2 (Bulk approve low priority): Approves only LOW priority scenes
- ✅ Mode 3 (Bulk approve all): Requires strong confirmation
- ✅ Mode 4 (Export report): Creates CSV/JSON report

**Pass/Fail**: [ ]

---

### 4.7 /list-versions

**Test**: View backup history

```bash
# Step 1: Create backups for entity
create_backup(entity_type='chapter', entity_id='chapter-10', ...)
create_backup(entity_type='chapter', entity_id='chapter-10', ...)

# Step 2: List versions
/list-versions chapter chapter-10 --act 10
```

**Expected**:
- ✅ Shows all backups in reverse chronological order
- ✅ Displays backup_id, timestamp, reason, version_hash
- ✅ Indicates file existence status
- ✅ Formatted table output

**Pass/Fail**: [ ]

---

### 4.8 /restore-version

**Test**: Restore backup safely

```bash
# Step 1: Get backup ID from /list-versions
/list-versions chapter chapter-11
# Note backup_id from output

# Step 2: Restore
/restore-version chapter chapter-11 <backup_id>
```

**Expected**:
- ⚠️ Shows confirmation prompt with:
  - Current version hash
  - Backup version hash
  - Warning about cascade (if entity has children)
- ✅ Creates safety backup of current version
- ✅ Restores backup content to file
- ✅ Updates MCP state (version_hash, status)
- ✅ Success message with file path

**Pass/Fail**: [ ]

---

### 4.9 /diff-version

**Test**: Compare backup versions

```bash
# Step 1: Get two backup IDs
/list-versions scene scene-1201
# Note two backup_ids

# Step 2: Compare
/diff-version <backup_id_1> <backup_id_2>
```

**Expected**:
- ✅ Shows metadata for both backups
- ✅ Unified diff format
- ✅ Legend explaining +/- symbols
- ✅ Readable comparison

**Pass/Fail**: [ ]

---

### 4.10 /rebuild-state

**Test**: Reconstruct state from files

```bash
# Step 1: Corrupt database (simulate)
rm workspace/planning-state.db

# Step 2: Dry-run preview
/rebuild-state --dry-run
```

**Expected**:
- ✅ Scans `acts/` directory
- ✅ Shows preview of entities to be created
- ✅ No database modifications

```bash
# Step 3: Execute rebuild
/rebuild-state
```

**Expected**:
- ✅ Creates new database
- ✅ Populates with all entities from files
- ✅ Calculates version hashes from current files
- ✅ Sets status='draft' for all (or preserves from JSON fallback)
- ✅ Success summary displayed

**Verification**:
```bash
get_hierarchy_tree(entity_type='act', entity_id='act-1')
# Should show full hierarchy
```

**Pass/Fail**: [ ]

---

### 4.11 /show-hierarchy

**Test**: Visual tree display

```bash
# Step 1: Display full hierarchy
/show-hierarchy
```

**Expected**:
- ✅ Box-drawing tree structure
- ✅ All acts, chapters, scenes displayed
- ✅ Status indicators: ✓ (approved), 📝 (draft), ⚠️ (requires-revalidation), ❌ (invalid)
- ✅ Indentation shows hierarchy levels

```bash
# Step 2: Filter by act
/show-hierarchy --act 1
```

**Expected**:
- ✅ Shows only act-1 and its descendants
- ✅ Progress summary at bottom

**Pass/Fail**: [ ]

---

## Test Suite 5: Emergency Recovery (30 min)

### 5.1 Database Corruption Recovery

**Test**: Recover from corrupted database

```bash
# Step 1: Simulate corruption
echo "corrupt data" > workspace/planning-state.db

# Step 2: Attempt normal operation (should fail gracefully)
get_entity_state(entity_type='act', entity_id='act-1')
```

**Expected**:
- ⚠️ Error message indicating database corruption
- ✅ JSON fallback engaged (if exists)

```bash
# Step 3: Follow recovery procedure from emergency-recovery.md
/rebuild-state
```

**Expected**:
- ✅ New database created
- ✅ State reconstructed from files
- ✅ Normal operations resume

**Pass/Fail**: [ ]

---

### 5.2 MCP Server Crash Recovery

**Test**: Restart MCP server

```bash
# Step 1: Kill MCP server process (simulate crash)
# (mechanism depends on MCP server setup)

# Step 2: Restart server
# (follow restart procedure)

# Step 3: Verify state persistence
get_entity_state(entity_type='act', entity_id='act-1')
```

**Expected**:
- ✅ State loads from SQLite database
- ✅ All data intact
- ✅ Operations resume normally

**Pass/Fail**: [ ]

---

### 5.3 Hook Blocking Override

**Test**: Temporarily disable hook

```bash
# Step 1: Hook blocks operation (e.g., hierarchy validation)
# Try to plan chapter without approved parent
/plan-chapter 5 --act 15

# Step 2: Temporarily disable hook
# Edit .claude/hooks.json - comment out hierarchy_validation_hook

# Step 3: Retry operation
/plan-chapter 5 --act 15
```

**Expected**:
- ✅ Operation proceeds (hook bypassed)
- ✅ File created

```bash
# Step 4: Re-enable hook
# Restore .claude/hooks.json
```

**Expected**:
- ✅ Hook active again for future operations

**Pass/Fail**: [ ]

---

### 5.4 Lost Planning State Recovery

**Test**: Recover state from Git

```bash
# Step 1: Delete entire workspace/planning-state/
rm -rf workspace/planning-state/
rm workspace/planning-state.db

# Step 2: Check Git for backups
git log --all --full-history -- "workspace/planning-state/*"

# Step 3: Restore from Git (if available) or rebuild
/rebuild-state
```

**Expected**:
- ✅ State reconstructed from files
- ✅ Operations resume

**Pass/Fail**: [ ]

---

## Test Suite 6: Integration Testing (45 min)

### 6.1 End-to-End: Plan Entire Act

**Test**: Complete workflow from act to scene

```bash
# Step 1: Plan act
/plan-act 20

# Step 2: Approve act
/approve-plan act-20

# Step 3: Plan chapter
/plan-chapter 1 --act 20

# Step 4: Approve chapter
/approve-plan chapter-01 --act 20

# Step 5: Plan scene
/plan-scene 2001 --chapter 1 --act 20

# Step 6: Approve scene
/approve-plan scene-2001 --chapter 1 --act 20

# Step 7: View hierarchy
/show-hierarchy --act 20
```

**Expected**:
- ✅ All entities created
- ✅ All approvals succeed
- ✅ Hierarchy displays correctly with ✓ indicators
- ✅ Parent-child relationships intact

**Pass/Fail**: [ ]

---

### 6.2 Cascade Invalidation Flow

**Test**: Full cascade from act change to scene

```bash
# Step 1: Use approved hierarchy from previous test
# (act-20 → chapter-01 → scene-2001, all approved)

# Step 2: Edit act plan
Edit(file_path='acts/act-20/strategic-plan.md',
     old_string='...', new_string='...')

# Step 3: Check cascade
get_entity_state(entity_type='chapter', entity_id='chapter-01')
get_entity_state(entity_type='scene', entity_id='scene-2001')
```

**Expected**:
- ✅ Both descendants marked 'requires-revalidation'
- ✅ invalidation_reason set correctly
- ✅ invalidated_at timestamp set

```bash
# Step 4: Revalidate chapter
/revalidate-scene 2001 --chapter 1 --act 20
# Choose option: Keep & approve
```

**Expected**:
- ✅ Scene approved again
- ✅ Status = 'approved'

**Pass/Fail**: [ ]

---

### 6.3 Backup and Restore Flow

**Test**: Full version control cycle

```bash
# Step 1: Create initial chapter plan
/plan-chapter 2 --act 20

# Step 2: Approve
/approve-plan chapter-02 --act 20

# Step 3: Create manual backup
create_backup(entity_type='chapter', entity_id='chapter-02',
              file_path='acts/act-20/chapters/chapter-02/plan.md',
              reason='manual')

# Step 4: Edit chapter (v2)
Edit(file_path='acts/act-20/chapters/chapter-02/plan.md', ...)

# Step 5: Create another backup
create_backup(..., reason='manual')

# Step 6: View versions
/list-versions chapter chapter-02 --act 20

# Step 7: Compare versions
/diff-version <backup_id_1> <backup_id_2>

# Step 8: Restore to v1
/restore-version chapter chapter-02 <backup_id_1>
```

**Expected**:
- ✅ All backups created correctly
- ✅ Diff shows changes between versions
- ✅ Restore succeeds with safety backup
- ✅ File content matches v1

**Pass/Fail**: [ ]

---

### 6.4 Regeneration with Cascade

**Test**: Regenerate chapter and observe cascade

```bash
# Step 1: Set up approved hierarchy
# (act-20 → chapter-03 → scene-2003, all approved)

# Step 2: Regenerate chapter using /plan-chapter --regenerate
/plan-chapter 3 --act 20 --regenerate

# Expected prompts:
# - Confirmation to regenerate
# - Automatic backup creation
```

**Expected**:
- ✅ Backup created (reason='regeneration')
- ✅ New chapter plan generated
- ✅ Chapter status = 'draft' (requires re-approval)
- ✅ Scene-2003 status = 'requires-revalidation' (cascade)

```bash
# Step 3: Verify cascade
get_entity_state(entity_type='scene', entity_id='scene-2003')
```

**Expected**:
- ✅ Scene invalidated
- ✅ Reason: "Parent chapter-03 version changed"

**Pass/Fail**: [ ]

---

## Test Suite 7: Error Handling (20 min)

### 7.1 Missing Files

**Test**: Handle missing files gracefully

```bash
# Step 1: Create MCP state without file
update_entity_state(entity_type='act', entity_id='act-missing',
                    file_path='acts/act-missing/strategic-plan.md',
                    ...)

# Step 2: Try to create backup
create_backup(entity_type='act', entity_id='act-missing',
              file_path='acts/act-missing/strategic-plan.md',
              reason='manual')
```

**Expected**:
- ❌ Error: "File not found: acts/act-missing/strategic-plan.md"
- ❌ Backup not created

**Pass/Fail**: [ ]

---

### 7.2 Invalid Entity References

**Test**: Handle nonexistent entities

```bash
# Step 1: Get state for nonexistent entity
get_entity_state(entity_type='act', entity_id='act-nonexistent')
```

**Expected**:
- ❌ Error: "Entity not found"

```bash
# Step 2: Approve nonexistent entity
approve_entity(entity_type='chapter', entity_id='chapter-nonexistent')
```

**Expected**:
- ❌ Error: "Entity not found"

**Pass/Fail**: [ ]

---

### 7.3 Concurrent Modifications

**Test**: Handle file modified during operation

```bash
# Step 1: Start planning operation
/plan-chapter 10 --act 20
# (operation in progress)

# Step 2: Manually edit file during operation (simulate)
# Edit acts/act-20/chapters/chapter-10/plan.md externally

# Step 3: Operation completes
```

**Expected**:
- ⚠️ Potential version hash mismatch detected by consistency_check_hook
- ⚠️ Warning displayed
- ✅ Operation completes (non-blocking)

**Pass/Fail**: [ ]

---

## Test Suite 8: Performance (15 min)

### 8.1 Large Hierarchy

**Test**: Handle multiple acts with many scenes

```bash
# Step 1: Create large hierarchy
for act in {1..5}; do
    update_entity_state(entity_type='act', entity_id="act-$act", ...)
    for chapter in {1..10}; do
        chapter_id=$(printf "chapter-%02d" $chapter)
        update_entity_state(entity_type='chapter', entity_id="$chapter_id",
                           parent_id="act-$act", ...)
        for scene in {1..5}; do
            scene_num=$((act * 1000 + chapter * 10 + scene))
            scene_id=$(printf "scene-%04d" $scene_num)
            update_entity_state(entity_type='scene', entity_id="$scene_id",
                               parent_id="$chapter_id", ...)
        done
    done
done

# Total: 5 acts × 10 chapters × 5 scenes = 250 scenes + 50 chapters + 5 acts = 305 entities

# Step 2: Test hierarchy query performance
time get_hierarchy_tree(entity_type='act', entity_id='act-1')
```

**Expected**:
- ✅ Query completes in <2 seconds
- ✅ Correct tree structure returned

**Pass/Fail**: [ ]

---

### 8.2 Cascade Performance

**Test**: Cascade to many descendants

```bash
# Using large hierarchy from previous test

# Step 1: Cascade from act-1 (should invalidate 50 scenes + 10 chapters)
time cascade_invalidate(entity_type='act', entity_id='act-1',
                        new_version_hash='new_hash',
                        reason='Performance test')
```

**Expected**:
- ✅ Completes in <5 seconds
- ✅ All 60 descendants invalidated

**Pass/Fail**: [ ]

---

## Test Suite 9: Backward Compatibility (10 min)

### 9.1 /plan-story Routing

**Test**: Old command routes to new workflow

```bash
# Step 1: Call old /plan-story command
/plan-story
```

**Expected**:
- ✅ Explains hierarchical workflow
- ✅ Recommends /plan-act, /plan-chapter, /plan-scene
- ✅ Maintains backward compatibility
- ✅ No errors

**Pass/Fail**: [ ]

---

## Test Results Summary

### Overall Results

| Test Suite | Total Tests | Passed | Failed | Skipped | Pass Rate |
|------------|-------------|--------|--------|---------|-----------|
| 1. Core MCP Tools | 5 | [ ] | [ ] | [ ] | [ ]% |
| 2. Backup System | 4 | [ ] | [ ] | [ ] | [ ]% |
| 3. Hooks | 4 | [ ] | [ ] | [ ] | [ ]% |
| 4. Slash Commands | 11 | [ ] | [ ] | [ ] | [ ]% |
| 5. Emergency Recovery | 4 | [ ] | [ ] | [ ] | [ ]% |
| 6. Integration | 4 | [ ] | [ ] | [ ] | [ ]% |
| 7. Error Handling | 3 | [ ] | [ ] | [ ] | [ ]% |
| 8. Performance | 2 | [ ] | [ ] | [ ] | [ ]% |
| 9. Backward Compatibility | 1 | [ ] | [ ] | [ ] | [ ]% |
| **TOTAL** | **38** | [ ] | [ ] | [ ] | [ ]% |

### Acceptance Criteria

- [ ] All critical tests passed (Suites 1-4)
- [ ] No blocking errors in integration tests (Suite 6)
- [ ] Emergency recovery procedures verified (Suite 5)
- [ ] Performance acceptable for expected scale (Suite 8)
- [ ] Backward compatibility maintained (Suite 9)

### Sign-Off

**Tester**: _______________
**Date**: _______________
**Status**: [ ] APPROVED FOR MERGE  [ ] REQUIRES FIXES  [ ] NEEDS DISCUSSION

---

## Troubleshooting

### Common Issues

1. **MCP tools not available**: Ensure MCP server is running and generation_state_mcp.py is loaded
2. **Hooks not triggering**: Check `.claude/hooks.json` registration
3. **Database locked**: Close other connections, check for hanging transactions
4. **Version hash mismatches**: Verify file content hasn't changed unexpectedly

### Support Resources

- Emergency Recovery: `docs/emergency-recovery.md`
- Implementation Details: `features/FEAT-0003-hierarchical-planning/IMPLEMENTATION-COMPLETE.md`
- Technical Spec: `features/FEAT-0003-hierarchical-planning/technical-design.md`

---

**End of Testing Checklist**
