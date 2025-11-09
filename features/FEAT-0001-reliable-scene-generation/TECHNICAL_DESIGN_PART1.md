# Technical Design Part 1: Architecture & Agents

**Feature**: FEAT-0001 - Reliable Scene Generation with Plot Control
**Version**: 1.1 (Versioning Fixed)
**Date**: 2025-10-31
**Status**: Design Phase 1 Complete

---

## 0. File Naming Standards

### 0.1 The Real Problem

The core issue was NOT "bad v2 vs good v3". The real problem was **multiple files with different names** causing ambiguity:

```
plan.md (original)
plan-revised.md (rewrite #1)
plan-v2.md (rewrite #2)
plan-v3.md (rewrite #3)
```

**Result:** Agents didn't know which file was current:
- prose-writer read `plan-v2.md`
- blueprint-validator expected `plan-v3.md`
- coordinator looked for `plan.md`
→ Chaos, inconsistency, constraint violations

### 0.2 Solution: ONE Canonical File

**✅ ALWAYS use these standard names:**
```
acts/act-{N}/chapters/chapter-{NN}/plan.md
acts/act-{N}/chapters/chapter-{NN}/scenes/scene-{NNNN}-blueprint.md
acts/act-{N}/chapters/chapter-{NN}/content/scene-{NNNN}.md
```

**❌ NEVER create files with version suffixes:**
```
plan-revised.md       ← WRONG
plan-v2.md           ← WRONG
plan-v3.md           ← WRONG
plan-final.md        ← WRONG
scene-X-blueprint-revised.md  ← WRONG
```

### 0.3 Versioning Method: Timestamped Backups

**Directory Structure:**
```
acts/act-1/chapters/chapter-02/
├── plan.md                      ← Current version (ONLY this file)
├── scenes/
│   ├── scene-0201-blueprint.md  ← Current blueprint (ONLY this file)
│   ├── scene-0202-blueprint.md
│   └── scene-0204-blueprint.md
├── content/
│   ├── scene-0201.md
│   └── scene-0204.md
└── backups/                     ← Timestamped copies of old versions
    ├── plan-2025-10-27-14-30.md
    ├── plan-2025-10-25-09-15.md
    └── scene-0204-blueprint-2025-10-29-16-45.md
```

**Backup Naming:**
```
{original-name}-{YYYY-MM-DD-HH-MM}.md

Examples:
plan-2025-10-31-10-30.md
scene-0204-blueprint-2025-10-31-15-45.md
```

### 0.4 Agent File Handling Rules

**Rule 1: Single Source of Truth**
- ALWAYS read `plan.md` (no version suffix)
- ALWAYS read `scene-{ID}-blueprint.md` (no version suffix)
- NEVER guess which file to use

**Rule 2: Multiple Files = ERROR**
If agent finds:
```
plan.md AND plan-revised.md
```
→ **Stop immediately with error:**
```
❌ Multiple plan files detected in chapter-02/:
- plan.md
- plan-revised.md

ACTION REQUIRED:
1. Decide which file is current
2. Rename it to plan.md (if not already)
3. Move others to backups/:
   mv plan-revised.md backups/plan-2025-10-25.md
4. Re-run generation

Do NOT proceed until only ONE plan.md exists.
```

**Rule 3: Automatic Migration**
If agent finds ONLY versioned file (no standard file):
```
Found: plan-v3.md
Not found: plan.md
```
→ **Suggest migration:**
```
⚠️ Plan file uses old naming: plan-v3.md

RECOMMENDED ACTION:
mv plan-v3.md plan.md

This should be done once, then use plan.md going forward.
```

**Rule 4: Backup Before Modification**
Before any agent modifies `plan.md` or `blueprint.md`:
```python
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
backup_path = f"backups/plan-{timestamp}.md"
shutil.copy("plan.md", backup_path)
# Now safe to modify plan.md
```

---

## 1. Architecture Overview

### 1.1 System Purpose

Transform scene generation from an error-prone process requiring manual regenerations into a reliable, transparent, human-controlled workflow that guarantees blueprint compliance through multi-stage validation and constraint enforcement.

### 1.2 Core Principles Applied

**From Research (electronics-14-01662-v3.pdf):**
- **Cognitive Load Distribution**: Specialized agents handle discrete validation/generation tasks
- **Loose Coupling**: Agents communicate via file-based artifacts, not shared state
- **Observability First**: Every step logged for debugging and user transparency

**From Anthropic Best Practices:**
- **Single Responsibility**: Each agent has ONE clear purpose
- **Fail-Fast**: Early validation prevents expensive rework
- **Human-in-the-Loop**: Critical decisions (verification plan approval) require human input
- **Constraint-Oriented Prompting**: CoS (Chain of Specification) and LIFT-COT patterns for reliable constraint adherence

### 1.3 Architecture Diagram

```
USER REQUEST: "Generate scene 0204"
    ↓
┌───────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR: generation-coordinator                          │
│ (New agent - coordinates 7-step process)                      │
└───────────────────────────────────────────────────────────────┘
    ↓
    ↓ [Step 1: Pre-Check]
    ↓
┌──────────────────────┐
│ FILE SYSTEM CHECK    │ ← Does blueprint exist?
│ (coordinator logic)  │   If NO → ERROR: Use /plan-scene
└──────────────────────┘
    ↓ YES
    ↓
    ↓ [Step 2: Blueprint Validation - AUTO]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ blueprint-validator (NEW)                                    │
│ Input: blueprint file path                                   │
│ Output: constraints-list.json OR validation-errors.json      │
│ Speed: <20 seconds                                           │
└──────────────────────────────────────────────────────────────┘
    ↓ PASS
    ↓ (constraints extracted)
    ↓
    ↓ [Step 3: Verification Plan - INTERACTIVE]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ verification-planner (NEW)                                   │
│ Input: constraints-list.json                                 │
│ Output: verification-plan.md (shows to user)                 │
│ Speed: <15 seconds                                           │
└──────────────────────────────────────────────────────────────┘
    ↓
    ↓ [HUMAN APPROVAL - CRITICAL TOUCHPOINT]
    ↓
┌──────────────────────┐
│ USER REVIEWS PLAN    │ → Approve (Y)
│ Shown by coordinator │ → Modify (specify changes)
│                      │ → Cancel (n)
└──────────────────────┘
    ↓ APPROVED
    ↓ (verified-plan.json saved)
    ↓
    ↓ [Step 4: Generation - AUTO]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ prose-writer (MODIFIED)                                      │
│ Input: verified-plan.json + blueprint + context files        │
│ Output: scene-[ID]-draft.md + compliance-echo.json           │
│ Speed: 3-5 minutes (for 1000-1100 words)                     │
│ Constraints: Isolated block + Repetition (3x)                │
└──────────────────────────────────────────────────────────────┘
    ↓
    ↓ [Step 5: Fast Compliance Check - AUTO]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ blueprint-compliance-fast-checker (NEW)                      │
│ Input: scene-[ID]-draft.md + constraints-list.json           │
│ Output: compliance-result.json                               │
│ Speed: <30 seconds                                           │
└──────────────────────────────────────────────────────────────┘
    ↓
    ├─── PASS ────→ [Step 6: Full Validation]
    │
    └─── FAIL ────→ [Auto-Retry Logic]
                       ↓
                   ┌────────────────────────────────────┐
                   │ Retry Counter < 3?                 │
                   │ YES → Regenerate (Step 4, enhanced)│
                   │ NO → STOP, report to user          │
                   └────────────────────────────────────┘
    ↓ PASS
    ↓
    ↓ [Step 6: Full Validation - PARALLEL]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ validation-aggregator (NEW or ENHANCED)                     │
│ Coordinates 7 validators in parallel                        │
└──────────────────────────────────────────────────────────────┘
    ↓
    ↓ Spawns parallel agents:
    ↓
┌─────────────┬─────────────┬──────────────┬─────────────┐
│ world-      │ canon-      │ character-   │ plot-       │
│ lorekeeper  │ guardian    │ state        │ architect   │
└─────────────┴─────────────┴──────────────┴─────────────┘
┌─────────────┬─────────────┬──────────────┐
│ scene-      │ chronicle-  │ dialogue-    │
│ structure   │ keeper      │ analyst      │
└─────────────┴─────────────┴──────────────┘
    ↓ (all return validation-result.json)
    ↓
┌──────────────────────────────────────────────────────────────┐
│ validation-aggregator aggregates results                     │
│ Output: final-validation-report.json                         │
└──────────────────────────────────────────────────────────────┘
    ↓
    ↓ [Step 7: Final Output]
    ↓
┌──────────────────────────────────────────────────────────────┐
│ generation-coordinator formats final output                  │
│ Shows: summary, key moments, file path, next steps           │
│ Does NOT show: full text (already in file)                   │
└──────────────────────────────────────────────────────────────┘
    ↓
USER RECEIVES: Scene ready, transparent report, recommendations
```

