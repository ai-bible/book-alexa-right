# FEAT-0003: Hierarchical Planning Workflow (Act → Chapter → Scene)

**Status**: Requirements Defined
**Created**: 2025-11-11
**Author**: User + Claude
**Priority**: High

---

## Problem Statement

Currently, the system has a robust workflow for scene blueprint generation and a separate `/plan-story` command, but there's no unified hierarchical planning process that enforces the structure: **Act → Chapter → Scene**. Authors can skip levels, create plans without parent context, and there's no automated validation ensuring child plans align with parent plans. The MCP/hooks system that works well for scene generation doesn't extend to the full planning hierarchy.

**Pain Points**:
1. No standardized way to plan an entire act and cascade down to chapters
2. Chapter plans are created manually without enforcing that act plan exists
3. Scene blueprints can be created without chapter plan approval
4. Regenerating a parent plan doesn't invalidate dependent child plans
5. No automated state tracking for the planning hierarchy (manual JSON files)
6. Authors must manually ensure consistency across levels

---

## User Journey

### Starting Point: Planning a New Act

**Scenario 1: Author Wants to Plan Act 1 from Scratch**

1. **User starts**: Types `/plan-act 1`
2. **System checks hierarchy** (via MCP hook):
   - ✅ No dependencies at act level
   - Proceeds to interactive planning