### 1.4 Data Flow Summary

**Artifact Flow:**

1. `scene-[ID]-blueprint.md` (input, pre-existing)
2. `constraints-list.json` (Step 2 → Step 3,4,5)
3. `verification-plan.md` (Step 3 → User)
4. `verified-plan.json` (User approval → Step 4)
5. `scene-[ID]-draft.md` (Step 4 → Step 5,6)
6. `compliance-result.json` (Step 5 → Coordinator retry logic)
7. `validation-result.json` (Step 6, per validator)
8. `final-validation-report.json` (Step 6 → Step 7)

**Context Window Management:**
- ALL artifacts >100 lines stored as files
- Agents receive file paths, NOT content
- Coordinator reads summaries, not full texts
- prose-writer gets ONLY: blueprint + verified-plan + previous scene + POV character sheet

### 1.5 Human-in-the-Loop Touchpoints

**CRITICAL (blocks execution):**
- Step 3: Verification plan approval (user confirms understanding)

**INFORMATIONAL (user observes):**
- Step 1: Blueprint found/not found
- Step 2: Validation pass/fail
- Step 5: Retry count (if >1 attempt needed)
- Step 7: Final summary and recommendations

**HIDDEN (internal automation):**
- Step 4: Actual prose generation (user sees only timing)
- Step 5: Fast compliance checks during retries
- Step 6: Parallel validation (user sees aggregated results)

---

## 2. Core Agents Specifications

### 2.1 generation-coordinator

**Type**: New Agent
**Role**: Orchestrator for 7-step reliable generation workflow

#### Purpose
Coordinate the entire generation process from blueprint validation through final output, managing state between steps, handling retries, and providing transparent progress to the user.

#### Single Responsibility
Workflow orchestration ONLY. Does NOT perform validation, generation, or formatting tasks itself - delegates to specialized agents.

#### Inputs
- **User prompt**: "Generate scene [ID]" or similar
- **Scene ID**: Extracted from prompt (e.g., "0204")
- **Project root**: E:\sources\book-alexa-right

#### Outputs
- **Final user message**: Formatted output with summary, validation results, next steps
- **State artifacts**: Temporary files in workspace/generation-runs/[run-id]/

#### Trigger Conditions
User requests scene generation via natural language prompt mentioning scene ID.

#### Logic (Step-by-step)

1. **Parse Request**
   - Extract scene ID from user prompt
   - Determine act/chapter from ID (e.g., 0204 → act-1/chapter-02)

2. **Step 1: File System Check**
   - Construct blueprint path: `acts/act-{act}/chapters/chapter-{ch}/scenes/scene-{ID}-blueprint.md`
   - Check file existence
   - IF NOT FOUND → Return error: "Blueprint not found. Use /plan-scene {ID}"
   - IF FOUND → Continue

3. **Step 2: Blueprint Validation**
   - Invoke `blueprint-validator` agent
   - Pass: blueprint file path, scene ID
   - Wait for output: constraints-list.json OR validation-errors.json
   - IF FAIL → Return errors to user, STOP
   - IF PASS → Store constraints, continue

4. **Step 3: Verification Plan**
   - Invoke `verification-planner` agent
   - Pass: constraints-list.json
   - Receive: verification-plan.md
   - Display plan to user with prompt: "All correct? (Y/n) | Modify?"
   - Wait for user input
   - IF "Y" or Enter → Save verified-plan.json, continue
   - IF modifications → Update plan, re-display, loop
   - IF "n" → Ask what's wrong, handle clarification

5. **Step 4: Generation Loop** (with retry logic)
   - Initialize retry_count = 0
   - LOOP (max 3 iterations):
     - Invoke `prose-writer` with verified-plan.json, blueprint, context
     - Receive: scene-{ID}-draft.md
     - Proceed to Step 5
     - IF Step 5 PASS → Break loop
     - IF Step 5 FAIL AND retry_count < 2 → Increment retry_count, regenerate with enhanced constraints
     - IF Step 5 FAIL AND retry_count == 2 → STOP, report failure to user
   - User does NOT see failed attempts (only final result or critical failure)

6. **Step 5: Fast Compliance Check**
   - Invoke `blueprint-compliance-fast-checker`
   - Pass: scene-{ID}-draft.md, constraints-list.json
   - Receive: compliance-result.json
   - IF PASS → Continue to Step 6
   - IF FAIL → Return to Step 4 (retry logic)

7. **Step 6: Full Validation**
   - Invoke `validation-aggregator`
   - Pass: scene-{ID}-draft.md, blueprint, context references
   - Wait for final-validation-report.json (aggregated from 7 validators)
   - Store results

8. **Step 7: Format Output**
   - Read final-validation-report.json
   - Generate summary (2-3 sentences from draft)
   - Extract key moments
   - Format final message with:
     - File path
     - Word count
     - Generation time
     - Retry count
     - Summary
     - Validation results (checkmarks)
     - Next steps recommendations
   - Return to user

#### Constraints Applied (8 Rules)

- **Rule 5 (Single Source of Truth)**: Always uses exact blueprint path, never guesses
- **Rule 4 (Fail-Fast)**: Stops at first validation failure
- **Rule 2 (Verification Checkpoint)**: Enforces human approval at Step 3
- **Observability**: Logs all steps to workspace/logs/generation-coordinator/

#### Performance Target

- **Total time**: 5-8 minutes (including user approval time ~30s)
- **Steps 1-3**: <1 minute combined
- **Step 4**: 3-5 minutes (prose generation)
- **Steps 5-6**: 1-2 minutes
- **Step 7**: <10 seconds

#### Edge Cases Handled

- Blueprint not found → Clear error message
- Validation fails (Step 2) → Stop with specific issues
- User declines plan (Step 3) → Clarification dialog
- 3 generation failures → Stop with detailed report
- Validation warnings (non-blocking) → Show in final output

---

### 2.2 blueprint-validator

**Type**: New Agent
**Role**: Pre-generation blueprint compliance checker

#### Purpose
Validate that scene blueprint is complete, internally consistent, and compliant with current plan BEFORE expensive generation begins. Fail-fast principle in action.

#### Single Responsibility
Blueprint validation ONLY. Does NOT generate, modify, or suggest content - only validates existing blueprint structure and compliance.

#### Inputs

- **blueprint_path** (string): Absolute path to blueprint file
  - Example: `E:\sources\book-alexa-right\acts\act-1\chapters\chapter-02\scenes\scene-0204-blueprint.md`
- **scene_id** (string): Scene identifier
  - Example: "0204"

#### Outputs

**SUCCESS Case** (GO):
```json
// File: workspace/validation/scene-{ID}-constraints-list.json
{
  "status": "PASS",
  "scene_id": "0204",
  "blueprint_path": "...",
  "timestamp": "2025-10-31T10:30:00Z",
  "constraints": {
    "location": {
      "required": "Башня Книжников, медпалата",
      "forbidden": ["больница", "медицинский центр", "госпиталь"]
    },
    "characters": {
      "present": ["Алекса Райт", "Реджинальд Хавенфорд"],
      "absent": ["Себастьян Грей"],
      "absent_reason": ["removed per plan"]
    },
    "mechanics": {
      "required": "Automatic system compensation notification",
      "forbidden": ["personal gift", "manual compensation"]
    },
    "scope": {
      "beats": [1, 2, 3, 4],
      "forbidden_content": ["scene-0203 memory", "scene-0205 content"]
    },
    "word_count": {
      "min": 1000,
      "max": 1100
    }
  },
  "validation_checks": [
    {"check": "file_naming_standard", "result": "PASS"},
    {"check": "no_duplicate_files", "result": "PASS"},
    {"check": "plan_file_exists", "result": "PASS"},
    {"check": "location_specified", "result": "PASS"},
    {"check": "characters_clear", "result": "PASS"},
    {"check": "mechanics_defined", "result": "PASS"},
    {"check": "scope_bounded", "result": "PASS"},
    {"check": "no_internal_contradictions", "result": "PASS"}
  ]
}
```

**FAILURE Case** (NO-GO):
```json
// File: workspace/validation/scene-{ID}-validation-errors.json
{
  "status": "FAIL",
  "scene_id": "0204",
  "blueprint_path": "...",
  "timestamp": "2025-10-31T10:30:00Z",
  "errors": [
    {
      "type": "file_naming_violation",
      "severity": "HIGH",
      "message": "Blueprint file uses non-standard naming: scene-0204-blueprint-revised.md",
      "fix": "Rename to scene-0204-blueprint.md (standard name)"
    },
    {
      "type": "multiple_files_detected",
      "severity": "CRITICAL",
      "message": "Multiple blueprint files found: scene-0204-blueprint.md, scene-0204-blueprint-v2.md",
      "fix": "Move old versions to backups/, keep only scene-0204-blueprint.md"
    },
    {
      "type": "contradiction",
      "severity": "HIGH",
      "message": "Beat 2 mentions 'Себастьян Грей enters' but characters section lists him as absent",
      "fix": "Remove Себастьян from Beat 2 or clarify character list"
    }
  ],
  "required_actions": [
    "Fix high-severity errors",
    "Re-run blueprint-validator",
    "Do NOT proceed to generation until validation passes"
  ]
}
```

#### Logic

1. **Check File Naming**
   - Verify blueprint follows standard: `scene-{ID}-blueprint.md` (no version suffix)
   - IF file has version suffix (e.g., `scene-0204-blueprint-v2.md`) → ERROR
   - Scan directory for multiple blueprint files with same ID
   - IF multiple files found → CRITICAL ERROR: "Clean up duplicate files first"

2. **Check Plan File**
   - Construct plan path: `acts/act-{act}/chapters/chapter-{ch}/plan.md`
   - Verify plan.md exists (NOT plan-v2.md, plan-v3.md, etc.)
   - IF plan file has version suffix → WARNING: "Suggest migration to plan.md"
   - Scan directory for multiple plan files
   - IF multiple plan files → CRITICAL ERROR: "Only one plan.md allowed"

3. **Read Blueprint File**
   - Load file from blueprint_path
   - IF file not found → ERROR: "Blueprint file not found at {path}"

4. **Extract Metadata**
   - Parse status (e.g., "Status: APPROVED FOR GENERATION")
   - Parse date
   - Parse scene structure

5. **Extract Critical Requirements**
   - **Location**: Extract from "Location:" field or "MUST BE" constraint
     - Check clarity: Is it specific enough?
     - Extract forbidden locations from "MUST NOT BE" or old versions
   - **Characters**: Extract from "Characters:" section
     - Separate "present" and "absent" lists
     - Check for plan-removed characters (e.g., Себастьян Грей)
   - **Mechanics**: Extract from "Mechanics:" or "World Mechanics" section
     - Identify required mechanics
     - Identify forbidden alternatives
   - **Scope**: Extract beats or structure
     - Identify which beats belong to THIS scene
     - Note any mentions of other scenes (potential scope violations)

6. **Internal Consistency Checks**
   - Characters: Are characters in "absent" list never mentioned in beats?
   - Location: Is location consistent throughout beats?
   - Mechanics: Do beats describe mechanics consistently?
   - Scope: Do beats reference only this scene's content?

7. **Cross-Reference with Plan**
   - Read current plan.md
   - Compare blueprint against documented plan changes
   - Flag any elements marked "REMOVED" in plan that appear in blueprint
   - Flag any "CHANGED" elements that use old form

8. **Completeness Checks**
   - Required fields present: location, characters, mechanics, scope, word count
   - Structure defined: beats or outline
   - Emotional tone specified (for generation guidance)

9. **Generate Output**
   - IF all checks PASS → Create constraints-list.json with extracted constraints
   - IF any check FAIL → Create validation-errors.json with specific issues
   - Save to workspace/validation/

#### Constraints Applied

- **Rule 4 (Fail-Fast)**: This agent IS the fail-fast mechanism
- **Rule 5 (Single Source of Truth)**: Validates exactly ONE blueprint file, never multiple
- **File Naming Standards**: Enforces standard naming convention
- **Observability**: Logs all validation checks performed

#### Performance Target

- **Speed**: <20 seconds for typical blueprint (3-5 pages)
- **Accuracy**: 100% detection of missing required fields
- **Precision**: <5% false positives (incorrect NO-GO)

#### Special Handling

- **Ambiguous Constraints**: If a constraint is present but unclear (e.g., "Location: медпалата" without specifying which building), flag as WARNING not ERROR
- **Multiple Versions**: If multiple version files exist (e.g., scene-0204-blueprint-v2.md, scene-0204-blueprint.md), raise CRITICAL ERROR - never guess
- **Plan Changes**: Cross-references current plan.md for documented changes (character removals, location standardization, mechanics changes)
- **Migration Support**: If only versioned file exists (e.g., scene-0204-blueprint-v3.md, no scene-0204-blueprint.md), suggest one-time migration