3. **System asks questions** (same style as current `/plan-story`):
   - "Какова главная цель акта 1?" (What's the main goal of act 1?)
   - "Какие ключевые события должны произойти?" (Key events?)
   - "Какие персонажи будут задействованы?" (Characters involved?)
   - "Какие сюжетные линии начинаются/завершаются?" (Storylines?)
   - "Какой эмоциональный путь проходит читатель?" (Emotional arc?)
4. **System generates draft**: Shows `strategic-plan.md` draft for review
5. **User approves/iterates**: Can modify and request changes
6. **System saves**: Creates `acts/act-1/strategic-plan.md`
7. **System updates MCP state**:
   ```json
   {
     "entity_type": "act",
     "entity_id": "act-1",
     "status": "draft",
     "version_hash": "abc123...",
     "created_at": "2025-11-11T10:30:00Z",
     "children": []
   }
   ```
8. **System asks**: "Хотите ли начать планирование глав сейчас? (Y/n)" (Want to plan chapters now?)
   - **If Yes**: Starts interactive chapter planning loop
   - **If No**: Exits, user can plan chapters later

---

### Scenario 2: Author Wants to Plan Chapter 2

1. **User starts**: Types `/plan-chapter 2`
2. **System checks hierarchy** (via MCP + hook):
   - Checks if `acts/act-1/strategic-plan.md` exists
   - Checks MCP state: `act-1` status = `approved` or `draft`?
   - **If NOT approved**: ❌ **HARD BLOCK**
     ```
     ERROR: Cannot plan chapter 02

     Reason: Parent act plan not approved
     Current status: act-1 = "draft"

     Action required:
     1. Review act plan: acts/act-1/strategic-plan.md
     2. Run: /approve-plan act 1
     3. Then retry: /plan-chapter 2

     Hierarchy requirement: Act → Chapter → Scene
     ```
     **Process stops here** - user MUST approve act first
   - **If approved**: ✅ Proceeds
3. **System loads parent context**:
   - Reads `acts/act-1/strategic-plan.md`
   - Extracts relevant information for chapter 2 from act plan
   - Injects into Phase 1 context-analyzer
4. **System asks questions** (interactive dialogue):
   - "Что должно произойти в главе 2 согласно плану акта?" (What should happen per act plan?)
   - "Какие конфликты развиваются?" (Conflicts?)
   - "Какие персонажи участвуют?" (Characters?)
   - "Сколько примерно сцен вы планируете?" (How many scenes?)
5. **System generates draft**: Shows `plan.md` draft
6. **User approves/iterates**: Can modify
7. **System saves**: Creates `acts/act-1/chapters/chapter-02/plan.md`
8. **System updates MCP state**:
   ```json
   {
     "entity_type": "chapter",
     "entity_id": "chapter-02",
     "parent_id": "act-1",
     "parent_version_hash": "abc123...",
     "status": "draft",
     "version_hash": "def456...",
     "created_at": "2025-11-11T11:00:00Z",
     "children": []
   }
   ```
9. **Hook triggers**: `hierarchy_consistency_hook.py` validates chapter plan matches act plan
10. **System asks**: "Хотите ли начать создание blueprint'ов для сцен? (Y/n)"

---

### Scenario 3: Author Wants to Generate Scene Blueprint

1. **User starts**: Types `/plan-scene 0205` (or `/plan-story scene 0205`)
2. **System checks hierarchy** (via MCP + hook):
   - Checks if `acts/act-1/chapters/chapter-02/plan.md` exists
   - Checks MCP state: `chapter-02` status = `approved`?
   - **If NOT approved**: ❌ **HARD BLOCK**
     ```
     ERROR: Cannot plan scene 0205

     Reason: Parent chapter plan not approved
     Current status: chapter-02 = "draft"

     Action required:
     1. Review chapter plan: acts/act-1/chapters/chapter-02/plan.md
     2. Run: /approve-plan chapter 2
     3. Then retry: /plan-scene 0205

     Hierarchy: Act → Chapter → Scene
                        ↑ You are here
     ```
     **Process stops** - user MUST approve chapter first
   - **If approved**: ✅ Proceeds
3. **System loads parent context**:
   - Reads chapter plan
   - Extracts scene 5 context from chapter
4. **Continues with existing `/plan-story` flow**: (5 phases, works as before)
5. **Creates blueprint**: `acts/act-1/chapters/chapter-02/scenes/scene-0205-blueprint.md`
6. **Updates MCP state**: Links scene to chapter

---

### Scenario 4: Author Regenerates Chapter Plan (Invalidation Flow)

**Context**: Author already created chapter-02 plan and 5 scene blueprints. Now they realize chapter plan needs changes.

1. **User starts**: Types `/plan-chapter 2` (regenerate existing)
2. **System detects existing plan**:
   ```
   ⚠️ WARNING: Chapter 02 plan already exists

   Current status: approved
   Dependent scenes: 5 blueprints

   If you regenerate this chapter plan:
   - All 5 scene blueprints will be marked as "requires-revalidation"
   - You will need to manually review each scene blueprint
   - Already generated scenes (content/*.md) stay but need review

   Continue? (y/N)
   ```
3. **User confirms**: y
4. **System archives old version**:
   - Moves `plan.md` → `backups/plan-2025-11-11-11-30.md` (timestamped)
5. **System runs interactive planning**: (same flow as Scenario 2)
6. **System creates new plan**: Saves new `plan.md`
7. **System updates MCP state**:
   ```json
   {
     "entity_type": "chapter",
     "entity_id": "chapter-02",
     "status": "draft",
     "version_hash": "xyz789...",  // NEW hash
     "previous_version_hash": "def456...",
     "updated_at": "2025-11-11T12:00:00Z"
   }
   ```
8. **Hook triggers cascade invalidation** (`hierarchy_invalidation_hook.py`):
   - Scans all children: scene-0201 through scene-0205
   - Updates MCP state for each scene:
     ```json
     {
       "entity_id": "scene-0201",
       "status": "requires-revalidation",
       "invalidation_reason": "parent_chapter_regenerated",
       "parent_version_changed_from": "def456...",
       "parent_version_changed_to": "xyz789...",
       "invalidated_at": "2025-11-11T12:00:05Z"
     }
     ```
9. **System shows summary**:
   ```
   ✅ Chapter 02 plan regenerated

   📁 Old version: backups/plan-2025-11-11-11-30.md
   📄 New version: plan.md (status: draft)

   ⚠️ Invalidated child blueprints:
   - scene-0201-blueprint.md (requires-revalidation)
   - scene-0202-blueprint.md (requires-revalidation)
   - scene-0203-blueprint.md (requires-revalidation)
   - scene-0204-blueprint.md (requires-revalidation)
   - scene-0205-blueprint.md (requires-revalidation)

   Next steps:
   1. Review new chapter plan
   2. Run: /approve-plan chapter 2
   3. Manually review each scene blueprint:
      - Keep: /revalidate-scene 0201
      - Regenerate: /plan-scene 0201
   ```

---

### Scenario 5: Author Validates Invalidated Scene Blueprint

**Context**: Scene 0201 was marked "requires-revalidation" after chapter regeneration.

1. **User starts**: Types `/revalidate-scene 0201`
2. **System checks**: Reads blueprint file + new chapter plan
3. **System shows comparison**:
   ```
   📋 Scene 0201 Blueprint Review

   Parent plan changed:
   - Old chapter focus: "Алекса discovers lower city"
   - New chapter focus: "Алекса explores temporal district"

   Blueprint still valid?
   - Location: Lower City Level 47 ✅ (compatible)
   - Characters: Алекса, Рейн ✅ (still in chapter)
   - Main event: First encounter with time cascade ⚠️ (timing changed)

   Recommendation: Regenerate blueprint (event timing no longer matches)

   Actions:
   [1] Approve blueprint as-is (mark valid)
   [2] Regenerate blueprint (run /plan-scene 0201)
   [3] Cancel (keep requires-revalidation status)
   ```
4. **User chooses**:
   - **Option 1**: System marks scene as `approved` in MCP
   - **Option 2**: System starts `/plan-scene 0201` flow
   - **Option 3**: System exits, scene stays `requires-revalidation`

---

### Scenario 6: Author Tries to Generate Scene Content Without Approval

**Context**: Author regenerated chapter plan, scene blueprint now `requires-revalidation`, author tries to generate prose.

1. **User starts**: "Generate scene 0201"
2. **System detects** (generation-coordinator Step 1):
   - Blueprint exists: ✅
   - Blueprint status: `requires-revalidation`
3. **System blocks** (via MCP hook):
   ```
   ❌ ERROR: Cannot generate scene 0201

   Reason: Blueprint requires revalidation
   Status: requires-revalidation
   Cause: Parent chapter plan was regenerated on 2025-11-11 12:00

   Action required:
   1. Review blueprint: acts/.../scenes/scene-0201-blueprint.md
   2. Compare with new chapter plan
   3. Either:
      - Approve: /revalidate-scene 0201
      - Regenerate: /plan-scene 0201

   Cannot generate prose from invalidated blueprint.
   ```
   **Process stops** - no generation happens

---

## Edge Cases & Behaviors

### Edge Case 1: Orphan Scene Blueprint

**Scenario**: Blueprint exists but parent chapter plan is missing

**System behavior**:
- Hook detects missing parent on any operation
- Shows error with file path
- Blocks operations until resolved
- Suggests creating chapter plan first

### Edge Case 2: Partial Hierarchy

**Scenario**: Chapter plan exists but act plan missing

**System behavior**:
- Allows chapter planning (soft warning)
- Warning: "Act plan not found. Recommendation: create acts/act-1/strategic-plan.md"
- Continues but logs warning in MCP state

### Edge Case 3: Multiple Versions in Backups

**Scenario**: User wants to restore old version

**System behavior**:
- `/list-versions chapter 2` shows all backups with timestamps
- `/restore-version chapter 2 2025-11-10-14-30` restores from backup
- Triggers cascade invalidation of children (same as regeneration)

### Edge Case 4: Concurrent Modifications

**Scenario**: Two planning sessions modify same plan

**System behavior**:
- Session isolation via hooks prevents this
- Error if no session active
- Session lock prevents concurrent writes

### Edge Case 5: Batch Revalidation

**Scenario**: Author regenerated chapter, has 20 invalidated scenes

**System behavior**:
- `/revalidate-all chapter 2` runs validation on all children
- Shows summary report with recommendations
- User can batch-approve compatible scenes

---

## Definition of Done (DoD)

### Must Have ✅

**Hierarchical Planning Commands**:
- [ ] `/plan-act <N>` command works with interactive dialogue
- [ ] `/plan-chapter <N>` command works with interactive dialogue
- [ ] `/plan-scene <NNNN>` command works (extends existing `/plan-story`)
- [ ] All three commands use consistent interaction pattern (like current `/plan-story`)

**MCP State Tracking**:
- [ ] MCP server tracks state for acts, chapters, scenes
- [ ] State includes: status (draft/approved/requires-revalidation/invalid), version hash, parent links, timestamps
- [ ] MCP exposes tools: `get_entity_state()`, `update_entity_state()`, `get_hierarchy_tree()`
- [ ] MCP exposes resources: `state://planning/{entity_type}/{entity_id}`

**Hooks System**:
- [ ] `hierarchy_validation_hook.py` (PreToolUse) - Blocks child creation if parent not approved
- [ ] `hierarchy_consistency_hook.py` (PostToolUse) - Validates child matches parent constraints
- [ ] `hierarchy_invalidation_hook.py` (PostToolUse) - Cascades invalidation to children on parent change
- [ ] `state_sync_hook.py` (PostToolUse) - Syncs file changes to MCP state
- [ ] All hooks log to `workspace/logs/hooks/`

**Validation & Enforcement**:
- [ ] **HARD BLOCK**: Cannot plan chapter if act not approved
- [ ] **HARD BLOCK**: Cannot plan scene if chapter not approved
- [ ] **HARD BLOCK**: Cannot generate scene if blueprint `requires-revalidation`
- [ ] Cascade invalidation works: parent regeneration → children marked `requires-revalidation`

**File Management**:
- [ ] Old versions moved to `backups/` subdirectories with timestamps
- [ ] Only ONE canonical file exists (no `-v2`, `-revised` suffixes)
- [ ] Backup naming: `{filename}-{YYYY-MM-DD-HH-MM}.md`

**Agent Integration**:
- [ ] Agents receive parent context automatically (act plan → chapter planning, chapter plan → scene planning)
- [ ] Agents do NOT write state files directly (only via MCP)
- [ ] Agents remain focused on creative work (planning content, generating ideas)

### Should Have 🎯

**User Experience**:
- [ ] `/approve-plan <type> <id>` command to change status: draft → approved
- [ ] `/revalidate-scene <NNNN>` command to manually review invalidated scenes
- [ ] `/revalidate-all <chapter-id>` batch validation command
- [ ] Visual hierarchy tree display: `/show-hierarchy act 1`
- [ ] Progress indicators during multi-step planning

**Version Management**:
- [ ] `/list-versions <type> <id>` shows backup history
- [ ] `/restore-version <type> <id> <timestamp>` restores from backup
- [ ] Diff view between current and backup versions

**Recovery & Resume**:
- [ ] Planning state persists across sessions
- [ ] Can resume interrupted planning workflow
- [ ] Graceful degradation if MCP server unavailable (fallback to manual state)

### Nice to Have 🌟

**Analytics & Insights**:
- [ ] `/planning-stats act 1` shows completion percentage
- [ ] Visualization of which scenes need revalidation
- [ ] Timeline view of planning history

**Smart Suggestions**:
- [ ] System suggests number of scenes based on chapter scope
- [ ] Auto-detects inconsistencies between levels
- [ ] Recommends when to split/merge scenes

**Batch Operations**:
- [ ] `/plan-all-chapters act 1` creates all chapter plans in sequence
- [ ] `/approve-all-scenes chapter 2` batch approval for compatible scenes

---

## Visual Description

### Before: Disconnected Planning

```
User: /plan-story    User: /plan-story    User: "Generate scene"
      ↓                    ↓                      ↓
   [Agent works]        [Agent works]         [Agent works]
      ↓                    ↓                      ↓
   Some file           Some file              Some file

   ❌ No structure
   ❌ No validation
   ❌ No parent context
   ❌ No invalidation tracking
```

### After: Hierarchical Planning

```
User: /plan-act 1
      ↓
   [Hook: Check hierarchy] ✅ Act has no parent, proceed
      ↓
   [MCP: Get state] → No existing act plan
      ↓
   [Agent: Interactive planning] → Questions + Draft
      ↓
   [User: Approves]
      ↓
   [File: strategic-plan.md created]
      ↓
   [Hook: Update MCP state] → act-1 = "draft"
      ↓
   [User: /approve-plan act 1]
      ↓
   [MCP: Update state] → act-1 = "approved"

   ─────────────────────────────────────

User: /plan-chapter 2
      ↓
   [Hook: Check hierarchy] → Is parent (act-1) approved?
      ├─ ❌ No → BLOCK with error message
      └─ ✅ Yes → Proceed
      ↓
   [MCP: Get parent context] → Load act-1 plan
      ↓
   [Agent: Interactive planning] → Inject parent context, ask questions
      ↓
   [File: chapter-02/plan.md created]
      ↓
   [Hook: Consistency check] → Validate against act plan
      ↓
   [Hook: Update MCP state] → chapter-02 = "draft", parent = act-1

   ─────────────────────────────────────

User: /plan-scene 0205
      ↓
   [Hook: Check hierarchy] → Is parent (chapter-02) approved?
      ├─ ❌ No → BLOCK
      └─ ✅ Yes → Proceed
      ↓
   [MCP: Get parent context] → Load chapter-02 plan
      ↓
   [Agent: Existing /plan-story flow]
      ↓
   [File: scene-0205-blueprint.md created]
      ↓
   [Hook: Update MCP state] → scene-0205 = "draft", parent = chapter-02

   ─────────────────────────────────────

User: /plan-chapter 2  (REGENERATE)
      ↓
   [System: Detect existing] → Warning + Confirm?
      ↓
   [User: Confirms]
      ↓
   [File: Move plan.md → backups/plan-2025-11-11.md]
      ↓
   [Agent: New planning flow]
      ↓
   [File: New plan.md created]
      ↓
   [Hook: Cascade invalidation]
      ├─ scene-0201 → "requires-revalidation"
      ├─ scene-0202 → "requires-revalidation"
      ├─ scene-0203 → "requires-revalidation"
      ├─ scene-0204 → "requires-revalidation"
      └─ scene-0205 → "requires-revalidation"
      ↓
   [MCP: Update all states] → Log invalidation reasons
      ↓
   [System: Show summary] → List invalidated children + next steps
```

---

## Open Questions

### For Technical Design (agent-architect to resolve):

1. **MCP Server Architecture**:
   - Should we extend existing `generation-state-tracker` spec or create new `planning-state-tracker`?
   - How to handle resource URIs: single namespace or separate per level?
   - State storage: SQLite DB or JSON files?

2. **Hook Execution Order**:
   - When multiple hooks trigger (validation + state sync + invalidation), what's the order?
   - How to pass data between hooks (e.g., validation result → state update)?
   - Should hooks run sequentially or can some be parallel?

3. **Agent Prompt Injection**:
   - How exactly to inject parent context into planning-coordinator Phase 1?
   - Should we modify existing agents or create wrapper agents?
   - How to maintain agent isolation while sharing parent context?

4. **Version Hash Calculation**:
   - Use file content hash (MD5/SHA256)?
   - Use git commit hash if available?
   - Include timestamps in hash or separate?

5. **Graceful Degradation**:
   - What happens if MCP server crashes mid-planning?
   - Can we fallback to manual state files (current approach)?
   - How to recover/sync state after MCP server restart?

6. **Command Structure**:
   - Separate commands (`/plan-act`, `/plan-chapter`, `/plan-scene`) or unified (`/plan <type> <id>`)?
   - Should `/plan-story` remain separate or be merged into new hierarchy?
   - Backward compatibility with existing `/plan-story` usage?

7. **Cascading Behavior Scope**:
   - When act regenerated, invalidate ALL chapters → ALL scenes (deep cascade)?
   - Or invalidate only chapters, require manual chapter revalidation before scene invalidation?
   - Performance impact of deep cascade on large acts?

8. **Approval Workflow**:
   - Should "draft" → "approved" transition require validation checks?
   - Can user approve even if consistency warnings exist?
   - Who can approve: only author or also automated validators?

---

## Success Metrics

The feature is successful when:

1. **User can plan entire act hierarchy without manual file management**:
   - Start with `/plan-act 1`
   - Progress through chapters
   - Create scene blueprints
   - Never manually edit state files

2. **System enforces hierarchy automatically**:
   - Attempting to skip levels produces clear error messages
   - Errors include actionable next steps
   - No confusion about what to do next

3. **Parent context flows naturally to children**:
   - Chapter planning receives act plan automatically
   - Scene planning receives chapter plan automatically
   - No need to manually copy/paste context

4. **Regeneration invalidation is clear and safe**:
   - User understands what will be invalidated before confirming
   - Backups are created automatically
   - Invalidated entities are clearly marked
   - Recovery path is obvious

5. **MCP/hooks are invisible to user**:
   - User never thinks about "MCP" or "hooks"
   - Everything just works
   - Errors are human-readable, not technical
   - State tracking happens automatically

6. **Agents focus on creative work**:
   - Agents don't write state files
   - Agents don't validate hierarchy
   - Agents receive context, generate content, return results
   - All orchestration handled by MCP/hooks

---

## Next Steps

1. **Hand off to `agent-architect`** for technical design:
   - Review this Feature Brief
   - Resolve open questions
   - Design MCP server architecture
   - Design hook system architecture
   - Design agent integration points
   - Create implementation plan

2. **Create technical specification** (agent-architect output):
   - MCP server spec (extend FEAT-0002)
   - Hook system spec
   - Agent modification spec
   - State schema definitions
   - API contracts

3. **Implementation phases** (after technical design):
   - Phase 1: MCP server for hierarchical state
   - Phase 2: Validation hooks
   - Phase 3: Invalidation hooks
   - Phase 4: Agent integration (context injection)
   - Phase 5: Commands (`/plan-act`, `/plan-chapter`, etc.)
   - Phase 6: Approval workflow
   - Phase 7: Version management

---

## Related Features

- **FEAT-0001**: Generation Workflow (blueprint → prose)
- **FEAT-0002**: Workflow State Tracking (MCP server spec)
- **Current `/plan-story`**: Interactive planning dialogue

This feature integrates with all three to create unified hierarchical workflow.

---

**Ready for Technical Design:** ✅ YES

**Agent-Architect Task:**
Design the technical architecture for hierarchical planning workflow, focusing on:
1. MCP server design (state tracking, tools, resources)
2. Hook system design (execution order, data passing, error handling)
3. Agent integration patterns (context injection without breaking isolation)
4. Command routing (unified vs. separate commands)
5. Cascading invalidation algorithm
6. Version management implementation
7. Recovery and fallback mechanisms

Use Anthropic agent best practices: isolation, artifact-passing, human-in-the-loop, observability.