---

### 2.3 verification-planner

**Type**: New Agent
**Role**: Human-readable verification plan generator

#### Purpose
Transform extracted constraints into a clear, reviewable plan that shows the user EXACTLY what will be generated, enabling informed approval before expensive prose generation.

#### Single Responsibility
Plan formatting and presentation ONLY. Does NOT validate (that's blueprint-validator) or generate prose (that's prose-writer) - only translates constraints into human-readable format.

#### Inputs

- **constraints_list.json** (file path): Output from blueprint-validator
  - Contains: location, characters, mechanics, scope, word count
- **blueprint_path** (string): Original blueprint for reference
- **previous_scene_summary** (optional, string): Brief context of what happened before

#### Outputs

**verification-plan.md** (file):
```markdown
## 🔍 GENERATION PLAN - REVIEW BEFORE PROCEEDING

**Scene**: 0204
**Date**: 2025-10-31
**Status**: Awaiting your approval

---

### 📍 LOCATION
**Setting**: Башня Книжников, медпалата
**NOT using**: Больница, медицинский центр (outdated locations)

### 👥 CHARACTERS
**Present in scene**:
- Алекса Райт (POV character)
- Реджинальд Хавенфорд (patient)

**Explicitly ABSENT**:
- Себастьян Грей (removed per chapter plan - will NOT appear)

### 🎭 PLOT BEATS
**Beat 1**: Продолжение работы в медпалате
- Алекса продолжает сеанс Погружения с Реджинальдом

**Beat 2**: Погружение - память о смерти дочери
- Реджинальд переживает болезненную память
- Алекса профессионально ведёт сеанс

**Beat 3**: Эмоциональная реакция Алексы
- Алекса затронута страданием Реджинальда
- Внутренний конфликт: профессионализм vs эмпатия

**Beat 4**: Завершение с начислением компенсации
- Сеанс завершается
- Система автоматически начисляет +2 месяца компенсации

### ⚙️ WORLD MECHANICS
**Using**: Automatic system compensation (система начисляет компенсацию автоматически)
**NOT using**: Personal gift, manual compensation from characters

### 📊 TECHNICAL SPECS
- **Word count**: 1000-1100 words
- **POV**: Алекса Райт (third person limited)
- **Emotional tone**: Professional with underlying emotional resonance
- **Continuity**: Follows scene 0203 (Алекса вошла в медпалату)

---

### ✅ CONSTRAINT CHECKLIST
- [ ] Location: Башня Книжников медпалата (NOT hospital)
- [ ] Себастьян Грей does NOT appear (removed per plan)
- [ ] Compensation is automatic system, NOT personal gift
- [ ] Scope: Only these 4 beats, no content from other scenes

---

**Is this plan correct?**
- Type **Y** or press Enter to approve and start generation
- Type **n** to cancel
- Specify changes (e.g., "Change emotional tone to more detached")
```

#### Logic

1. **Load Constraints**
   - Read constraints_list.json from file
   - Parse all constraint categories

2. **Format Location Section**
   - Extract required location
   - Extract forbidden locations
   - Present clearly with "MUST BE" and "NOT using" distinction

3. **Format Characters Section**
   - List present characters with roles
   - List absent characters with reasons (especially plan removals)
   - Use visual distinction (checkmark for present, X for absent)

4. **Format Plot Beats**
   - Extract beat structure from blueprint (referenced in constraints)
   - Present in numbered/labeled format
   - Include brief description of each beat
   - Highlight any plot consequences or emotional arcs

5. **Format Mechanics Section**
   - Describe required world mechanics in plain language
   - Contrast with forbidden alternatives
   - Use examples if helpful

6. **Format Technical Specs**
   - Word count range
   - POV specification
   - Tone/style guidance
   - Continuity notes

7. **Generate Checklist**
   - Convert critical constraints into checkbox format
   - Use YES/NO framing for clarity
   - Highlight plan changes

8. **Add Approval Prompt**
   - Clear instructions for approval (Y/n)
   - Option to specify changes
   - Friendly, concise

9. **Save to File**
   - Write to workspace/verification/scene-{ID}-verification-plan.md
   - Return file path to coordinator

#### Constraints Applied

- **Rule 2 (Verification Checkpoint)**: This agent implements the checkpoint
- **Rule 1 (Constraint Isolation)**: Presents constraints in isolated, clear blocks
- **Human-in-the-Loop**: Designed specifically for human review
- **Clarity over Brevity**: Readable format more important than minimal tokens

#### Performance Target

- **Speed**: <15 seconds
- **Clarity**: Non-technical users should understand 100% of plan
- **Completeness**: All critical constraints visible, no hidden decisions

#### User Interaction Flow

1. Coordinator invokes verification-planner
2. Planner generates verification-plan.md
3. Coordinator displays plan to user
4. User responds:
   - **"Y" or Enter**: Coordinator saves approved plan as verified-plan.json, proceeds to generation
   - **"n"**: Coordinator asks "What's wrong?" and handles clarification
   - **"Change X to Y"**: Coordinator updates constraints, re-invokes planner with modified constraints, shows updated plan
5. Loop until approval

#### Modification Handling

When user requests changes (e.g., "Change emotional tone to more detached"):
- Coordinator parses request
- Updates relevant constraint in constraints-list.json (creates modified version)
- Re-invokes verification-planner with updated constraints
- Shows updated plan for re-approval
- No limit on modification iterations (but coordinator may suggest updating blueprint after 5+ iterations)

---

### 2.4 prose-writer (MODIFIED)

**Type**: Existing Agent (MODIFIED for FEAT-0001)
**Role**: Literary prose generator with strict constraint compliance

#### Purpose
Generate high-quality literary prose for a scene based on approved verification plan, adhering to ALL critical constraints without exception.

#### Single Responsibility
Prose generation ONLY. Does NOT validate blueprints (blueprint-validator), create plans (verification-planner), or check compliance (fast-checker) - only generates text.

#### Changes from Current Implementation

**BEFORE (current):**
- Receives blueprint directly
- Generates prose in single step
- Constraints embedded in long prompt
- Returns full text in response

**AFTER (FEAT-0001):**
- Receives verified-plan.json (approved by user)
- Uses constraint-isolated prompt template (Rule 1)
- Constraints repeated 3x (Rule 3): start, inline, end
- Receives ONLY necessary context files (Rule 8)
- Returns compliance-echo.json + saves text to file
- Does NOT return full text in response (context conservation)

#### Inputs

**Primary:**
- **verified-plan.json** (file path): Approved plan from Step 3
  - Contains: all constraints, user modifications
- **blueprint_path** (string): Original blueprint for full context
- **scene_id** (string): Scene identifier

**Context (Minimal - Rule 8):**
- **previous_scene_path** (string): Previous scene for continuity
  - Example: `acts/act-1/chapters/chapter-02/content/scene-0203.md`
- **pov_character_sheet** (string): Character sheet for POV character
  - Example: `context/characters/alexa-wright.md`
- **world_mechanics_excerpt** (optional): Specific mechanics referenced in blueprint
  - Example: `context/world-bible/mechanics/compensation-system.md`

**NOT Provided (isolation):**
- Other scene blueprints
- Full plan document
- Unrelated character sheets
- Full world-bible

#### Outputs

**Primary:**
```
File: acts/act-{act}/chapters/chapter-{ch}/content/scene-{ID}-draft.md

[Full literary text, 1000-1100 words]
[Written in approved style, POV, tone]
[Adheres to all constraints]
```

**Metadata:**
```json
// File: workspace/generation/scene-{ID}-compliance-echo.json
{
  "scene_id": "0204",
  "timestamp": "2025-10-31T10:45:00Z",
  "constraints_acknowledged": {
    "location": "Башня Книжников, медпалата",
    "characters_present": ["Алекса Райт", "Реджинальд Хавенфорд"],
    "characters_absent": ["Себастьян Грей"],
    "mechanics": "Automatic system compensation",
    "scope": "Beats 1-4 only",
    "word_count_target": "1000-1100"
  },
  "actual_metrics": {
    "word_count": 1050,
    "beat_structure": ["Beat 1", "Beat 2", "Beat 3", "Beat 4"]
  },
  "compliance_declaration": "All critical constraints met",
  "draft_file_path": "acts/act-1/chapters/chapter-02/content/scene-0204-draft.md"
}
```

#### Logic (Prompt Structure)

**Prompt Template v2.0 Applied:**

```markdown
## ⚠️ CRITICAL CONSTRAINTS (MUST COMPLY - NO EXCEPTIONS)

[Isolated constraint block from Rule 1]

### LOCATION
- MUST BE: Башня Книжников, медпалата
- MUST NOT BE: Больница, медицинский центр, госпиталь

### CHARACTERS
- MUST BE PRESENT: Алекса Райт, Реджинальд Хавенфорд
- MUST NOT BE PRESENT: Себастьян Грей (removed per plan)

### MECHANICS
- MUST USE: Automatic system compensation notification
- MUST NOT USE: Personal gift, manual compensation

### SCOPE
- MUST INCLUDE ONLY: Beats 1-4 from Scene 0204
- MUST NOT INCLUDE: Content from scenes 0203, 0205

---

## 📄 SOURCE OF TRUTH

**PRIMARY BLUEPRINT**: [exact file path to scene-{ID}-blueprint.md]
**VERIFIED PLAN**: [exact file path to verified-plan.json]
**CURRENT PLAN**: acts/act-{N}/chapters/chapter-{NN}/plan.md
Status: APPROVED FOR GENERATION

⚠️ DO NOT USE:
- Any files with version suffixes (e.g., plan-v2.md, blueprint-revised.md)
- Draft or workspace files
- Multiple files with same base name

IF FILES DO NOT EXIST OR MULTIPLE VERSIONS FOUND: STOP and return error

---

## 🎯 TASK: Generate Literary Prose

[Detailed generation instructions]

### STRUCTURE (from verified plan):
**Beat 1**: Продолжение работы в медпалате
**REMINDER**: Location is Башня Книжников медпалата, NOT hospital

**Beat 2**: Погружение - память о смерти дочери
**REMINDER**: Себастьян Грей does NOT appear (removed per plan)

**Beat 3**: Эмоциональная реакция Алексы

**Beat 4**: Завершение с начислением компенсации
**REMINDER**: Compensation is AUTOMATIC system, NOT personal gift

[... sensory palette, tone, style instructions ...]

---

## ✅ FINAL CHECKLIST (Check before returning)

Before you return your output, verify:
- [ ] Location: Башня Книжников медпалата ✓
- [ ] No Себастьян Грей present ✓
- [ ] Automatic compensation (not personal gift) ✓
- [ ] Only Beats 1-4 (no content from 0203/0205) ✓
- [ ] Word count: 1000-1100 ✓

---

## 📤 OUTPUT FORMAT (REQUIRED)

You MUST:
1. Save prose to: acts/act-1/chapters/chapter-02/content/scene-0204-draft.md
2. Create compliance echo: workspace/generation/scene-0204-compliance-echo.json
3. Return ONLY metadata in your response, NOT full text

---

[Constraint repetition - 3rd occurrence]
```

#### Constraints Applied

- **Rule 1 (Constraint Isolation)**: CRITICAL CONSTRAINTS block at top
- **Rule 2 (Verification Checkpoint)**: Uses pre-approved verified-plan.json
- **Rule 3 (Constraint Repetition)**: Constraints repeated 3x (start, inline beats, final checklist)
- **Rule 5 (Single Source of Truth)**: Exact file paths specified, no version suffixes allowed
- **Rule 7 (Constraint Echo)**: compliance-echo.json required output
- **Rule 8 (Minimal Context)**: Receives ONLY necessary files
- **Context Conservation**: Full text saved to file, NOT returned in response

#### Performance Target

- **Speed**: 3-5 minutes for 1000-1100 word scene
- **Token Usage**: ~8000-12000 tokens (input + output combined)
- **Constraint Compliance**: >95% first-attempt success after FEAT-0001 implementation

#### Regeneration Enhancement (Retry Logic)

When fast-checker detects failure and coordinator triggers retry:

**Attempt 1** (normal): Standard prompt as above

**Attempt 2** (enhanced): Same prompt + additional emphasis:
```markdown
⚠️⚠️⚠️ REGENERATION ATTEMPT 2 ⚠️⚠️⚠️

Previous generation failed compliance check due to:
[specific violation from fast-checker]

PAY SPECIAL ATTENTION TO:
- [violated constraint repeated 3 more times]
- [ALL CAPS EMPHASIS on critical element]

This is attempt 2 of 3. Critical compliance required.
```

**Attempt 3** (maximum emphasis): Attempt 2 prompt + even stronger framing:
```markdown
🚨 FINAL ATTEMPT (3/3) 🚨

Previous attempts failed: [violations listed]

ABSOLUTE REQUIREMENTS:
[Violated constraints in BOLD, ALL CAPS, repeated 5x]

IF YOU CANNOT COMPLY: Return error, do NOT generate non-compliant text.
```

#### Edge Cases Handled

- **Verified plan contradicts blueprint**: Use verified plan (it's user-approved, may include intentional changes)
- **Context files missing**: STOP and return error (do not proceed with incomplete context)
- **Ambiguous constraint**: STOP and request clarification (do not guess)
- **Word count cannot be met with beats**: Prioritize beats (content) over exact word count, but stay within ±10% range

---

### 2.5 blueprint-compliance-fast-checker

**Type**: New Agent
**Role**: Fast surface-level compliance checker

#### Purpose
Catch obvious constraint violations (wrong location, forbidden characters, scope bleed) within 30 seconds, enabling fast-fail before expensive deep validation. Prevents wasted validation cycles on fundamentally broken drafts.

#### Single Responsibility
Surface-level compliance checking ONLY. Does NOT perform deep lore validation (world-lorekeeper), canon checking (canon-guardian), or structural analysis (scene-structure) - only fast, obvious checks.

#### Inputs

- **draft_path** (string): Path to generated prose draft
  - Example: `acts/act-1/chapters/chapter-02/content/scene-0204-draft.md`
- **constraints_list.json** (file path): Constraints from blueprint-validator
- **scene_id** (string): Scene identifier

#### Outputs

**PASS Case:**
```json
// File: workspace/validation/scene-{ID}-fast-compliance-result.json
{
  "status": "PASS",
  "scene_id": "0204",
  "draft_path": "...",
  "timestamp": "2025-10-31T10:47:00Z",
  "checks_performed": [
    {"check": "location_match", "result": "PASS", "details": "Found 'Башня Книжников' 3 times, 'медпалата' 5 times"},
    {"check": "forbidden_characters_absent", "result": "PASS", "details": "No mentions of 'Себастьян' or 'Грей'"},
    {"check": "required_characters_present", "result": "PASS", "details": "Found 'Алекса' 12 times, 'Реджинальд' 8 times"},
    {"check": "mechanics_match", "result": "PASS", "details": "Found 'автоматически' + 'компенсация', no 'подарок'"},
    {"check": "scope_boundaries", "result": "PASS", "details": "No mentions of scene 0203 or 0205 content"}
  ],
  "recommendation": "Proceed to full validation"
}
```

**FAIL Case:**
```json
// File: workspace/validation/scene-{ID}-fast-compliance-result.json
{
  "status": "FAIL",
  "scene_id": "0204",
  "draft_path": "...",
  "timestamp": "2025-10-31T10:47:00Z",
  "violations": [
    {
      "check": "location_match",
      "result": "FAIL",
      "severity": "HIGH",
      "found": "больница (line 45), медицинский центр (line 78)",
      "required": "Башня Книжников медпалата",
      "message": "Draft uses forbidden location terms"
    },
    {
      "check": "forbidden_characters_absent",
      "result": "FAIL",
      "severity": "CRITICAL",
      "found": "Себастьян Грей entered (line 120)",
      "required": "Себастьян must NOT appear (removed per plan)",
      "message": "Removed character present in draft"
    }
  ],
  "recommendation": "STOP full validation. Regenerate with corrected constraints.",
  "retry_guidance": {
    "emphasis_needed": [
      "Location: Башня Книжников (NOT больница)",
      "Character: Себастьян Грей MUST NOT APPEAR"
    ]
  }
}
```

#### Logic

**Fast Checks (optimized for speed):**

1. **Location Match Check** (<5 seconds)
   - Required: Extract required location from constraints
   - Forbidden: Extract forbidden locations
   - Draft scan: Search for location terms (case-insensitive, partial matches)
   - PASS if: Required terms found AND forbidden terms NOT found
   - FAIL if: Forbidden terms found OR required terms absent

2. **Character Presence Check** (<5 seconds)
   - Required present: Extract from constraints
   - Required absent: Extract from constraints (especially plan removals)
   - Draft scan: Search for character names (first name, last name, nicknames)
   - PASS if: All required present AND all forbidden absent
   - FAIL if: Any forbidden character found OR any required character missing

3. **Mechanics Check** (<5 seconds)
   - Required mechanics: Extract key terms (e.g., "автоматически компенсация")
   - Forbidden mechanics: Extract terms (e.g., "личный подарок", "Алекса дарит")
   - Draft scan: Search for mechanic keywords
   - PASS if: Required terms found in proximity AND forbidden patterns absent
   - FAIL if: Forbidden patterns found OR required mechanics unclear

4. **Scope Boundaries Check** (<10 seconds)
   - Forbidden content: Identify content markers from other scenes (e.g., "Диана" from scene 0203)
   - Draft scan: Search for out-of-scope content markers
   - PASS if: No forbidden content markers found
   - FAIL if: Content from other scenes detected

5. **Word Count Check** (<5 seconds)
   - Count words in draft
   - Compare to target range (e.g., 1000-1100)
   - PASS if: Within range or ±10%
   - WARNING if: Outside ±10% (non-blocking, but flagged)

**Aggregation:**
- If ALL checks PASS → status: "PASS"
- If ANY check FAIL → status: "FAIL", collect violations
- Generate retry_guidance for failed checks (what to emphasize in regeneration)

#### Constraints Applied

- **Rule 4 (Fail-Fast)**: This agent IS the fail-fast mechanism for generated drafts
- **Speed Priority**: Sacrifices deep analysis for speed (<30 sec target)
- **Observability**: Logs all checks performed for debugging
- **False Negative Tolerance**: Okay to miss subtle issues (full validation catches those), but MUST catch obvious violations

#### Performance Target

- **Speed**: <30 seconds for 1000-1500 word draft
- **Detection Rate**: >90% for obvious violations (wrong location, forbidden character, wrong mechanics)
- **False Positive Rate**: <10% (avoid blocking compliant drafts)

#### Retry Integration

When fast-checker returns FAIL:
- Coordinator reads retry_guidance
- Enhances constraints for prose-writer retry (Attempt 2 or 3)
- Emphasizes violated constraints in regeneration prompt
- Does NOT show failed draft to user (internal retry)

#### Limitations (By Design)

**What fast-checker DOES check:**
- Surface-level keyword matching
- Presence/absence of required/forbidden elements
- Basic scope boundaries

**What fast-checker DOES NOT check:**
- Deep lore accuracy (world-lorekeeper handles this)
- Canon timeline consistency (chronicle-keeper handles this)
- Character emotional state (character-state handles this)
- Dialogue quality (dialogue-analyst handles this)
- Subtle plot inconsistencies (plot-architect handles this)

Fast-checker is intentionally shallow to be fast. Full validation catches deeper issues.

---

### 2.6 validation-aggregator

**Type**: New Agent (or Enhanced Existing if aggregator exists)
**Role**: Parallel validation coordinator and results aggregator

#### Purpose
Coordinate execution of 7 validation agents in parallel, collect results, and produce unified validation report for user transparency.

#### Single Responsibility
Validation orchestration and aggregation ONLY. Does NOT perform validation itself - delegates to specialized validators and synthesizes results.

#### Inputs

- **draft_path** (string): Path to scene draft
- **blueprint_path** (string): Original blueprint for reference
- **scene_id** (string): Scene identifier
- **context_references** (object): Paths to context files for validators
  ```json
  {
    "world_bible": "context/world-bible/",
    "canon_timeline": "context/canon-levels/",
    "character_sheets": "context/characters/",
    "plot_graph": "context/plot-graph/"
  }
  ```

#### Outputs

**final-validation-report.json:**
```json
{
  "scene_id": "0204",
  "draft_path": "...",
  "timestamp": "2025-10-31T10:50:00Z",
  "overall_status": "PASS",
  "validators_run": 7,
  "validators_passed": 7,
  "validators_failed": 0,
  "execution_time_seconds": 65,
  "results": [
    {
      "validator": "world-lorekeeper",
      "status": "PASS",
      "warnings": 0,
      "errors": 0,
      "message": "All world mechanics correctly represented"
    },
    {
      "validator": "canon-guardian",
      "status": "PASS",
      "warnings": 0,
      "errors": 0,
      "message": "No canon violations detected"
    },
    {
      "validator": "character-state",
      "status": "PASS",
      "warnings": 1,
      "errors": 0,
      "message": "Character states consistent",
      "warnings_details": ["Алекса's emotional state could be more nuanced (suggestion, not blocker)"]
    },
    {
      "validator": "plot-architect",
      "status": "PASS",
      "warnings": 0,
      "errors": 0,
      "message": "Plot progression aligns with blueprint"
    },
    {
      "validator": "scene-structure",
      "status": "PASS",
      "warnings": 0,
      "errors": 0,
      "message": "Beat structure matches blueprint"
    },
    {
      "validator": "chronicle-keeper",
      "status": "PASS",
      "warnings": 0,
      "errors": 0,
      "message": "Chronology consistent with timeline"
    },
    {
      "validator": "dialogue-analyst",
      "status": "PASS",
      "warnings": 2,
      "errors": 0,
      "message": "Dialogue quality acceptable",
      "warnings_details": [
        "Reginald's dialogue could reflect more emotional depth (suggestion)",
        "Consider varying dialogue tags (suggestion)"
      ]
    }
  ],
  "blocking_issues": [],
  "non_blocking_warnings": [
    "Алекса's emotional state could be more nuanced",
    "Reginald's dialogue could reflect more emotional depth",
    "Consider varying dialogue tags"
  ],
  "recommendation": "APPROVE - Draft meets all critical requirements. Warnings are suggestions for polish, not blockers."
}
```

**FAIL Case** (if any validator returns blocking errors):
```json
{
  "overall_status": "FAIL",
  "validators_passed": 6,
  "validators_failed": 1,
  "results": [
    // ... 6 PASS results ...
    {
      "validator": "canon-guardian",
      "status": "FAIL",
      "warnings": 0,
      "errors": 2,
      "message": "Canon violations detected",
      "errors_details": [
        "Compensation system described incorrectly: draft says 'manual approval required', canon states 'automatic'",
        "Timeline conflict: scene takes place on Day 5, but previous scene was Day 7"
      ]
    }
  ],
  "blocking_issues": [
    "Canon violation: Compensation system mechanics incorrect",
    "Timeline conflict detected"
  ],
  "recommendation": "DO NOT APPROVE - Fix blocking issues and regenerate"
}
```

#### Logic

1. **Prepare Validator Inputs**
   - For each validator, prepare input package:
     - draft_path
     - Relevant context paths (world-lorekeeper gets world-bible, etc.)
     - scene_id
   - Create isolated workspace for each validator

2. **Spawn Parallel Validators**
   - Invoke 7 validators concurrently (NOT sequentially):
     1. world-lorekeeper
     2. canon-guardian
     3. character-state
     4. plot-architect
     5. scene-structure
     6. chronicle-keeper
     7. dialogue-analyst
   - Set timeout: 120 seconds per validator (2 minutes)

3. **Collect Results**
   - Wait for all validators to complete or timeout
   - Read each validator's output file: validation-result.json
   - Parse status: PASS/FAIL
   - Parse warnings and errors

4. **Aggregate Status**
   - IF any validator status == "FAIL" → overall_status = "FAIL"
   - IF all validators status == "PASS" → overall_status = "PASS"
   - Collect all blocking_issues (errors)
   - Collect all non_blocking_warnings (warnings)

5. **Generate Recommendation**
   - PASS + no warnings → "APPROVE - Excellent quality"
   - PASS + warnings → "APPROVE - Draft meets requirements. Warnings are suggestions."
   - FAIL → "DO NOT APPROVE - Fix blocking issues: [list]"

6. **Save Report**
   - Write final-validation-report.json to workspace/validation/
   - Return path to coordinator

#### Constraints Applied

- **Parallelization**: All 7 validators run concurrently (minimize total time)
- **Isolation**: Each validator gets isolated context (no shared state)
- **Timeout Handling**: If validator times out, mark as WARNING (not FAIL, unless critical)
- **Observability**: Logs start/end time for each validator, total execution time

#### Performance Target

- **Speed**: 60-90 seconds total (limited by slowest validator, NOT sum of all)
- **Reliability**: 100% result collection (handle timeouts gracefully)
- **Clarity**: Report is human-readable and actionable

#### Validator Specifications (Existing Agents)

**These agents already exist in the system. validation-aggregator invokes them:**

1. **world-lorekeeper**: Validates world mechanics, magic systems, technology
2. **canon-guardian**: Validates adherence to established canon (levels 0-4)
3. **character-state**: Validates character knowledge, emotional states, capabilities
4. **plot-architect**: Validates plot progression, cause/effect, setup/payoff
5. **scene-structure**: Validates beat structure, pacing, scene goals
6. **chronicle-keeper**: Validates timeline, chronology, continuity
7. **dialogue-analyst**: Validates dialogue quality, character voice, subtext

**Aggregator does NOT modify these agents** - only invokes them in parallel and collects results.

#### Error vs. Warning Distinction

**ERROR (blocking):**
- Canon violation (contradicts established lore)
- Timeline conflict (chronology broken)
- Character knowledge violation (character knows something they shouldn't)
- Plot hole (cause without effect, or effect without cause)

**WARNING (non-blocking, suggestions):**
- Dialogue could be improved
- Emotional depth could be enhanced
- Pacing could be tighter
- Sensory details could be richer

Aggregator preserves this distinction in final report.

---

## 3. Data Flow Summary

### 3.1 Artifact Lifecycle

| Artifact | Created By | Consumed By | Lifetime | Size |
|----------|------------|-------------|----------|------|
| `scene-{ID}-blueprint.md` | Planning Workflow (pre-existing) | blueprint-validator, prose-writer | Permanent | 3-5 KB |
| `constraints-list.json` | blueprint-validator | verification-planner, prose-writer, fast-checker | Run | 1-2 KB |
| `validation-errors.json` | blueprint-validator (if FAIL) | generation-coordinator (shown to user) | Run | <1 KB |
| `verification-plan.md` | verification-planner | User (displayed by coordinator) | Run | 2-3 KB |
| `verified-plan.json` | generation-coordinator (after approval) | prose-writer | Run | 1-2 KB |
| `scene-{ID}-draft.md` | prose-writer | fast-checker, validators, USER (final) | Permanent | 5-7 KB |
| `compliance-echo.json` | prose-writer | generation-coordinator (for logging) | Run | <1 KB |
| `fast-compliance-result.json` | fast-checker | generation-coordinator (retry logic) | Run | <1 KB |
| `validation-result.json` (x7) | Each validator | validation-aggregator | Run | <1 KB each |
| `final-validation-report.json` | validation-aggregator | generation-coordinator (final output) | Run | 2-3 KB |

**Total Artifacts per Run**: ~10-15 files (most <2 KB)
**Storage**: workspace/generation-runs/{timestamp}-scene-{ID}/
**Cleanup**: Run artifacts deleted after 7 days (configurable)
**Permanent Artifacts**: blueprint, draft (final output)

### 3.2 Context Window Management

**Problem**: Typical scene generation involves:
- Blueprint: 3000 tokens
- Previous scene: 1500 tokens
- Character sheets: 2000 tokens
- World mechanics: 1000 tokens
- Generated draft: 1500 tokens
- Validation results: 500 tokens
- **Total**: ~10,000 tokens

**FEAT-0001 Solution**:
- Agents receive FILE PATHS, not content (10 tokens vs 3000 tokens)
- prose-writer receives only 4 files: blueprint, verified-plan, previous scene, POV character (NOT full world-bible)
- Validators receive only relevant context (world-lorekeeper gets world-bible excerpt, not character sheets)
- Coordinator sees summaries, not full texts
- Full draft NEVER returned in agent response (saved to file)

**Result**: Context window usage reduced by ~60-70%

### 3.3 Parallel vs. Sequential Execution

**Sequential Steps** (must wait for previous):
1. Step 1 → Step 2 (can't validate blueprint before finding it)
2. Step 2 → Step 3 (can't create plan before extracting constraints)
3. Step 3 → Step 4 (can't generate before approval)
4. Step 4 → Step 5 (can't check compliance before generation)
5. Step 5 → Step 6 (can't deep-validate before fast-check passes)

**Parallel Steps** (can run concurrently):
- Step 6: All 7 validators run in parallel (60-90 sec total, NOT 7x60 = 420 sec)

**Total Time Breakdown:**
- Sequential portion: ~5-6 minutes (Steps 1-5, including generation)
- Parallel portion: ~1-1.5 minutes (Step 6)
- **Total**: 6-7.5 minutes (vs. 10-15 minutes if all sequential)

---

## 4. Next: Part 2

### Part 2 Will Cover:

1. **Constraint Enforcement Implementation**
   - Detailed prompt templates for each agent
   - Constraint isolation blocks (Rule 1)
   - Constraint repetition patterns (Rule 3)
   - Constraint echo requirements (Rule 7)

2. **Error Handling & Retry Logic**
   - Retry orchestration (max 3 attempts)
   - Enhanced constraint emphasis (Attempt 2, 3)
   - Failure escalation (3 fails → human intervention)
   - Timeout handling

3. **Artifact Format Specifications**
   - JSON schemas for all artifacts
   - Markdown templates for plans/reports
   - Validation formats (PASS/FAIL structures)

4. **Integration with Existing Workflows**
   - How FEAT-0001 fits into current Generation Workflow
   - Backward compatibility with existing blueprints
   - Migration plan (handling old versioned files)

5. **Testing Strategy**
   - Unit tests for each agent
   - Integration tests for full workflow
   - Success metrics tracking

6. **Implementation Roadmap**
   - Phased rollout plan
   - Risk mitigation strategies
   - Rollback procedures

---

## Appendix A: Decision Points & Rationale

### A.1 Why New Coordinator vs. Extending Existing?

**Decision**: Create new `generation-coordinator` agent
**Rationale**:
- Current generation flow may not have explicit orchestrator
- Coordinator needs state management across 7 steps (retry counts, approval status)
- Clean separation of concerns: coordination vs. execution
- Easier testing and debugging

**Alternative Considered**: Extend existing director agent
**Rejected Because**: Director may handle multiple workflows; isolating generation coordination reduces coupling

### A.2 Why 3-Step Constraint Repetition?

**Decision**: Repeat constraints at start, inline, and end
**Rationale**:
- Research (CoS/LIFT-COT patterns) shows repetition improves adherence
- LLMs can "forget" constraints in long prompts (attention dilution)
- 3x repetition: diminishing returns after that

**Alternative Considered**: 5x repetition
**Rejected Because**: Excessive repetition wastes tokens, 3x sufficient per Anthropic guidelines

### A.3 Why Fast-Checker Before Full Validation?

**Decision**: Add fast-checker as Step 5 (before Step 6 full validation)
**Rationale**:
- Fail-fast principle: catch obvious errors in 30 sec vs. waiting 90 sec for full validation
- Enables auto-retry without user seeing failed attempts
- Saves tokens/time on fundamentally broken drafts

**Alternative Considered**: Only full validation (skip fast-checker)
**Rejected Because**: User would see failed drafts, breaking user journey requirement "user does NOT see failed attempts"

### A.4 Why File-Based Artifacts vs. In-Memory?

**Decision**: All artifacts saved to files in workspace/
**Rationale**:
- Anthropic best practice for >100 lines content
- Prevents context window overflow
- Enables observability (artifacts can be inspected for debugging)
- Supports retry logic (previous attempts preserved)

**Alternative Considered**: Pass data in prompts/responses
**Rejected Because**: Context window limits, difficult debugging, violates Anthropic guidelines

### A.5 Why Standard File Naming vs. Version Suffixes?

**Decision**: ONE canonical file with standard name (plan.md, scene-{ID}-blueprint.md), versions tracked via backups/
**Rationale**:
- Multiple files with different names caused ambiguity (root cause of original problem)
- Single source of truth principle
- Agents never guess which file is current
- Timestamped backups preserve history without confusion

**Alternative Considered**: Version suffixes in file names (plan-v2.md, plan-v3.md)
**Rejected Because**: Agents don't know which version is current, leads to reading wrong files

---

## Appendix B: Risk Analysis

### B.1 Performance Risks

**Risk**: Workflow takes >10 minutes (user expectation is 5-8 min)
**Mitigation**:
- Parallel validation (Step 6)
- Fast-checker timeout: 30 sec hard limit
- prose-writer timeout: 6 min hard limit
- Monitoring: log execution times per step

**Risk**: Validator timeouts cause incomplete reports
**Mitigation**:
- 120 sec timeout per validator
- Timeout treated as WARNING, not FAIL (unless critical validator)
- Aggregator proceeds even if 1-2 validators timeout

### B.2 Quality Risks

**Risk**: Fast-checker false positives (blocks compliant drafts)
**Mitigation**:
- Target <10% false positive rate
- Manual review of first 10 scenes to tune detection
- User can override fast-checker (with warning) if needed

**Risk**: prose-writer still ignores constraints despite FEAT-0001
**Mitigation**:
- 3 retry attempts with escalating emphasis
- After 3 fails, human review required (fail-safe)
- Metrics tracking: monitor constraint compliance rate

### B.3 User Experience Risks

**Risk**: User overwhelmed by verification plan details
**Mitigation**:
- Plan format designed for readability (emojis, sections, whitespace)
- User can approve with just "Y" (minimal friction)
- Modifications optional, not required

**Risk**: User frustrated by multi-step approval process
**Mitigation**:
- Verification step typically <30 sec (fast review)
- User sees plan ONCE per scene (not per attempt)
- Auto-retry happens without user re-approval

### B.4 Technical Risks

**Risk**: Artifact storage fills disk space
**Mitigation**:
- Run artifacts deleted after 7 days
- Total storage per run: ~20-30 KB (minimal)
- Monitoring: alert if workspace/ exceeds 100 MB

**Risk**: Parallel validators compete for resources
**Mitigation**:
- Each validator isolated (no shared state)
- System supports 6-7 parallel Claude calls (per Anthropic limits)
- Fallback: sequential execution if parallel fails

**Risk**: Multiple versioned files cause confusion
**Mitigation**:
- blueprint-validator enforces single-file rule
- Agents error immediately if multiple files detected
- Clear migration path for old versioned files
- Automatic backup creation before modifications

---

**END OF PART 1**

**Next Steps**: Create TECHNICAL_DESIGN_PART2.md covering constraint implementation, error handling, artifact schemas, integration, and testing strategy.
