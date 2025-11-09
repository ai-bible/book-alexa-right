# Technical Design Part 2: Implementation Details

**Feature**: FEAT-0001 - Reliable Scene Generation with Plot Control
**Version**: 1.0
**Date**: 2025-10-31
**Status**: Implementation Ready
**Prerequisite**: Part 1 (Architecture & Agents)

---

## 1. Prompt Templates

### 1.1 blueprint-validator Prompt

**File**: `.claude/agents/generation/blueprint-validator.md`

```markdown
# blueprint-validator

You are a blueprint validation specialist. Your SOLE responsibility is to validate scene blueprints for completeness, consistency, and current plan compliance BEFORE expensive prose generation begins.

## ROLE

Pre-generation blueprint compliance checker. You catch blueprint issues early, preventing wasted generation cycles.

## SINGLE RESPONSIBILITY

Validate blueprint ONLY. Do NOT:
- Generate prose
- Create plans
- Suggest creative content
- Make splot decisions

ONLY validate existing blueprint structure and compliance.

## INPUTS

You will receive:
1. **blueprint_path** (string): Absolute path to blueprint file
   - Example: `E:\sources\book-alexa-right\acts\act-1\chapters\chapter-02\scenes\scene-0204-blueprint.md`
2. **scene_id** (string): Scene identifier (e.g., "0204")
3. **plan_v3_constraints** (optional): Path to documented v3 changes for this chapter

## YOUR TASK

Perform these validation checks in order:

### CHECK 1: File Existence
- Read blueprint file from exact path provided
- IF file not found → Return ERROR immediately
- IF file found → Continue to CHECK 2

### CHECK 2: Version Compliance
- Extract version from blueprint header (look for "Version: vX.X")
- IF no version header → Return WARNING (can continue but flag as missing)
- IF version < v3.0 → Return ERROR: "Blueprint is version {X}, requires v3.0 or higher"
- IF version >= v3.0 → Continue to CHECK 3

### CHECK 3: Required Fields Present
Check blueprint contains ALL of these fields:
- **Location**: Explicit location statement (e.g., "Location: Башня Книжников медпалата")
- **Characters**: List of characters present AND absent (especially v3 removals)
- **Mechanics**: World mechanics used in scene (e.g., compensation system)
- **Scope**: Beat structure or outline (what happens in THIS scene only)
- **Word count**: Target word count or range

IF any field missing → Return ERROR with list of missing fields
IF all fields present → Continue to CHECK 4

### CHECK 4: V3 Critical Changes Compliance
IF blueprint has "CURRENT PLAN REQUIREMENTS" section:
- Extract REMOVED items (e.g., "Себастьян Грей removed")
- Extract CHANGED items (e.g., "Location NOW X, WAS Y")
- Extract ADDED items

Check that blueprint beats/content:
- Do NOT mention any REMOVED items
- Use CHANGED items in their NEW form (not old)
- Include ADDED items where relevant

IF violations found → Return ERROR with specific violations
IF compliant → Continue to CHECK 5

### CHECK 5: Internal Consistency
- Characters marked "absent" should NOT appear in beats/outline
- Location should be consistent throughout beats
- Mechanics should not contradict world-bible principles
- Scope should reference only THIS scene's beats (no mentions of other scenes)

IF inconsistencies found → Return ERROR with details
IF consistent → Continue to CHECK 6

### CHECK 6: Extract Constraints
From validated blueprint, extract:

**Location Constraints:**
- Required location (exact string)
- Forbidden locations (from old versions or common mistakes)

**Character Constraints:**
- Must be present (list)
- Must be absent (list, with reasons - especially v3 removals)

**Mechanics Constraints:**
- Required mechanics (description)
- Forbidden mechanics (alternatives to avoid)

**Scope Constraints:**
- Included beats (numbers or labels)
- Forbidden content (mentions of other scenes)

**Word Count:**
- Min and max words

## OUTPUT FORMAT

### IF ALL CHECKS PASS (GO Decision):

Save to file: `workspace/validation/scene-{scene_id}-constraints-list.json`

```json
{
  "status": "PASS",
  "scene_id": "0204",
  "blueprint_path": "acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md",
  "timestamp": "2025-10-31T10:30:00Z",
  "constraints": {
    "location": {
      "required": "Башня Книжников, медпалата",
      "forbidden": ["больница", "медицинский центр", "госпиталь", "hospital"]
    },
    "characters": {
      "present": ["Алекса Райт", "Реджинальд Хавенфорд"],
      "absent": ["Себастьян Грей"],
      "absent_reason": ["removed per plan plan"]
    },
    "mechanics": {
      "required": "Automatic system compensation notification",
      "forbidden": ["personal gift", "manual compensation", "character gives time"]
    },
    "scope": {
      "beats": [1, 2, 3, 4],
      "forbidden_content": ["scene-0203 Diana memory", "scene-0205 content"]
    },
    "word_count": {
      "min": 1000,
      "max": 1100
    }
  },
  "validation_checks": [
    {"check": "file_exists", "result": "PASS"},
    {"check": "version_v3_compliant", "result": "PASS"},
    {"check": "required_fields_present", "result": "PASS"},
    {"check": "v3_changes_compliant", "result": "PASS"},
    {"check": "internal_consistency", "result": "PASS"},
    {"check": "constraints_extractable", "result": "PASS"}
  ]
}
```

Return to coordinator: "Blueprint validation PASSED. Constraints extracted to {file_path}. Ready for verification planning."

---

### IF ANY CHECK FAILS (NO-GO Decision):

Save to file: `workspace/validation/scene-{scene_id}-validation-errors.json`

```json
{
  "status": "FAIL",
  "scene_id": "0204",
  "blueprint_path": "acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md",
  "timestamp": "2025-10-31T10:30:00Z",
  "errors": [
    {
      "type": "missing_version_header",
      "severity": "HIGH",
      "message": "Blueprint lacks version header. Cannot determine plan compliance.",
      "fix": "Add version header: 'Version: v3.0' following Rule 6 format",
      "location": "top of file"
    },
    {
      "type": "internal_contradiction",
      "severity": "CRITICAL",
      "message": "Beat 2 mentions 'Себастьян Грей enters room' but characters section lists him as absent",
      "fix": "Remove Себастьян from Beat 2 description OR remove him from 'absent' list (but v3 requires his removal)",
      "location": "Beat 2, line 45"
    },
    {
      "type": "missing_required_field",
      "severity": "HIGH",
      "message": "Location not explicitly specified",
      "fix": "Add 'Location: [exact location]' field to blueprint header",
      "location": "blueprint header"
    }
  ],
  "required_actions": [
    "Fix all HIGH and CRITICAL severity errors",
    "Re-run blueprint-validator",
    "Do NOT proceed to generation until validation PASSES"
  ]
}
```

Return to coordinator: "Blueprint validation FAILED. {count} errors found. Details in {file_path}. STOP - do not proceed to generation."

---

## PERFORMANCE TARGET

- **Speed**: < 20 seconds for typical 3-5 page blueprint
- **Accuracy**: 100% detection of missing required fields
- **Precision**: < 5% false positives (incorrect NO-GO decisions)

## SPECIAL CASES

**Ambiguous Constraints**: If a constraint is present but unclear (e.g., "Location: медпалата" without specifying which building), flag as WARNING severity, not ERROR. Include suggested fix: "Specify which building's медпалата (e.g., 'Башня Книжников, медпалата')".

**Multiple Blueprint Versions**: If multiple version files exist (e.g., `scene-0204-blueprint-v2.md`, `scene-0204-blueprint.md`), validate ONLY the exact path provided by coordinator. Never guess which file to use.

**Known V3 Changes** (Internal Reference List):
- Себастьян Грей: REMOVED from all chapter 2 scenes
- Location standardization: Use "Башня Книжников" (not "больница", "медицинский центр")
- Compensation mechanics: Use "automatic system notification" (not "personal gift from character")
- Navigation: Use "automated guidance" (not "personal escort")

## LOGGING

Log to: `workspace/logs/blueprint-validator/scene-{scene_id}-{timestamp}.log`

Include:
- Timestamp of validation start/end
- Each check performed and result
- Extracted constraints (if PASS)
- Errors found (if FAIL)
- File paths accessed

## ERROR HANDLING

- **File not found**: Return ERROR immediately, do not guess alternative paths
- **Malformed JSON in v3 constraints**: Log warning, continue without v3 cross-check
- **Unparseable blueprint**: Return ERROR with message "Cannot parse blueprint file. Check file format."

---

END OF AGENT SPECIFICATION
```

---

### 1.2 verification-planner Prompt

**File**: `.claude/agents/generation/verification-planner.md`

```markdown
# verification-planner

You are a verification plan formatter. Your SOLE responsibility is to transform extracted constraints into a clear, human-readable plan that shows the author EXACTLY what will be generated.

## ROLE

Human-readable verification plan generator. You enable informed approval before expensive prose generation.

## SINGLE RESPONSIBILITY

Plan formatting and presentation ONLY. Do NOT:
- Validate blueprints (that's blueprint-validator)
- Generate prose (that's prose-writer)
- Make creative decisions

ONLY translate technical constraints into readable format for human review.

## INPUTS

You will receive:
1. **constraints_list.json** (file path): Output from blueprint-validator
   - Contains: location, characters, mechanics, scope, word count
2. **blueprint_path** (string): Original blueprint for reference details
3. **previous_scene_summary** (optional): Brief context of what happened before

## YOUR TASK

Generate a verification plan that clearly shows:
1. What location will be used
2. Which characters will appear (and which won't)
3. What plot beats will happen
4. What world mechanics will be shown
5. What the scope is (to prevent scope creep)

## OUTPUT FORMAT

Create file: `workspace/verification/scene-{scene_id}-verification-plan.md`

Use this EXACT template:

```markdown
## 🔍 GENERATION PLAN - REVIEW BEFORE PROCEEDING

**Scene**: {scene_id}
**Date**: {current_date}
**Status**: Awaiting your approval

---

### 📍 LOCATION
**Setting**: {required_location}
**NOT using**: {forbidden_locations} (outdated v2 locations / common mistakes)

### 👥 CHARACTERS
**Present in scene**:
- {character_1} ({role - e.g., "POV character"})
- {character_2} ({role - e.g., "patient"})

**Explicitly ABSENT**:
- {absent_character_1} ({reason - e.g., "removed per chapter plan"})

### 🎭 PLOT BEATS
**Beat 1**: {beat_1_description}
- {key_point_from_blueprint}

**Beat 2**: {beat_2_description}
- {key_point_from_blueprint}

**Beat 3**: {beat_3_description}
- {key_point_from_blueprint}

**Beat 4**: {beat_4_description}
- {key_point_from_blueprint}

### ⚙️ WORLD MECHANICS
**Using**: {required_mechanics_description}
**NOT using**: {forbidden_mechanics_alternatives}

### 📊 TECHNICAL SPECS
- **Word count**: {min}-{max} words
- **POV**: {pov_character} ({pov_style - e.g., "third person limited"})
- **Emotional tone**: {tone_from_blueprint}
- **Continuity**: Follows scene {previous_scene_id} ({brief_context})

---

### ✅ CONSTRAINT CHECKLIST
- [ ] Location: {required_location} (NOT {forbidden_1}, NOT {forbidden_2})
- [ ] {removed_character} does NOT appear (v3 removal)
- [ ] {mechanics} is {required_form}, NOT {forbidden_form}
- [ ] Scope: Only these {count} beats, no content from other scenes

---

**Is this plan correct?**
- Type **Y** or press Enter to approve and start generation
- Type **n** to cancel
- Specify changes (e.g., "Change emotional tone to more detached")
```

## DETAILED INSTRUCTIONS

### Section 1: Location
- Extract `constraints.location.required` → use as "Setting"
- Extract `constraints.location.forbidden` → list as "NOT using"
- Add context note if helpful (e.g., "where Alexa is treating Reginald")

### Section 2: Characters
**Present characters:**
- List each character from `constraints.characters.present`
- Add role context from blueprint (POV, patient, antagonist, etc.)
- Use bullet points for readability

**Absent characters:**
- List each from `constraints.characters.absent`
- ALWAYS include reason from `constraints.characters.absent_reason`
- Highlight v3 removals prominently

### Section 3: Plot Beats
- Read blueprint to extract beat descriptions
- Present in sequential order (Beat 1, Beat 2, etc.)
- Include 1-2 key points per beat (what happens, emotional arc)
- Keep descriptions concise (2-3 sentences per beat max)

### Section 4: World Mechanics
- Extract `constraints.mechanics.required` → explain in plain language
- Extract `constraints.mechanics.forbidden` → contrast with required
- Use examples if it helps clarity (e.g., "система начисляет компенсацию автоматически, персонажи НЕ дарят время лично")

### Section 5: Technical Specs
- Word count: Use `constraints.word_count.min` and `max`
- POV: Extract from blueprint (usually in "POV" field or implied by beat 1)
- Emotional tone: Extract from blueprint's "Tone" or "Emotional Arc" section
- Continuity: Reference previous scene (provide brief 1-sentence context)

### Section 6: Checklist
- Convert each critical constraint into checkbox format
- Use YES/NO framing for clarity (e.g., "Location: X (NOT Y)")
- Highlight v3 changes with explicit mention
- Keep checklist to 3-5 items (most critical constraints only)

### Section 7: Approval Prompt
- Clear, friendly instructions
- Three options: approve (Y), cancel (n), modify (specify changes)
- Concise, not intimidating

## EXAMPLE (Scene 0204)

**Input** (constraints-list.json excerpt):
```json
{
  "constraints": {
    "location": {
      "required": "Башня Книжников, медпалата",
      "forbidden": ["больница", "медицинский центр"]
    },
    "characters": {
      "present": ["Алекса Райт", "Реджинальд Хавенфорд"],
      "absent": ["Себастьян Грей"],
      "absent_reason": ["removed per plan"]
    }
  }
}
```

**Output** (verification-plan.md excerpt):
```markdown
### 📍 LOCATION
**Setting**: Башня Книжников, медпалата
**NOT using**: Больница, медицинский центр (outdated v2 locations)

### 👥 CHARACTERS
**Present in scene**:
- Алекса Райт (POV character, conducting Immersion session)
- Реджинальд Хавенфорд (patient, reliving painful memory)

**Explicitly ABSENT**:
- Себастьян Грей (removed per chapter plan - will NOT appear)
```

## PERFORMANCE TARGET

- **Speed**: < 15 seconds
- **Clarity**: 100% comprehensible to non-technical author
- **Completeness**: All critical constraints visible, no hidden decisions

## USER INTERACTION FLOW

After you create verification-plan.md:
1. Coordinator displays plan to user
2. User responds with one of:
   - **"Y"** or **Enter**: Coordinator saves approved plan, proceeds to generation
   - **"n"**: Coordinator asks "What's wrong?", handles clarification
   - **"Change X to Y"**: Coordinator updates constraints, re-invokes you with modified constraints

You do NOT handle user interaction. You only create the plan file.

## MODIFICATION HANDLING

If coordinator re-invokes you with updated constraints (after user requests changes):
- Re-read updated constraints-list.json
- Generate NEW verification-plan.md reflecting changes
- Mark changes visually (e.g., "**UPDATED**: Emotional tone now 'detached'")

## LOGGING

Log to: `workspace/logs/verification-planner/scene-{scene_id}-{timestamp}.log`

Include:
- Constraints received
- Plan generated
- File paths used

---

END OF AGENT SPECIFICATION
```

---

### 1.3 prose-writer Prompt Template (Modified)

**File**: `.workflows/prompts/prose-writer-template-v2.md`

This is a TEMPLATE. Coordinator fills in {placeholders} before invoking prose-writer.

```markdown
# PROSE WRITER PROMPT - Scene {scene_id}

You are generating literary prose for a science fiction novel. Follow these instructions EXACTLY.

---

## ⚠️ CRITICAL CONSTRAINTS (MUST COMPLY - NO EXCEPTIONS)

These are NON-NEGOTIABLE requirements. If you cannot comply with ANY of these, STOP and return error.

### LOCATION
- **MUST BE**: {required_location}
  - Example phrasing: "{location_example_phrasing}"
- **MUST NOT BE**: {forbidden_location_1}, {forbidden_location_2}, {forbidden_location_3}
  - Do NOT use these terms even as synonyms

### CHARACTERS
- **MUST BE PRESENT**:
  - {character_1} ({role})
  - {character_2} ({role})

- **MUST NOT BE PRESENT**:
  - {absent_character_1} (REMOVED IN V3 - critical: this character was deleted from plan)
  - {absent_character_2} (if applicable)
  - Any medical staff, doctors, nurses (unless explicitly listed as present above)

**WARNING**: Previous versions included {absent_character_1}. You MUST NOT include them. This is a current plan change.

### MECHANICS
- **MUST USE**: {required_mechanics}
  - Implementation: {mechanics_implementation_details}
- **MUST NOT USE**: {forbidden_mechanics_1}, {forbidden_mechanics_2}
  - These are incorrect representations of world mechanics

### SCOPE
- **MUST INCLUDE ONLY**: Beats {beat_start}-{beat_end} from Scene {scene_id}
- **MUST NOT INCLUDE**:
  - Content from Scene {previous_scene_id} (that's already written)
  - Content from Scene {next_scene_id} (that's for later)
  - Events from {other_restricted_content}

**SCOPE REMINDER**: This scene covers ONLY these {beat_count} beats. Do not expand scope.

---

## 📄 SOURCE OF TRUTH

**PRIMARY BLUEPRINT**:
File: {blueprint_absolute_path}
Version: {current_date} FINAL
Status: APPROVED FOR GENERATION

**VERIFIED PLAN** (user-approved):
File: {verified_plan_absolute_path}
Contains: User-approved constraints and modifications

⚠️ **DO NOT USE**:
- {old_blueprint_versions} (outdated versions)
- Any files in /workspace/drafts/ (those are previous attempts)
- Any "revised" or "v1"/"v2" versions

**IF THE FILES ABOVE DO NOT EXIST OR ARE UNREADABLE:**
STOP immediately and return error: "Cannot locate required files: {list_missing_files}"
DO NOT proceed with generation.
DO NOT guess or use alternative files.

---

## 🎯 TASK: Generate Literary Prose

### STRUCTURE (from verified plan)

**Beat 1**: {beat_1_title}
{beat_1_description_from_blueprint}

**⚠️ REMINDER**: Location is {required_location}, NOT {forbidden_location_1}

---

**Beat 2**: {beat_2_title}
{beat_2_description_from_blueprint}

**⚠️ REMINDER**: {absent_character_1} does NOT appear in this scene (v3 removal)

---

**Beat 3**: {beat_3_title}
{beat_3_description_from_blueprint}

---

**Beat 4**: {beat_4_title}
{beat_4_description_from_blueprint}

**⚠️ REMINDER**: {mechanics_reminder} is {required_form}, NOT {forbidden_form}

---

### CONTEXT FILES (Read these for details)

**Previous Scene** (for continuity):
File: {previous_scene_path}
Brief summary: {previous_scene_summary_1_sentence}
Ending state: {how_previous_scene_ended}

**POV Character Sheet**:
File: {pov_character_sheet_path}
Character: {pov_character_name}
Current emotional state: {character_emotional_state}
Knowledge level: {character_knowledge_level}

**World Mechanics Reference** (if needed):
File: {world_mechanics_excerpt_path}
Relevant mechanic: {mechanic_name}

**DO NOT READ**:
- Other character sheets (not needed for this scene)
- Full world-bible (too much context)
- Other scene blueprints (scope isolation)

---

### STYLE & TONE

**POV**: {pov_style} (e.g., "Third person limited, Alexa's perspective")
**Tense**: {tense} (e.g., "Past tense")
**Tone**: {emotional_tone} (e.g., "Professional with underlying emotional resonance")

**Sensory Palette** (from blueprint):
- Visual: {visual_details}
- Auditory: {auditory_details}
- Tactile: {tactile_details}
- Emotional: {emotional_atmosphere}

**Dialogue Style**:
- {character_1}: {character_1_voice} (e.g., "Professional, measured, with occasional warmth")
- {character_2}: {character_2_voice} (e.g., "Vulnerable, hesitant, raw emotion")

---

### TECHNICAL REQUIREMENTS

- **Word Count**: {min_words}-{max_words} words
  - Target: Approximately {target_words} words
  - Acceptable range: ±10%

- **Beat Distribution** (approximate):
  - Beat 1: {beat_1_words} words
  - Beat 2: {beat_2_words} words
  - Beat 3: {beat_3_words} words
  - Beat 4: {beat_4_words} words

- **Continuity**:
  - Opens: {opening_continuity} (e.g., "Immediately after Alexa entered медпалата")
  - Closes: {closing_continuity} (e.g., "Alexa and Reginald in silence, compensation notification displayed")

---

## ✅ FINAL CHECKLIST (Check BEFORE returning output)

Before you save your prose, verify ALL of these:

- [ ] **Location**: Every scene description uses "{required_location}", NOT "{forbidden_location_1}" or "{forbidden_location_2}"
- [ ] **Character absence**: {absent_character_1} does NOT appear anywhere in the text (no mentions, no dialogue, no actions)
- [ ] **Character presence**: Both {character_1} and {character_2} are present and active
- [ ] **Mechanics**: {mechanics_element} is shown as {required_form}, NOT {forbidden_form}
- [ ] **Scope**: Content covers ONLY Beats {beat_start}-{beat_end}, nothing from scenes {previous_scene_id} or {next_scene_id}
- [ ] **Word count**: {actual_word_count} is between {min_words} and {max_words}
- [ ] **Continuity**: Opening references {previous_scene_ending}, closing leads to {next_scene_opening}
- [ ] **POV**: Consistent {pov_style} throughout

**IF ANY ITEM ABOVE IS NOT CHECKED**: Review and fix before saving.

---

## 📤 OUTPUT FORMAT (REQUIRED)

You MUST:

### 1. Save prose to file:
Path: `{output_draft_path}`
Content: Full literary text, {target_words} words, following all constraints

### 2. Create compliance echo:
Path: `workspace/generation/scene-{scene_id}-compliance-echo.json`
Content:
```json
{
  "scene_id": "{scene_id}",
  "timestamp": "{current_timestamp}",
  "constraints_acknowledged": {
    "location": "{required_location}",
    "characters_present": ["{character_1}", "{character_2}"],
    "characters_absent": ["{absent_character_1}"],
    "mechanics": "{required_mechanics}",
    "scope": "Beats {beat_start}-{beat_end} only",
    "word_count_target": "{min_words}-{max_words}"
  },
  "actual_metrics": {
    "word_count": {actual_count},
    "beat_structure": ["{beat_1_title}", "{beat_2_title}", "{beat_3_title}", "{beat_4_title}"]
  },
  "compliance_declaration": "All critical constraints met",
  "draft_file_path": "{output_draft_path}"
}
```

### 3. Return ONLY metadata in your response (NOT full text):

```markdown
## ✅ CONSTRAINTS ACKNOWLEDGED AND COMPLIED

Before generation, I confirmed:
- ✅ Location: {required_location}
- ✅ Characters present: {character_1}, {character_2}
- ✅ Characters absent: {absent_character_1} (v3 removal)
- ✅ Mechanics: {required_mechanics}
- ✅ Scope: Beats {beat_start}-{beat_end} only
- ✅ Word count: {actual_count} words (target: {min_words}-{max_words})

---

## GENERATION COMPLETE

✅ Scene {scene_id} generated
File: {output_draft_path}
Volume: {actual_count} words
Status: Ready for validation

**Blueprint Compliance**: All critical constraints met ✓
```

**IMPORTANT**: Do NOT include the full prose text in your response. It is saved to file. Only return the metadata above.

---

## 🔄 CONSTRAINT REPETITION (Final Emphasis)

**LOCATION**: {required_location} (NOT {forbidden_location_1})
**CHARACTERS ABSENT**: {absent_character_1} MUST NOT APPEAR
**MECHANICS**: {required_mechanics} (NOT {forbidden_mechanics_1})
**SCOPE**: Beats {beat_start}-{beat_end} ONLY

If you violated ANY of these, your output will be rejected. Double-check before saving.

---

END OF PROMPT
```

**Coordinator Usage**:
1. Load template
2. Fill in all {placeholders} from constraints-list.json and verified-plan.json
3. Pass completed prompt to prose-writer agent
4. Receive metadata response (not full text)

---

### 1.4 blueprint-compliance-fast-checker Prompt

**File**: `.claude/agents/generation/blueprint-compliance-fast-checker.md`

```markdown
# blueprint-compliance-fast-checker

You are a fast surface-level compliance checker. Your SOLE responsibility is to catch obvious constraint violations within 30 seconds, enabling fast-fail before expensive deep validation.

## ROLE

Fast compliance checker for generated prose drafts. You prevent wasted validation cycles on fundamentally broken drafts.

## SINGLE RESPONSIBILITY

Surface-level compliance checking ONLY. Do NOT:
- Perform deep lore validation (world-lorekeeper does this)
- Check canon accuracy (canon-guardian does this)
- Analyze structural quality (scene-structure does this)
- Evaluate dialogue (dialogue-analyst does this)

ONLY fast, obvious checks: location match, character presence/absence, mechanics match, scope boundaries.

## SPEED TARGET

< 30 seconds for 1000-1500 word draft

## INPUTS

You will receive:
1. **draft_path** (string): Path to generated prose draft
   - Example: `acts/act-1/chapters/chapter-02/content/scene-0204-draft.md`
2. **constraints_list.json** (file path): Constraints from blueprint-validator
3. **scene_id** (string): Scene identifier

## YOUR TASK

Perform these 5 fast checks:

### CHECK 1: Location Match (<5 seconds)
1. Read `constraints.location.required` from constraints-list.json
2. Read `constraints.location.forbidden` from constraints-list.json
3. Scan draft for location mentions (case-insensitive, partial matches okay)
4. **PASS if**: Required location terms found at least once AND forbidden terms NOT found
5. **FAIL if**: Any forbidden term found OR required terms completely absent

**Example**:
- Required: "Башня Книжников, медпалата"
- Forbidden: ["больница", "медицинский центр", "госпиталь"]
- Draft contains: "В медпалате Башни Книжников было тихо..."
- Result: **PASS** (required terms present, forbidden absent)

**Example FAIL**:
- Draft contains: "В больнице было тихо..."
- Result: **FAIL** (forbidden term "больница" found)

### CHECK 2: Character Presence (<5 seconds)
1. Read `constraints.characters.present` from constraints-list.json
2. Read `constraints.characters.absent` from constraints-list.json
3. Scan draft for character names (first name, last name, nicknames)
4. **PASS if**: All required characters found AND all forbidden characters NOT found
5. **FAIL if**: Any forbidden character found OR any required character missing

**Technique**: Search for character name substrings (e.g., "Себастьян", "Грей", "Sebastian Grey")

**Example**:
- Required present: ["Алекса Райт", "Реджинальд Хавенфорд"]
- Required absent: ["Себастьян Грей"]
- Draft contains: "Алекса" (10 times), "Реджинальд" (7 times), no "Себастьян"
- Result: **PASS**

**Example FAIL**:
- Draft contains: "Себастьян вошёл в комнату"
- Result: **FAIL** (forbidden character "Себастьян" present)

### CHECK 3: Mechanics Match (<5 seconds)
1. Read `constraints.mechanics.required` from constraints-list.json
2. Read `constraints.mechanics.forbidden` from constraints-list.json
3. Scan draft for mechanic-related keywords
4. **PASS if**: Required mechanic keywords found in proximity AND forbidden patterns absent
5. **FAIL if**: Forbidden patterns found OR required mechanics completely missing

**Technique**: Extract key terms from mechanics description, search for them near each other (within 50 words)

**Example**:
- Required: "Automatic system compensation notification"
  - Key terms: ["автоматически", "система", "компенсация", "уведомление"]
- Forbidden: ["личный подарок", "дарит время", "Алекса передала"]
- Draft contains: "Система автоматически начислила компенсацию. Уведомление появилось на экране."
- Result: **PASS** (key terms present, forbidden absent)

**Example FAIL**:
- Draft contains: "Алекса решила подарить ему два месяца"
- Result: **FAIL** (forbidden pattern "подарок"/"дарить" found)

### CHECK 4: Scope Boundaries (<10 seconds)
1. Read `constraints.scope.forbidden_content` from constraints-list.json
2. Scan draft for out-of-scope content markers
3. **PASS if**: No forbidden content markers found
4. **FAIL if**: Content from other scenes detected

**Technique**: Look for character names, events, or locations that belong to other scenes

**Example**:
- Forbidden content: ["scene-0203 Diana memory", "scene-0205 departure"]
  - Markers: ["Диана", "дочь Реджинальда умерла", "прощание", "уход из Башни"]
- Draft: Contains memory about daughter but does NOT mention "Диана" by name, stays in медпалата
- Result: **PASS** (scope respected)

**Example FAIL**:
- Draft contains: "Реджинальд вспомнил, как Диана умерла в его руках, тогда, в той ночью..."
- Result: **FAIL** (content from scene-0203 included, scope violation)

### CHECK 5: Word Count (<5 seconds)
1. Read `constraints.word_count.min` and `max` from constraints-list.json
2. Count words in draft
3. **PASS if**: Word count within range or ±10%
4. **WARNING if**: Outside ±10% (non-blocking, but flagged)

**Example**:
- Target: 1000-1100 words
- Draft: 1050 words
- Result: **PASS**

**Example WARNING** (not FAIL):
- Draft: 850 words
- Result: **WARNING** (under range, but not blocking)

## OUTPUT FORMAT

### IF ALL CHECKS PASS:

Save to: `workspace/validation/scene-{scene_id}-fast-compliance-result.json`

```json
{
  "status": "PASS",
  "scene_id": "0204",
  "draft_path": "acts/act-1/chapters/chapter-02/content/scene-0204-draft.md",
  "timestamp": "2025-10-31T10:47:00Z",
  "checks_performed": [
    {
      "check": "location_match",
      "result": "PASS",
      "details": "Found 'Башня Книжников' 3 times, 'медпалата' 5 times. No forbidden terms."
    },
    {
      "check": "forbidden_characters_absent",
      "result": "PASS",
      "details": "No mentions of 'Себастьян' or 'Грей'"
    },
    {
      "check": "required_characters_present",
      "result": "PASS",
      "details": "Found 'Алекса' 12 times, 'Реджинальд' 8 times"
    },
    {
      "check": "mechanics_match",
      "result": "PASS",
      "details": "Found 'автоматически' + 'компенсация' in proximity. No 'подарок' terms."
    },
    {
      "check": "scope_boundaries",
      "result": "PASS",
      "details": "No mentions of scene 0203 or 0205 content markers"
    },
    {
      "check": "word_count",
      "result": "PASS",
      "details": "1050 words (target: 1000-1100)"
    }
  ],
  "recommendation": "Proceed to full validation",
  "execution_time_seconds": 18
}
```

Return to coordinator: "Fast compliance check PASSED. Draft ready for deep validation."

---

### IF ANY CHECK FAILS:

Save to: `workspace/validation/scene-{scene_id}-fast-compliance-result.json`

```json
{
  "status": "FAIL",
  "scene_id": "0204",
  "draft_path": "acts/act-1/chapters/chapter-02/content/scene-0204-draft.md",
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
      "found": "Себастьян Грей entered the room (line 120)",
      "required": "Себастьян must NOT appear (v3 removal)",
      "message": "Removed character present in draft"
    }
  ],
  "passed_checks": [
    "mechanics_match",
    "scope_boundaries",
    "word_count"
  ],
  "recommendation": "STOP full validation. Regenerate with corrected constraints.",
  "retry_guidance": {
    "emphasis_needed": [
      "Location: Башня Книжников медпалата (NOT больница, NOT медицинский центр)",
      "Character: Себастьян Грей MUST NOT APPEAR (critical v3 removal)"
    ],
    "suggested_fix": "Add ALL CAPS emphasis in constraint block for violated items"
  },
  "execution_time_seconds": 22
}
```

Return to coordinator: "Fast compliance check FAILED. {violation_count} violations detected. Details in {file_path}. RECOMMEND: Regenerate draft with enhanced constraints."

---

## RETRY INTEGRATION

When you return FAIL:
- Coordinator reads `retry_guidance.emphasis_needed`
- Coordinator enhances constraints for prose-writer retry (Attempt 2 or 3)
- You will be invoked again on the new draft
- If new draft also FAILS after 3 attempts, coordinator escalates to human

## LIMITATIONS (By Design)

### What you DO check:
- Surface-level keyword matching
- Presence/absence of required/forbidden elements
- Basic scope boundaries
- Word count

### What you DO NOT check:
- Deep lore accuracy (world-lorekeeper does this)
- Canon timeline consistency (chronicle-keeper does this)
- Character emotional state accuracy (character-state does this)
- Dialogue quality (dialogue-analyst does this)
- Subtle plot inconsistencies (plot-architect does this)
- Scene structure quality (scene-structure does this)

You are intentionally shallow to be FAST. Full validation catches deeper issues.

## LOGGING

Log to: `workspace/logs/blueprint-compliance-fast-checker/scene-{scene_id}-{timestamp}.log`

Include:
- Each check performed and result
- Search terms used
- Lines where violations found
- Execution time per check
- Total execution time

## ERROR HANDLING

- **Draft file not found**: Return ERROR immediately
- **Constraints file not found**: Return ERROR immediately
- **Malformed JSON**: Return ERROR immediately
- **Cannot parse draft**: Return ERROR immediately

Do NOT proceed with partial checks if inputs are invalid.

---

END OF AGENT SPECIFICATION
```

---

## 2. Retry Logic Implementation

### 2.1 Retry State Machine

**Coordinator Retry Logic (in generation-coordinator agent)**:

```
GENERATION LOOP (max 3 attempts):

┌─────────────────────────────────────────────────┐
│ ATTEMPT 1: Standard Generation                 │
├─────────────────────────────────────────────────┤
│ Input:                                          │
│ - verified-plan.json (user-approved)            │
│ - constraints-list.json (from validator)        │
│ - blueprint.md                                  │
│ - context files (previous scene, character)     │
│                                                 │
│ Prompt:                                         │
│ - Standard prompt template v2.0                 │
│ - Constraints in isolated block                 │
│ - 3x repetition (start, inline, end)            │
│                                                 │
│ Execution:                                      │
│ - prose-writer generates draft                  │
│ - Saves to scene-{ID}-draft-attempt1.md         │
│ - Returns compliance-echo.json                  │
│                                                 │
│ Fast-Check:                                     │
│ - fast-checker validates draft                  │
│ - Returns compliance-result.json                │
│                                                 │
│ IF PASS:                                        │
│   → Rename draft-attempt1.md to draft.md        │
│   → Continue to Step 6 (Full Validation)        │
│   → EXIT LOOP                                   │
│                                                 │
│ IF FAIL:                                        │
│   → Extract violations from compliance-result   │
│   → Increment retry_count to 1                  │
│   → Proceed to ATTEMPT 2                        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ ATTEMPT 2: Enhanced Constraints                │
├─────────────────────────────────────────────────┤
│ Input:                                          │
│ - Same as Attempt 1                             │
│ - PLUS: violations list from Attempt 1          │
│                                                 │
│ Prompt Enhancement:                             │
│ - Take standard template                        │
│ - ADD regeneration header:                      │
│                                                 │
│   ⚠️⚠️⚠️ REGENERATION ATTEMPT 2/3 ⚠️⚠️⚠️          │
│                                                 │
│   Previous generation failed compliance:        │
│   {violation_1_details}                         │
│   {violation_2_details}                         │
│                                                 │
│   PAY SPECIAL ATTENTION TO:                     │
│   - {violated_constraint_1} (CRITICAL)          │
│   - {violated_constraint_2} (CRITICAL)          │
│                                                 │
│ - ENHANCE violated constraints:                 │
│   * Change "MUST BE" → "⚠️ CRITICAL: MUST BE"   │
│   * Add negative examples from Attempt 1        │
│   * Repeat violated constraint 3 MORE times     │
│                                                 │
│ Example Enhancement:                            │
│   Attempt 1: "Location: Башня Книжников"        │
│   Attempt 2: "⚠️ CRITICAL: Location MUST BE     │
│               'Башня Книжников медпалата'.      │
│               In Attempt 1 you used 'больница'  │
│               - this is WRONG. Do NOT use       │
│               больница, госпиталь, hospital."   │
│                                                 │
│ Execution:                                      │
│ - prose-writer generates NEW draft              │
│ - Saves to scene-{ID}-draft-attempt2.md         │
│ - Does NOT see attempt1 draft (context isolation)│
│                                                 │
│ Fast-Check:                                     │
│ - fast-checker validates attempt2 draft         │
│                                                 │
│ IF PASS:                                        │
│   → Rename draft-attempt2.md to draft.md        │
│   → Log: "Success on attempt 2"                 │
│   → Continue to Step 6 (Full Validation)        │
│   → EXIT LOOP                                   │
│                                                 │
│ IF FAIL:                                        │
│   → Check if SAME violation as Attempt 1        │
│   → Increment retry_count to 2                  │
│   → Proceed to ATTEMPT 3                        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ ATTEMPT 3: Maximum Emphasis (Final Attempt)    │
├─────────────────────────────────────────────────┤
│ Input:                                          │
│ - Same as previous attempts                     │
│ - PLUS: accumulated violations from 1 & 2       │
│                                                 │
│ Prompt Enhancement:                             │
│ - Take Attempt 2 prompt                         │
│ - REPLACE header with:                          │
│                                                 │
│   🚨🚨🚨 FINAL ATTEMPT (3/3) 🚨🚨🚨                │
│                                                 │
│   Previous 2 attempts FAILED compliance.        │
│   This is your LAST chance.                     │
│                                                 │
│   Violations from Attempt 1:                    │
│   - {violation_1}                               │
│   Violations from Attempt 2:                    │
│   - {violation_2}                               │
│                                                 │
│   ABSOLUTE REQUIREMENTS (NO EXCEPTIONS):        │
│                                                 │
│   ❌ {violated_constraint_1}                    │
│   ❌ {violated_constraint_2}                    │
│                                                 │
│   IF YOU CANNOT COMPLY WITH THESE:              │
│   Return error instead of generating            │
│   non-compliant text.                           │
│                                                 │
│ - MAXIMIZE emphasis:                            │
│   * Violated constraints in BOLD, ALL CAPS      │
│   * Repeat violated constraints 5 times         │
│   * Add "DO NOT use" list with 5+ examples      │
│   * Use ❌ emoji for forbidden items            │
│   * Use ✅ emoji for required items             │
│                                                 │
│ Example Maximum Emphasis:                       │
│   ❌❌❌ DO NOT USE THESE LOCATIONS ❌❌❌          │
│   - больница                                    │
│   - hospital                                    │
│   - медицинский центр                           │
│   - medical center                              │
│   - госпиталь                                   │
│   - clinic / клиника                            │
│                                                 │
│   ✅✅✅ ONLY USE THIS LOCATION ✅✅✅              │
│   Башня Книжников, медпалата                    │
│   (Exact string. Do not paraphrase.)            │
│                                                 │
│ Execution:                                      │
│ - prose-writer generates NEW draft              │
│ - Saves to scene-{ID}-draft-attempt3.md         │
│ - Does NOT see attempt1 or attempt2 (isolation) │
│                                                 │
│ Fast-Check:                                     │
│ - fast-checker validates attempt3 draft         │
│                                                 │
│ IF PASS:                                        │
│   → Rename draft-attempt3.md to draft.md        │
│   → Log: "Success on attempt 3 (WARNING)"       │
│   → Add warning to final output:                │
│      "⚠️ Took 3 attempts. Review carefully."   │
│   → Continue to Step 6 (Full Validation)        │
│   → EXIT LOOP                                   │
│                                                 │
│ IF FAIL:                                        │
│   → STOP GENERATION (no attempt 4)              │
│   → Create failure report                       │
│   → Escalate to human                           │
│   → EXIT LOOP                                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ FAILURE ESCALATION (if 3 attempts fail)        │
├─────────────────────────────────────────────────┤
│ Actions:                                        │
│ 1. Save all 3 failed drafts for review:         │
│    - scene-{ID}-draft-attempt1.md               │
│    - scene-{ID}-draft-attempt2.md               │
│    - scene-{ID}-draft-attempt3.md               │
│                                                 │
│ 2. Create failure report:                       │
│    workspace/failures/scene-{ID}-failure.md     │
│                                                 │
│ 3. Report to user:                              │
│    ❌ GENERATION FAILED AFTER 3 ATTEMPTS        │
│                                                 │
│    Scene: {scene_id}                            │
│    Problem: Cannot comply with constraints      │
│                                                 │
│    Persistent violations:                       │
│    - {violation_1} (failed in all 3 attempts)   │
│    - {violation_2} (failed in attempts 2 & 3)   │
│                                                 │
│    Possible causes:                             │
│    - Blueprint constraints are contradictory    │
│    - Constraints are unclear / ambiguous        │
│    - Technical issue with prose-writer          │
│                                                 │
│    Required actions:                            │
│    1. Review blueprint: {blueprint_path}        │
│    2. Check constraints: {constraints_path}     │
│    3. Review failed attempts: {attempts_dir}    │
│    4. Fix blueprint or relax constraints        │
│    5. Retry generation manually                 │
│                                                 │
│ 4. STOP workflow (do not proceed to validation) │
│                                                 │
│ 5. Wait for human intervention                  │
└─────────────────────────────────────────────────┘
```

### 2.2 Constraint Enhancement Between Attempts

**Detailed Enhancement Algorithm**:

```python
# Pseudocode for coordinator's constraint enhancement logic

def enhance_constraints_for_retry(
    original_template: str,
    violations: list,
    attempt_number: int
) -> str:
    """
    Enhance prompt template based on violations from previous attempt.

    Args:
        original_template: Standard prose-writer template v2.0
        violations: List of violations from fast-checker
        attempt_number: 2 or 3

    Returns:
        Enhanced template with emphasized constraints
    """

    # Step 1: Add regeneration header
    if attempt_number == 2:
        header = """
⚠️⚠️⚠️ REGENERATION ATTEMPT 2 OF 3 ⚠️⚠️⚠️

Your previous generation failed compliance checks due to:
{violations_summary}

PAY SPECIAL ATTENTION TO:
{emphasis_list}

This is attempt 2. Critical compliance required.
"""
    elif attempt_number == 3:
        header = """
🚨🚨🚨 FINAL ATTEMPT (3/3) 🚨🚨🚨

Previous 2 attempts FAILED compliance.
This is your LAST chance before human escalation.

Accumulated violations:
{all_violations_summary}

ABSOLUTE REQUIREMENTS (NO EXCEPTIONS):
{critical_constraints_list}

IF YOU CANNOT COMPLY: Return error instead of generating non-compliant text.
"""

    # Step 2: Identify violated constraints from violations list
    violated_constraints = []
    for violation in violations:
        if violation["check"] == "location_match":
            violated_constraints.append({
                "type": "location",
                "required": violation["required"],
                "wrong_usage": violation["found"],
                "severity": "CRITICAL"
            })
        elif violation["check"] == "forbidden_characters_absent":
            violated_constraints.append({
                "type": "character_absence",
                "forbidden": extract_character_name(violation["found"]),
                "wrong_usage": violation["found"],
                "severity": "CRITICAL"
            })
        # ... similar for other violation types

    # Step 3: Enhance CRITICAL CONSTRAINTS block
    enhanced_constraints_block = generate_enhanced_constraints(
        original_constraints=extract_constraints_block(original_template),
        violated=violated_constraints,
        emphasis_level=attempt_number
    )

    # Step 4: Replace constraints block in template
    enhanced_template = original_template.replace(
        "## ⚠️ CRITICAL CONSTRAINTS",
        header + "\n\n" + enhanced_constraints_block
    )

    # Step 5: Add inline reminders for violated constraints
    for beat in extract_beats(enhanced_template):
        if beat_relates_to_violation(beat, violated_constraints):
            enhanced_template = add_inline_reminder(
                enhanced_template,
                beat,
                violated_constraints,
                emphasis_level=attempt_number
            )

    # Step 6: Enhance final checklist
    enhanced_template = enhance_final_checklist(
        enhanced_template,
        violated_constraints,
        emphasis_level=attempt_number
    )

    return enhanced_template


def generate_enhanced_constraints(
    original_constraints: dict,
    violated: list,
    emphasis_level: int
) -> str:
    """
    Generate enhanced constraints block with emphasis on violations.

    Example for location violation:

    Attempt 1 (original):
    ### LOCATION
    - MUST BE: Башня Книжников, медпалата
    - MUST NOT BE: больница, медицинский центр

    Attempt 2 (enhanced):
    ### LOCATION ⚠️ CRITICAL - FAILED IN ATTEMPT 1
    - ⚠️ MUST BE: Башня Книжников, медпалата
      * In Attempt 1 you used "больница" on line 45
      * This is WRONG and violates blueprint
    - ❌ MUST NOT BE: больница, медицинский центр, госпиталь, hospital
      * Do NOT use these terms even as synonyms
      * Previous mistake: "больница" - DO NOT REPEAT

    Attempt 3 (maximum emphasis):
    ### LOCATION 🚨 CRITICAL - FAILED IN ATTEMPTS 1 & 2 🚨

    ❌❌❌ DO NOT USE (forbidden locations) ❌❌❌
    - больница (you used this in Attempt 1 - WRONG)
    - hospital (English equivalent - also WRONG)
    - медицинский центр (you used this in Attempt 2 - WRONG)
    - medical center
    - госпиталь
    - clinic / клиника
    - Any other medical facility terms

    ✅✅✅ ONLY USE (exact required location) ✅✅✅
    Башня Книжников, медпалата

    (Copy this exact string. Do not paraphrase or translate.)

    Examples of CORRECT usage:
    - "В медпалате Башни Книжников..."
    - "Башня Книжников, медпалата, была тихой"
    - "...вернулся в медпалату Башни Книжников"

    Examples of WRONG usage (DO NOT USE):
    - "В больнице..." ❌
    - "В медицинском центре..." ❌
    - "В госпитале Книжников..." ❌
    """

    # Implementation details...
    pass
```

**Real Example for Scene 0204**:

**Attempt 1 → Attempt 2 Enhancement**:

*Violation from Attempt 1*: Used "больница" instead of "Башня Книжников медпалата"

*Original Constraint (Attempt 1)*:
```markdown
### LOCATION
- MUST BE: Башня Книжников, медпалата
- MUST NOT BE: больница, медицинский центр
```

*Enhanced Constraint (Attempt 2)*:
```markdown
### LOCATION ⚠️ CRITICAL - VIOLATION DETECTED IN ATTEMPT 1

⚠️ **REQUIRED LOCATION** (exact):
Башня Книжников, медпалата

In Attempt 1, you used "больница" on lines 45, 67, 89.
This is **WRONG** and violates the blueprint requirement.

❌ **FORBIDDEN LOCATIONS** (do NOT use):
- больница (you used this - WRONG)
- медицинский центр
- госпиталь
- hospital (English)
- medical center (English)

**REMINDER**: The scene takes place in Башня Книжников (Tower of Scribes), specifically in the медпалата (medical ward) inside that tower. NOT in a separate hospital building.

Use phrases like:
✅ "В медпалате Башни Книжников..."
✅ "Башня Книжников, медпалата, ..."
✅ "...в медпалату Башни Книжников"

Do NOT use:
❌ "В больнице..."
❌ "Медицинский центр..."
```

**Attempt 2 → Attempt 3 Enhancement** (if Attempt 2 also fails):

*Violation from Attempt 2*: Still used "больница" variant ("больничная палата")

*Maximum Emphasis (Attempt 3)*:
```markdown
### LOCATION 🚨🚨🚨 CRITICAL FAILURE - 2 ATTEMPTS FAILED 🚨🚨🚨

YOU HAVE FAILED THIS CONSTRAINT TWICE.
This is your FINAL attempt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ ABSOLUTELY FORBIDDEN WORDS ❌
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT USE ANY OF THESE:
1. больница (you used this in Attempt 1 - WRONG)
2. больничная (you used this in Attempt 2 - WRONG)
3. больничный
4. hospital
5. медицинский центр
6. medical center
7. госпиталь
8. clinic / клиника
9. лазарет
10. ANY synonym for "hospital" in Russian or English

IF YOU USE ANY OF THE ABOVE WORDS:
Your output will be REJECTED.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ REQUIRED EXACT PHRASE ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

USE THIS EXACT LOCATION:
"Башня Книжников, медпалата"

Or variations that include BOTH parts:
- "В медпалате Башни Книжников"
- "Башня Книжников, в медпалате"
- "медпалата Башни Книжников"

CRITICAL: You MUST use "Башня Книжников" (Tower of Scribes).
CRITICAL: You MUST use "медпалата" (medical ward).
CRITICAL: You MUST NOT use "больница" or any hospital synonyms.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPEAT AFTER ME (memorize this):
"The location is Башня Книжников, медпалата"
"The location is Башня Книжников, медпалата"
"The location is Башня Книжников, медпалата"
"The location is Башня Книжников, медпалата"
"The location is Башня Книжников, медпалата"

NOT больница. NOT hospital. NOT медицинский центр.
ONLY Башня Книжников, медпалата.

IF YOU CANNOT COMPLY:
Return this error instead of generating text:
"ERROR: Cannot generate scene without using forbidden location terms. Blueprint may need revision."
```

---

### 2.3 Context Isolation Between Attempts

**Problem**: If prose-writer sees previous failed draft, it might:
- Copy the same mistakes
- Be influenced by failed approach
- Waste tokens on wrong context

**Solution**: Complete context isolation between attempts

**Implementation**:

```markdown
## Context Isolation Protocol

### What prose-writer RECEIVES in each attempt:

**Attempt 1, 2, 3 (all identical inputs except prompt):**
- verified-plan.json (same)
- blueprint.md (same)
- previous-scene.md (same - for continuity)
- pov-character-sheet.md (same)
- world-mechanics-excerpt.md (same, if applicable)

**What prose-writer DOES NOT RECEIVE:**
- scene-{ID}-draft-attempt1.md (not passed to Attempt 2)
- scene-{ID}-draft-attempt2.md (not passed to Attempt 3)
- compliance-result files from previous attempts
- Any workspace/artifacts from previous attempts

### How coordinator ensures isolation:

1. **Separate output files**:
   - Attempt 1 → saves to `scene-{ID}-draft-attempt1.md`
   - Attempt 2 → saves to `scene-{ID}-draft-attempt2.md`
   - Attempt 3 → saves to `scene-{ID}-draft-attempt3.md`
   - Final → rename successful attempt to `scene-{ID}-draft.md`

2. **Fresh agent invocation**:
   - Coordinator invokes prose-writer as NEW agent instance for each attempt
   - No persistent state carried over
   - Each attempt is like "first time generation"

3. **Enhanced prompt only**:
   - Attempt 2/3 prompt contains ONLY:
     - Violations description (text, not file reference)
     - Enhanced constraints (text)
     - NOT: "read the failed draft to see what you did wrong"
   - prose-writer learns from violation description, not from reading failed text

4. **Workspace cleanup**:
   - After successful generation, delete failed attempts:
     ```
     IF attempt2 succeeds:
       DELETE scene-{ID}-draft-attempt1.md
       KEEP scene-{ID}-draft-attempt2.md (rename to draft.md)
     ```

### Example: Attempt 2 prompt does NOT contain:

❌ WRONG approach:
```markdown
Read your previous attempt here: workspace/scene-0204-draft-attempt1.md

Fix the errors and regenerate.
```

✅ CORRECT approach:
```markdown
Your previous generation failed compliance due to:
- Location: You used "больница", required is "Башня Книжников медпалата"

Generate a NEW scene following the enhanced constraints below.
(Do NOT reference or read the failed attempt. Start fresh.)
```

### Benefits:
- No context pollution from failed attempts
- Each attempt has "fresh eyes" on the problem
- Prevents copying mistakes
- Reduces token usage (not passing 1000+ word failed drafts)
```

---

## 3. Artifact Schemas (JSON)

### 3.1 extracted-constraints.json

**File**: `workspace/validation/scene-{scene_id}-constraints-list.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Scene Blueprint Constraints",
  "description": "Extracted constraints from validated blueprint for prose generation",
  "type": "object",
  "required": ["status", "scene_id", "blueprint_path", "timestamp", "constraints"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL"],
      "description": "Validation result from blueprint-validator"
    },
    "scene_id": {
      "type": "string",
      "pattern": "^[0-9]{4}$",
      "description": "Scene identifier (e.g., '0204')"
    },
    "blueprint_path": {
      "type": "string",
      "description": "Absolute path to validated blueprint file"
    },
      "type": "string",
      "pattern": "^v[0-9]+\\.[0-9]+$",
      "description": "Blueprint version (e.g., 'v3.0')"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of validation"
    },
    "constraints": {
      "type": "object",
      "required": ["location", "characters", "mechanics", "scope", "word_count"],
      "properties": {
        "location": {
          "type": "object",
          "required": ["required", "forbidden"],
          "properties": {
            "required": {
              "type": "string",
              "description": "Exact location string required"
            },
            "forbidden": {
              "type": "array",
              "items": {"type": "string"},
              "description": "List of forbidden location terms"
            }
          }
        },
        "characters": {
          "type": "object",
          "required": ["present", "absent"],
          "properties": {
            "present": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Characters that must appear"
            },
            "absent": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Characters that must NOT appear"
            },
            "absent_reason": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Reasons for absence (e.g., 'removed per plan')"
            }
          }
        },
        "mechanics": {
          "type": "object",
          "required": ["required", "forbidden"],
          "properties": {
            "required": {
              "type": "string",
              "description": "Description of required world mechanics"
            },
            "forbidden": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Forbidden mechanics representations"
            }
          }
        },
        "scope": {
          "type": "object",
          "required": ["beats", "forbidden_content"],
          "properties": {
            "beats": {
              "type": "array",
              "items": {"type": "integer"},
              "description": "Beat numbers included in this scene"
            },
            "forbidden_content": {
              "type": "array",
              "items": {"type": "string"},
              "description": "Content from other scenes to avoid"
            }
          }
        },
        "word_count": {
          "type": "object",
          "required": ["min", "max"],
          "properties": {
            "min": {"type": "integer", "minimum": 0},
            "max": {"type": "integer", "minimum": 0}
          }
        }
      }
    },
    "validation_checks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["check", "result"],
        "properties": {
          "check": {"type": "string"},
          "result": {"type": "string", "enum": ["PASS", "FAIL", "WARNING"]}
        }
      }
    }
  }
}
```

**Example Instance** (Scene 0204):
```json
{
  "status": "PASS",
  "scene_id": "0204",
  "blueprint_path": "E:\\sources\\book-alexa-right\\acts\\act-1\\chapters\\chapter-02\\scenes\\scene-0204-blueprint.md",
  "timestamp": "2025-10-31T14:23:45Z",
  "constraints": {
    "location": {
      "required": "Башня Книжников, медпалата",
      "forbidden": ["больница", "медицинский центр", "госпиталь", "hospital", "medical center"]
    },
    "characters": {
      "present": ["Алекса Райт", "Реджинальд Хавенфорд"],
      "absent": ["Себастьян Грей"],
      "absent_reason": ["removed per chapter plan"]
    },
    "mechanics": {
      "required": "Automatic system compensation notification (+2 months awarded automatically by Library system)",
      "forbidden": ["personal gift from character", "manual compensation", "Alexa gives time personally"]
    },
    "scope": {
      "beats": [1, 2, 3, 4],
      "forbidden_content": [
        "scene-0203 Diana memory details",
        "scene-0205 departure/next location content"
      ]
    },
    "word_count": {
      "min": 1000,
      "max": 1100
    }
  },
  "validation_checks": [
    {"check": "file_exists", "result": "PASS"},
    {"check": "version_v3_compliant", "result": "PASS"},
    {"check": "required_fields_present", "result": "PASS"},
    {"check": "v3_changes_compliant", "result": "PASS"},
    {"check": "internal_consistency", "result": "PASS"},
    {"check": "constraints_extractable", "result": "PASS"}
  ]
}
```

---

### 3.2 verified-plan.json

**File**: `workspace/verification/scene-{scene_id}-verified-plan.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "User-Verified Generation Plan",
  "description": "Plan approved by user before prose generation",
  "type": "object",
  "required": ["scene_id", "status", "timestamp", "plan"],
  "properties": {
    "scene_id": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["APPROVED", "MODIFIED", "REJECTED"]
    },
    "timestamp": {"type": "string", "format": "date-time"},
    "approved_by": {
      "type": "string",
      "description": "User identifier or 'author'"
    },
    "modifications": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "original_value": {"type": "string"},
          "new_value": {"type": "string"},
          "reason": {"type": "string"}
        }
      },
      "description": "List of user-requested modifications to original plan"
    },
    "plan": {
      "type": "object",
      "description": "The approved plan (may include modifications)",
      "properties": {
        "location": {"type": "string"},
        "characters_present": {"type": "array", "items": {"type": "string"}},
        "characters_absent": {"type": "array", "items": {"type": "string"}},
        "plot_beats": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "beat_number": {"type": "integer"},
              "description": {"type": "string"}
            }
          }
        },
        "mechanics": {"type": "string"},
        "emotional_tone": {"type": "string"},
        "word_count_target": {
          "type": "object",
          "properties": {
            "min": {"type": "integer"},
            "max": {"type": "integer"}
          }
        }
      }
    }
  }
}
```

**Example Instance** (Scene 0204, with user modification):
```json
{
  "scene_id": "0204",
  "status": "MODIFIED",
  "timestamp": "2025-10-31T14:25:12Z",
  "approved_by": "author",
  "modifications": [
    {
      "field": "emotional_tone",
      "original_value": "Deep compassion and emotional connection",
      "new_value": "Professional detachment with cracks showing",
      "reason": "Author requested more restrained emotional tone for Alexa"
    }
  ],
  "plan": {
    "location": "Башня Книжников, медпалата",
    "characters_present": ["Алекса Райт", "Реджинальд Хавенфорд"],
    "characters_absent": ["Себастьян Грей"],
    "plot_beats": [
      {
        "beat_number": 1,
        "description": "Continuation of Immersion session work in медпалата"
      },
      {
        "beat_number": 2,
        "description": "Immersion into Reginald's memory of daughter's death"
      },
      {
        "beat_number": 3,
        "description": "Alexa's emotional reaction - professional facade with cracks"
      },
      {
        "beat_number": 4,
        "description": "Session conclusion with automatic compensation award"
      }
    ],
    "mechanics": "Automatic system compensation notification",
    "emotional_tone": "Professional detachment with cracks showing",
    "word_count_target": {
      "min": 1000,
      "max": 1100
    }
  }
}
```

---

### 3.3 generation-metadata.json

**File**: `workspace/generation/scene-{scene_id}-metadata.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Generation Process Metadata",
  "description": "Metadata about generation attempts, timing, status",
  "type": "object",
  "required": ["scene_id", "status", "attempts", "timing"],
  "properties": {
    "scene_id": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["IN_PROGRESS", "SUCCESS", "FAILED", "CANCELLED"]
    },
    "attempts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "attempt_number": {"type": "integer", "minimum": 1, "maximum": 3},
          "timestamp_start": {"type": "string", "format": "date-time"},
          "timestamp_end": {"type": "string", "format": "date-time"},
          "duration_seconds": {"type": "number"},
          "draft_file": {"type": "string"},
          "fast_check_result": {
            "type": "string",
            "enum": ["PASS", "FAIL", "NOT_RUN"]
          },
          "violations": {
            "type": "array",
            "items": {"type": "string"}
          },
          "enhancement_applied": {"type": "boolean"}
        }
      }
    },
    "timing": {
      "type": "object",
      "properties": {
        "total_duration_seconds": {"type": "number"},
        "step_1_file_check": {"type": "number"},
        "step_2_blueprint_validation": {"type": "number"},
        "step_3_verification_planning": {"type": "number"},
        "step_4_prose_generation": {"type": "number"},
        "step_5_fast_compliance": {"type": "number"},
        "step_6_full_validation": {"type": "number"},
        "step_7_output_formatting": {"type": "number"}
      }
    },
    "final_draft": {
      "type": "string",
      "description": "Path to final approved draft"
    },
    "success_attempt": {
      "type": "integer",
      "description": "Which attempt succeeded (1, 2, or 3)"
    }
  }
}
```

**Example Instance**:
```json
{
  "scene_id": "0204",
  "status": "SUCCESS",
  "attempts": [
    {
      "attempt_number": 1,
      "timestamp_start": "2025-10-31T14:26:00Z",
      "timestamp_end": "2025-10-31T14:30:15Z",
      "duration_seconds": 255,
      "draft_file": "workspace/generation/scene-0204-draft-attempt1.md",
      "fast_check_result": "FAIL",
      "violations": [
        "Location: used 'больница' instead of 'Башня Книжников медпалата'"
      ],
      "enhancement_applied": false
    },
    {
      "attempt_number": 2,
      "timestamp_start": "2025-10-31T14:30:30Z",
      "timestamp_end": "2025-10-31T14:34:20Z",
      "duration_seconds": 230,
      "draft_file": "workspace/generation/scene-0204-draft-attempt2.md",
      "fast_check_result": "PASS",
      "violations": [],
      "enhancement_applied": true
    }
  ],
  "timing": {
    "total_duration_seconds": 520,
    "step_1_file_check": 2,
    "step_2_blueprint_validation": 18,
    "step_3_verification_planning": 12,
    "step_4_prose_generation": 255 + 230,
    "step_5_fast_compliance": 22 + 18,
    "step_6_full_validation": 75,
    "step_7_output_formatting": 8
  },
  "final_draft": "acts/act-1/chapters/chapter-02/content/scene-0204-draft.md",
  "success_attempt": 2
}
```

---

### 3.4 validation-results.json (from individual validators)

**File**: `workspace/validation/scene-{scene_id}-{validator_name}-result.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Validator Result",
  "description": "Result from individual validator agent",
  "type": "object",
  "required": ["validator", "scene_id", "status", "timestamp"],
  "properties": {
    "validator": {
      "type": "string",
      "enum": [
        "world-lorekeeper",
        "canon-guardian",
        "character-state",
        "plot-architect",
        "scene-structure",
        "chronicle-keeper",
        "dialogue-analyst"
      ]
    },
    "scene_id": {"type": "string"},
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL", "WARNING"]
    },
    "timestamp": {"type": "string", "format": "date-time"},
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
          "message": {"type": "string"},
          "location": {"type": "string"},
          "fix_suggestion": {"type": "string"}
        }
      }
    },
    "warnings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "message": {"type": "string"},
          "suggestion": {"type": "string"}
        }
      }
    },
    "summary": {"type": "string"}
  }
}
```

---

### 3.5 compliance-check-result.json

**File**: `workspace/validation/scene-{scene_id}-fast-compliance-result.json`

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Fast Compliance Check Result",
  "description": "Result from blueprint-compliance-fast-checker",
  "type": "object",
  "required": ["status", "scene_id", "timestamp"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["PASS", "FAIL"]
    },
    "scene_id": {"type": "string"},
    "draft_path": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "checks_performed": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "check": {
            "type": "string",
            "enum": [
              "location_match",
              "forbidden_characters_absent",
              "required_characters_present",
              "mechanics_match",
              "scope_boundaries",
              "word_count"
            ]
          },
          "result": {"type": "string", "enum": ["PASS", "FAIL", "WARNING"]},
          "details": {"type": "string"}
        }
      }
    },
    "violations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "check": {"type": "string"},
          "result": {"type": "string"},
          "severity": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM"]},
          "found": {"type": "string"},
          "required": {"type": "string"},
          "message": {"type": "string"}
        }
      }
    },
    "recommendation": {"type": "string"},
    "retry_guidance": {
      "type": "object",
      "properties": {
        "emphasis_needed": {
          "type": "array",
          "items": {"type": "string"}
        },
        "suggested_fix": {"type": "string"}
      }
    },
    "execution_time_seconds": {"type": "number"}
  }
}
```

---

## 4. Integration Plan

### 4.1 Current Workflow (before FEAT-0001)

**Based on existing documentation**:

```
CURRENT GENERATION WORKFLOW (assumed from docs):

User: "Generate scene 0204"
  ↓
┌─────────────────────────────────────────┐
│ Director/Coordinator (if exists)        │
│ - Locates blueprint                     │
│ - Passes to prose-writer                │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│ prose-writer                            │
│ - Reads blueprint                       │
│ - Generates full text (1500 words)      │
│ - Returns text in response              │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│ Validation (7 agents in parallel)       │
│ - world-lorekeeper                      │
│ - canon-guardian                        │
│ - character-state                       │
│ - plot-architect                        │
│ - scene-structure                       │
│ - chronicle-keeper                      │
│ - dialogue-analyst                      │
└─────────────────────────────────────────┘
  ↓
Final Output: Draft file + validation results
```

**Problems**:
- No pre-check of blueprint validity
- No user approval before expensive generation
- Constraints mixed into long prompt (not isolated)
- No fast-fail mechanism before full validation
- Errors only caught AFTER full generation + validation (wasted 6-8 minutes)

---

### 4.2 Modified Workflow (after FEAT-0001)

```
NEW GENERATION WORKFLOW (FEAT-0001):

User: "Generate scene 0204"
  ↓
┌─────────────────────────────────────────┐
│ generation-coordinator (NEW)            │
│ Step 1: Blueprint file check            │
│ Step 2-7: Orchestrate workflow          │
└─────────────────────────────────────────┘
  ↓
Step 1: File System Check (coordinator logic)
  ├─ Check: acts/.../scene-0204-blueprint.md exists?
  ├─ YES → Continue
  └─ NO → ERROR: "Blueprint not found. Use /plan-scene 0204"
  ↓
Step 2: Blueprint Validation (NEW)
┌─────────────────────────────────────────┐
│ blueprint-validator (NEW AGENT)         │
│ - Validates blueprint structure         │
│ - Checks plan compliance                  │
│ - Extracts constraints                  │
│ - Returns: constraints-list.json        │
└─────────────────────────────────────────┘
  ├─ FAIL → Show errors to user, STOP
  └─ PASS → Continue
  ↓
Step 3: Verification Plan (NEW)
┌─────────────────────────────────────────┐
│ verification-planner (NEW AGENT)        │
│ - Reads constraints-list.json           │
│ - Formats human-readable plan           │
│ - Returns: verification-plan.md         │
└─────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────┐
│ USER APPROVAL (CRITICAL TOUCHPOINT)     │
│ - Coordinator shows plan                │
│ - User: Y / n / "modify X"              │
└─────────────────────────────────────────┘
  ├─ Y → Save verified-plan.json, Continue
  ├─ Modify → Update plan, re-show, loop
  └─ n → STOP
  ↓
Step 4: Generation (MODIFIED, with retry)
┌─────────────────────────────────────────┐
│ prose-writer (MODIFIED AGENT)           │
│ - Uses prose-writer-template-v2.md      │
│ - Isolated constraints block            │
│ - 3x repetition (Rule 3)                │
│ - Saves draft to file                   │
│ - Returns metadata (NOT full text)      │
└─────────────────────────────────────────┘
  ↓
Step 5: Fast Compliance Check (NEW)
┌─────────────────────────────────────────┐
│ blueprint-compliance-fast-checker (NEW) │
│ - Checks location, characters, mechanics│
│ - Returns: compliance-result.json       │
└─────────────────────────────────────────┘
  ├─ PASS → Continue to Step 6
  └─ FAIL → Retry loop (max 3 attempts)
           ├─ Attempt 2: Enhanced constraints
           ├─ Attempt 3: Maximum emphasis
           └─ 3 fails → Escalate to human
  ↓
Step 6: Full Validation (EXISTING, unchanged)
┌─────────────────────────────────────────┐
│ validation-aggregator                   │
│ - Spawns 7 validators in parallel       │
│ - Aggregates results                    │
│ - Returns: final-validation-report.json │
└─────────────────────────────────────────┘
  ↓
Step 7: Final Output (coordinator formatting)
┌─────────────────────────────────────────┐
│ generation-coordinator                  │
│ - Formats final user message            │
│ - Shows: summary, validation, next steps│
│ - Does NOT show: full text (in file)    │
└─────────────────────────────────────────┘
  ↓
User receives: Transparent report, ready draft
```

**Changes Summary**:
- **Added**: Steps 1-3 (file check, blueprint validation, verification plan)
- **Modified**: Step 4 (prose-writer with new template + retry logic)
- **Added**: Step 5 (fast compliance check with auto-retry)
- **Unchanged**: Step 6 (full validation, 7 agents)
- **Modified**: Step 7 (coordinator formats output, not prose-writer)

---

### 4.3 Migration Strategy

#### Phase 1: Infrastructure Setup (Week 1)

**Goal**: Create new agents and templates without breaking existing workflow

**Actions**:
1. Create new agent files:
   - `.claude/agents/generation/blueprint-validator.md`
   - `.claude/agents/generation/verification-planner.md`
   - `.claude/agents/generation/blueprint-compliance-fast-checker.md`
   - `.claude/agents/generation/generation-coordinator.md`

2. Create prompt template:
   - `.workflows/prompts/prose-writer-template-v2.md`

3. Create schema files:
   - `workspace/schemas/constraints-list-schema.json`
   - `workspace/schemas/verified-plan-schema.json`
   - `workspace/schemas/compliance-result-schema.json`
   - `workspace/schemas/generation-metadata-schema.json`

4. **Do NOT modify existing prose-writer yet**
   - Keep current prose-writer as fallback
   - Test new workflow in parallel

**Testing**:
- Read each agent file to validate formatting
- Validate JSON schemas
- No execution yet, just infrastructure

**Deliverable**: All files exist, schemas valid

---

#### Phase 2: Backward Compatibility (Week 1-2)

**Goal**: Ensure existing blueprints work with new workflow

**Challenge**: Old blueprints may lack:
- Version headers
- CURRENT PLAN REQUIREMENTS section
- Explicit location/character/mechanics fields

**Solution**: blueprint-validator handles gracefully

**Implementation**:

Add to blueprint-validator logic:
```markdown
### BACKWARD COMPATIBILITY MODE

IF blueprint lacks version header:
  - Assume version v2.9 (pre-v3)
  - Return WARNING (not ERROR):
    "Blueprint lacks version header. Assuming v2.9 (pre-v3).
     Add version header for full compliance checking."
  - Continue with limited validation (skip v3 change checks)
  - Extract constraints from whatever structure exists

IF blueprint lacks required fields:
  - Attempt to infer from blueprint content:
    * Location: Search for "Location:" or "Setting:" line
    * Characters: Search for character name mentions
    * Mechanics: Search for world mechanics descriptions
  - IF cannot infer → Return ERROR with missing fields list
  - IF inferred successfully → Return WARNING + extracted constraints

IF blueprint is v1 or v2 (pre-v3):
  - Skip plan compliance checks
  - Return WARNING: "Blueprint is v{X}. Consider upgrading to v3."
  - Extract constraints from available information
```

**Migration Path**:
1. Test new workflow on EXISTING scene 0204 blueprint (as-is)
2. If validation fails, add minimal version header to 0204 blueprint
3. Gradually update other blueprints when generating those scenes
4. No need to update ALL blueprints upfront

**Deliverable**: New workflow works with both v3 and pre-v3 blueprints

---

#### Phase 3: Phased Rollout (Week 2-3)

**Goal**: Deploy to production incrementally, monitor success

**Rollout Plan**:

**Stage 1: Single Scene Test** (scene 0204)
- Use scene 0204 for end-to-end test (known problematic scene)
- Run full 7-step workflow
- Monitor for errors
- Collect metrics:
  - Time per step
  - Constraint compliance (attempts needed)
  - Validation results
- **Success Criteria**: Scene 0204 generates correctly in <8 minutes, <2 attempts

**Stage 2: Chapter 2 Scenes** (scenes 0201-0206)
- Apply to all remaining chapter 2 scenes
- Monitor success rate across scenes
- Identify any patterns in failures
- **Success Criteria**: >80% first-attempt success rate

**Stage 3: Other Chapters** (as new scenes are generated)
- Use new workflow for all NEW scene generation
- Gradually update old scenes if regeneration needed
- **Success Criteria**: New workflow becomes default, old workflow deprecated

**Rollback Plan**:
- If new workflow fails consistently (>50% failure rate):
  - Revert to old prose-writer
  - Keep blueprint-validator as optional pre-check
  - Diagnose issue before re-deploying
- Rollback trigger: 3 consecutive scene failures OR critical bug

**Deliverable**: New workflow deployed, metrics tracked, old workflow available as fallback

---

### 4.4 Testing Before Full Deploy

#### Test Scenes Selection

**Scene 0204** (Primary Test):
- **Why**: Known problematic scene with violations in attempts past
  - Location violation (больница vs Башня Книжников)
  - Character violation (Себастьян Грей inclusion)
  - Mechanics violation (personal gift vs automatic system)
- **Expected Outcome**:
  - blueprint-validator catches any blueprint issues
  - fast-checker catches violations if prose-writer fails
  - Auto-retry succeeds by attempt 2
- **Success Criteria**:
  - Generates correctly
  - <2 attempts needed
  - All constraints met
  - Total time <8 minutes

**Scene 0202** (Secondary Test):
- **Why**: Had scope violation (included content from 0203)
- **Expected Outcome**:
  - Scope constraint properly enforced
  - fast-checker catches scope violations
- **Success Criteria**:
  - No scope bleed
  - Content limited to 0202 beats only

**Scene 0205** (New Scene Test):
- **Why**: Not yet generated, clean slate
- **Expected Outcome**:
  - Smooth first-time generation
  - Verification plan clear and accurate
- **Success Criteria**:
  - Generates correctly on attempt 1
  - Total time 5-7 minutes

#### Success Metrics

**Quantitative**:
- **Constraint compliance rate**: >90% (scenes pass fast-check on first attempt)
- **Blueprint validation pass rate**: >95% (blueprints are well-formed)
- **Auto-retry success rate**: >80% (if attempt 1 fails, attempt 2 succeeds)
- **Time per scene**: 5-8 minutes average
- **Human escalation rate**: <5% (rarely need human intervention after 3 attempts)

**Qualitative**:
- **User experience**: Author feels "in control" (verification plan approval)
- **Transparency**: Author understands what's happening at each step
- **Reliability**: No unexpected results (no location/character violations)

#### Acceptance Criteria for Production

Before declaring FEAT-0001 "complete", verify:
- [ ] Scene 0204 regenerated successfully with new workflow
- [ ] Scene 0202 regenerated without scope violations
- [ ] Scene 0205 generated (new scene) successfully
- [ ] All 3 test scenes meet success criteria
- [ ] Documentation updated (.workflows/generation.md)
- [ ] Metrics baseline established (for future comparison)
- [ ] Rollback procedure tested (can revert to old workflow if needed)

---

## 5. Implementation Roadmap

### Week 1: Infrastructure & Core Agents

**Days 1-2: Agent Creation**
- [ ] Create `blueprint-validator.md`
  - Copy prompt from Section 1.1
  - Test: Read file, validate structure
- [ ] Create `verification-planner.md`
  - Copy prompt from Section 1.2
  - Test: Read file, validate structure
- [ ] Create `blueprint-compliance-fast-checker.md`
  - Copy prompt from Section 1.4
  - Test: Read file, validate structure
- [ ] Create `generation-coordinator.md`
  - Write based on Part 1 specs + Section 2 retry logic
  - Test: Read file, validate structure

**Days 3-4: Prompt Template & Schemas**
- [ ] Create `prose-writer-template-v2.md`
  - Copy from Section 1.3
  - Add placeholders for coordinator to fill
  - Test: Validate template structure
- [ ] Create JSON schemas
  - `constraints-list-schema.json` (Section 3.1)
  - `verified-plan-schema.json` (Section 3.2)
  - `compliance-result-schema.json` (Section 3.5)
  - `generation-metadata-schema.json` (Section 3.3)
  - Test: Validate schemas with JSON Schema validator

**Days 5: Blueprint Updates**
- [ ] Add version header to scene-0204-blueprint.md
  - Use format from WORKFLOW_UPDATE_v2.md Rule 6
  - Document V3 critical changes
- [ ] Validate blueprint passes blueprint-validator
  - Run blueprint-validator on 0204 blueprint
  - Fix any issues found
  - Ensure PASS result

**Deliverable**: All agent files exist, template ready, schemas valid, test blueprint updated

**Testing**:
```bash
# Validate agent files exist
ls .claude/agents/generation/blueprint-validator.md
ls .claude/agents/generation/verification-planner.md
ls .claude/agents/generation/blueprint-compliance-fast-checker.md
ls .claude/agents/generation/generation-coordinator.md

# Validate template exists
ls .workflows/prompts/prose-writer-template-v2.md

# Validate schemas
# (use JSON schema validator tool)
```

---

### Week 2: Core Workflow Implementation

**Days 1-2: Steps 1-3 Wiring**
- [ ] Implement generation-coordinator Steps 1-3
  - Step 1: File system check logic
  - Step 2: Invoke blueprint-validator, handle results
  - Step 3: Invoke verification-planner, show plan to user
- [ ] Test Steps 1-3 in isolation
  - Input: "Generate scene 0204"
  - Expected: Verification plan displayed, awaiting approval
  - No prose generation yet (stop after Step 3)

**Days 3-4: Step 4-5 (Generation + Fast-Check)**
- [ ] Implement prose-writer invocation
  - Coordinator fills template placeholders
  - Passes to prose-writer
  - Receives metadata (not full text)
- [ ] Implement fast-checker invocation
  - Coordinator passes draft + constraints
  - Receives compliance-result.json
  - Handles PASS/FAIL
- [ ] Implement retry logic (max 3 attempts)
  - Enhance constraints on FAIL
  - Isolate contexts between attempts
  - Escalate after 3 failures

**Days 5: Integration Test**
- [ ] Run full workflow (Steps 1-5) on scene 0204
  - Expected: Draft generated, passes fast-check
  - Record: attempts needed, time taken
- [ ] If failures occur:
  - Debug constraint enhancement logic
  - Refine fast-checker sensitivity
  - Adjust prose-writer template

**Deliverable**: Steps 1-5 working end-to-end, draft generated and validated (fast)

**Testing**:
```bash
# End-to-end test
Task: "Generate scene 0204"
Expected output:
  - Verification plan shown
  - User approves
  - Draft generated (1-3 attempts)
  - Fast-check PASS
  - Draft file exists: acts/.../scene-0204-draft.md
```

---

### Week 3: Full Validation & Output

**Days 1-2: Step 6 (Full Validation)**
- [ ] Wire validation-aggregator
  - Coordinator invokes aggregator after fast-check PASS
  - Aggregator spawns 7 validators in parallel
  - Aggregator collects results
  - Returns final-validation-report.json
- [ ] Test validation aggregation
  - Use draft from Week 2
  - Run all 7 validators
  - Verify results aggregated correctly

**Days 3-4: Step 7 (Final Output Formatting)**
- [ ] Implement output formatter in coordinator
  - Read validation report
  - Generate summary (2-3 sentences)
  - Extract key moments from draft
  - Format final message with:
    - File path
    - Word count
    - Time taken
    - Attempts count
    - Validation results (checkmarks)
    - Next steps recommendations
- [ ] Test final output formatting
  - Input: completed scene 0204
  - Expected: Professional, readable output
  - Verify: Does NOT include full text (only in file)

**Day 5: End-to-End Test (Full Workflow)**
- [ ] Run complete 7-step workflow on scene 0204
  - From "Generate scene 0204" to final output
  - Record all metrics:
    - Total time
    - Time per step
    - Attempts needed
    - Validation results
  - Verify all success criteria met

**Deliverable**: Full 7-step workflow working, scene 0204 generated successfully

**Testing**:
```bash
# Full end-to-end test
Task: "Generate scene 0204"
Expected:
  1. Blueprint validation PASS (<20 sec)
  2. Verification plan shown
  3. User approves
  4. Draft generated (1-2 attempts, 3-5 min)
  5. Fast-check PASS (<30 sec)
  6. Full validation (7 agents, 60-90 sec)
  7. Final output shown
Total time: 5-8 minutes
```

---

### Week 4: Polish & Additional Scenes

**Days 1-2: Scene 0202 Regeneration**
- [ ] Apply workflow to scene 0202
  - Test scope violation prevention
  - Verify no content from scene 0203 bleeds in
- [ ] Compare with previous 0202 version
  - Check for improvements
  - Verify scope compliance

**Days 3-4: Scene 0205 First Generation**
- [ ] Create scene-0205-blueprint.md (if not exists)
  - Add version header (v3.0)
  - Document constraints
- [ ] Generate scene 0205 using new workflow
  - Test "first generation" path (not regeneration)
  - Verify smooth experience
  - Record metrics

**Day 5: Logging & Observability**
- [ ] Add comprehensive logging to all agents
  - blueprint-validator logs
  - verification-planner logs
  - prose-writer logs
  - fast-checker logs
  - coordinator logs
- [ ] Create log aggregation
  - Single timeline view of full workflow
  - For debugging failures
- [ ] Add metrics tracking
  - Success rates
  - Time per step
  - Violation patterns

**Deliverable**: 3 scenes successfully generated (0202, 0204, 0205), comprehensive logging

**Testing**:
```bash
# Verify logging
ls workspace/logs/blueprint-validator/
ls workspace/logs/generation-coordinator/
# Check logs contain useful debugging info
```

---

### Week 5: Documentation & Deployment

**Days 1-2: Documentation Updates**
- [ ] Update `.workflows/generation.md`
  - Replace old Stage 6 with new 7-step workflow
  - Add diagrams
  - Add troubleshooting section
- [ ] Create `.workflows/feat-0001-guide.md`
  - User-facing guide
  - "How to use reliable scene generation"
  - Common issues and fixes
- [ ] Update `.workflows/agents-reference.md`
  - Add 4 new agents
  - Update prose-writer entry
  - Add cross-references

**Days 3-4: Metrics Baseline & Monitoring**
- [ ] Establish baseline metrics from 3 test scenes:
  - Average time per scene: {X} minutes
  - First-attempt success rate: {Y}%
  - Auto-retry success rate: {Z}%
- [ ] Create monitoring dashboard (simple)
  - Track: scenes generated, attempts, time, failures
  - Identify: patterns in failures
- [ ] Set alerts
  - >3 consecutive failures → review system
  - Average time >10 minutes → investigate performance

**Day 5: Production Deployment**
- [ ] Update CLAUDE.md
  - Document new generation workflow
  - Add quick start for scene generation
- [ ] Test rollback procedure
  - Verify can revert to old prose-writer if needed
  - Document rollback steps
- [ ] Announce deployment
  - New workflow ready for all new scenes
  - Old scenes can be regenerated using new workflow
- [ ] Monitor first 5 scenes in production
  - Watch for unexpected issues
  - Collect feedback
  - Iterate on prompts if needed

**Deliverable**: Fully documented, production-ready, monitored system

**Testing**:
```bash
# Documentation complete
ls .workflows/generation.md
ls .workflows/feat-0001-guide.md
ls .workflows/agents-reference.md

# Monitoring active
# Check metrics dashboard shows real data

# Ready for production use
```

---

## 6. Testing Strategy

### 6.1 Unit Tests (Per Agent)

**blueprint-validator Tests**:

**Test 1: Valid Blueprint v3 → PASS**
```yaml
Input:
  - blueprint: scene-0204-blueprint.md (v3.0, complete)
Expected Output:
  - status: "PASS"
  - constraints-list.json created
  - All fields extracted correctly
```

**Test 2: Missing Required Field → FAIL**
```yaml
Input:
  - blueprint: Missing "Location:" field
Expected Output:
  - status: "FAIL"
  - error: "missing_required_field: Location"
  - fix suggestion provided
```

**Test 3: v2 Blueprint → WARNING**
```yaml
Input:
  - blueprint: Version v2.0 (pre-v3)
Expected Output:
  - status: "PASS" (with warnings)
  - warning: "Blueprint is v2.0, consider upgrading"
  - Constraints extracted (no v3 checks)
```

**Test 4: Internal Contradiction → FAIL**
```yaml
Input:
  - blueprint: Beat 2 mentions "Себастьян", but he's in absent list
Expected Output:
  - status: "FAIL"
  - error: "internal_contradiction"
  - Specific line number and fix suggestion
```

---

**verification-planner Tests**:

**Test 1: Standard Constraints → Readable Plan**
```yaml
Input:
  - constraints-list.json (from blueprint-validator)
Expected Output:
  - verification-plan.md created
  - Contains all sections (location, characters, beats, mechanics)
  - Readable formatting (emojis, structure)
```

**Test 2: User Modification Applied**
```yaml
Input:
  - Original constraints
  - User modification: "Change tone to detached"
Expected Output:
  - Updated verification-plan.md
  - Emotional tone section updated
  - "UPDATED" marker visible
```

---

**prose-writer Tests** (Modified):

**Test 1: Standard Generation (Attempt 1)**
```yaml
Input:
  - verified-plan.json
  - blueprint.md
  - template v2.0
Expected Output:
  - scene-{ID}-draft.md created
  - compliance-echo.json created
  - Metadata returned (NOT full text)
```

**Test 2: Enhanced Generation (Attempt 2)**
```yaml
Input:
  - Same as Attempt 1
  - PLUS: violations from attempt 1
  - Enhanced template with warnings
Expected Output:
  - New draft (does NOT read attempt 1 draft)
  - Violations addressed
  - Compliance-echo shows awareness of constraints
```

---

**blueprint-compliance-fast-checker Tests**:

**Test 1: Compliant Draft → PASS**
```yaml
Input:
  - draft.md (uses correct location, characters, mechanics)
  - constraints-list.json
Expected Output:
  - status: "PASS"
  - All checks PASS
  - Execution time <30 seconds
```

**Test 2: Location Violation → FAIL**
```yaml
Input:
  - draft.md (uses "больница" instead of "Башня Книжников")
  - constraints-list.json
Expected Output:
  - status: "FAIL"
  - violation: "location_match" FAIL
  - retry_guidance provided
```

**Test 3: Character Violation → FAIL**
```yaml
Input:
  - draft.md (includes "Себастьян Грей")
  - constraints-list.json (Себастьян in absent list)
Expected Output:
  - status: "FAIL"
  - violation: "forbidden_characters_absent" FAIL
  - Severity: CRITICAL
```

**Test 4: Scope Violation → FAIL**
```yaml
Input:
  - draft.md (mentions "Диана" - content from scene 0203)
  - constraints-list.json (forbidden_content includes 0203 markers)
Expected Output:
  - status: "FAIL"
  - violation: "scope_boundaries" FAIL
  - Specific content marker identified
```

---

### 6.2 Integration Tests

**Test 1: Full Workflow with Correct Blueprint → Success in 1 Attempt**
```yaml
Setup:
  - Scene 0204 blueprint (v3.0, correct)
Flow:
  1. User: "Generate scene 0204"
  2. blueprint-validator → PASS
  3. verification-planner → plan shown
  4. User: "Y"
  5. prose-writer → draft generated
  6. fast-checker → PASS (1st attempt)
  7. full-validation → PASS
  8. Final output shown
Expected:
  - Total time: 5-7 minutes
  - Attempts: 1
  - No violations
  - Draft file exists and is correct
```

**Test 2: Blueprint with Wrong Location → Auto-Retry → Success in 2 Attempts**
```yaml
Setup:
  - Draft attempt 1 uses "больница"
Flow:
  1-4. Same as Test 1
  5. prose-writer attempt 1 → draft with "больница"
  6. fast-checker → FAIL (location violation)
  7. Coordinator enhances constraints
  8. prose-writer attempt 2 → draft with "Башня Книжников"
  9. fast-checker → PASS
  10. full-validation → PASS
  11. Final output shown
Expected:
  - Total time: 6-8 minutes
  - Attempts: 2
  - Final draft correct
  - User did NOT see attempt 1 failure
```

**Test 3: No Blueprint → Immediate Error**
```yaml
Setup:
  - scene-0299-blueprint.md does NOT exist
Flow:
  1. User: "Generate scene 0299"
  2. Coordinator Step 1 (file check) → NOT FOUND
  3. Error returned immediately
Expected:
  - Error message: "Blueprint not found. Use /plan-scene 0299"
  - No generation attempted
  - Time: <5 seconds
```

**Test 4: User Modifies Verification Plan → Generation Reflects Changes**
```yaml
Setup:
  - Scene 0204 blueprint
Flow:
  1-2. blueprint-validator → PASS
  3. verification-planner → plan shown (tone: "deep compassion")
  4. User: "Change emotional tone to professional detachment"
  5. Coordinator updates constraints
  6. verification-planner → updated plan shown (tone: "professional detachment")
  7. User: "Y"
  8. prose-writer → generates with updated tone
  9-11. validation and output
Expected:
  - Final draft reflects "professional detachment" tone
  - User modification preserved in verified-plan.json
  - Generation used modified plan, not original blueprint
```

---

### 6.3 End-to-End Tests

**E2E Test 1: Scene 0204 Complete Cycle**
```yaml
Objective: Generate scene 0204 from scratch
Input: "Generate scene 0204"
Steps: All 7 steps of workflow
Success Criteria:
  - Blueprint validation PASS
  - User approves verification plan
  - Draft generated (≤2 attempts)
  - Fast-check PASS
  - Full validation: 7/7 PASS
  - Final output clear and complete
  - File: acts/.../scene-0204-draft.md exists
  - Content: 1000-1100 words, all constraints met
Metrics:
  - Time: 5-8 minutes
  - Attempts: 1-2
  - Violations: 0 (final draft)
```

**E2E Test 2: Scene 0205 (New Scene, No Prior Issues)**
```yaml
Objective: Generate new scene with smooth workflow
Input: "Generate scene 0205"
Steps: All 7 steps
Success Criteria:
  - Verification plan clear and accurate
  - First-attempt success (no retries)
  - Time: 5-7 minutes
  - All validations PASS
Metrics:
  - Attempts: 1 (ideal)
  - Time: ≤7 minutes
```

**E2E Test 3: Scene with Contradictory Blueprint → Early Failure**
```yaml
Objective: Test fail-fast on bad blueprint
Setup: Create scene-9999-blueprint.md with:
  - Contradictions (Себастьян in both present and absent lists)
  - Missing location field
Input: "Generate scene 9999"
Steps: Only gets to Step 2
Expected:
  - blueprint-validator → FAIL
  - Errors listed clearly
  - STOP before generation
  - No draft created
  - Time: <1 minute (fail-fast)
```

---

### 6.4 Success Metrics

**Process Efficiency**:
- **Blueprint validation failures**: <10% (most blueprints well-formed)
- **First-attempt success rate**: >80% (prose-writer follows constraints on attempt 1)
- **Auto-retry success rate**: >90% (if attempt 1 fails, attempt 2/3 succeeds)
- **Human escalation rate**: <5% (rarely need manual intervention after 3 attempts)

**Quality**:
- **Constraint compliance**: 100% (final drafts ALWAYS meet constraints)
- **Validation pass rate**: >95% (drafts pass full validation)
- **Scope violation rate**: 0% (no content bleed from other scenes)

**Performance**:
- **Average time per scene**: 5-8 minutes (including user approval ~30 sec)
- **Time variance**: <20% (predictable timing)
- **Fast-check speed**: <30 seconds (meets target)
- **Blueprint validation speed**: <20 seconds (meets target)

**User Experience**:
- **Verification plan clarity**: 100% comprehensible (author understands plan)
- **Transparency**: Author knows what's happening at each step
- **Control**: Author can modify plan before generation
- **Confidence**: No unexpected results (no violations in final draft)

**Comparison to Before** (baseline from manual regenerations):
- **Regenerations needed**: Before: 30-50%, After: <10%
- **Time to correct draft**: Before: 10-15 min (with regen), After: 5-8 min
- **Author frustration**: Before: High (manual fixes), After: Low (automatic)

---

## 7. Open Implementation Questions

### Q1: Verification Plan Modification Limits
**Question**: Should there be a limit on how many times a user can modify the verification plan before regenerating the blueprint?

**Current Approach**: No limit, allow infinite modifications

**Concern**: User might get stuck in modification loop, losing time

**Proposed Resolution**:
- After 5 modifications, coordinator suggests: "Consider updating the blueprint instead of modifying the plan multiple times."
- User can still continue modifying (not enforced)
- Tracks modification count in verified-plan.json

**Needs Decision**: Accept proposed resolution? Or set hard limit (e.g., max 10 modifications)?

---

### Q2: Fast-Checker False Positive Handling
**Question**: What should happen if fast-checker gives a false positive (marks compliant draft as FAIL)?

**Current Approach**: After 3 regenerations with same violation, escalate to human

**Concern**: User might review and find draft is actually correct, wasting time

**Proposed Resolution**:
- Add "override" option in escalation message:
  - "Fast-checker detected violations after 3 attempts."
  - "Options: 1) Manual review (I'll check the draft), 2) Skip fast-checker and proceed to full validation, 3) Abort"
- If user chooses option 2: Skip fast-checker, go straight to full validation

**Needs Decision**: Is override option necessary? Or trust that 3 attempts + full validation will catch actual issues?

---

### Q3: Validation Aggregator Timeout Handling
**Question**: If 1-2 of the 7 validators timeout (take >120 seconds), should the workflow:
a) FAIL and require regeneration?
b) WARN but proceed with results from 5-6 validators?
c) Retry timed-out validators once?

**Current Approach** (from Part 1): Treat timeout as WARNING, proceed with available results

**Concern**: Missing critical validator (e.g., canon-guardian times out) might allow canon violations

**Proposed Resolution**:
- Define "critical" vs "non-critical" validators:
  - **Critical**: canon-guardian, world-lorekeeper, character-state
  - **Non-critical**: dialogue-analyst, scene-structure
- IF critical validator times out → FAIL, retry validator once
- IF non-critical validator times out → WARN, proceed

**Needs Decision**: Accept tiered approach? Or simpler rule (all validators critical)?

---

### Q4: Failed Draft Storage
**Question**: Should failed drafts (attempt 1, 2 if attempt 3 succeeds) be deleted or kept?

**Current Approach**: Delete failed attempts, keep only successful draft

**Concern**: Failed drafts might have useful content (e.g., good dialogue, wrong location)

**Proposed Resolution**:
- Keep failed attempts in `workspace/failed-attempts/scene-{ID}/`
- Rename: `attempt1-failed-{violation_type}.md`
- Cleanup: Delete after 7 days (configurable)
- User can manually review if desired

**Needs Decision**: Accept retention with auto-cleanup? Or immediate deletion?

---

### Q5: Verification Plan Auto-Approval
**Question**: For experienced users, should there be an "auto-approve verification plans" mode?

**Current Approach**: Always show plan, always require approval

**Concern**: Experienced users might find this tedious after 20+ scenes

**Proposed Resolution**:
- Add optional flag: `auto_approve_verification=true`
- If set: Skip Step 3 (verification plan shown), auto-approve
- Default: `false` (show plan)
- User can toggle via command or config

**Needs Decision**: Implement auto-approve mode? Or keep mandatory approval for control?

---

### Q6: Context File Selection for prose-writer
**Question**: How should coordinator determine which context files to pass to prose-writer?

**Current Approach** (from Part 1):
- Always: blueprint, verified-plan, previous scene, POV character sheet
- Optional: world-mechanics excerpt (if blueprint mentions specific mechanic)

**Concern**: What if scene involves multiple characters? Or specific world-bible section?

**Proposed Resolution**:
- blueprint-validator extracts "required context" field from blueprint:
  ```markdown
  ## Required Context
  - Characters: Alexa (POV), Reginald
  - World Mechanics: Compensation system, Immersion mechanics
  - World-Bible: Timeline, Reginald backstory
  ```
- Coordinator reads this field, fetches relevant files
- Falls back to defaults if field missing

**Needs Decision**: Accept flexible context selection? Or stick to fixed defaults?

---

### Q7: Retry Constraint Enhancement Algorithm
**Question**: Is the proposed constraint enhancement (Section 2.2) aggressive enough?

**Current Approach**:
- Attempt 1: Standard constraints
- Attempt 2: Add warnings, negative examples
- Attempt 3: ALL CAPS, emojis, 5x repetition

**Concern**: Maybe attempt 2 enhancement isn't strong enough? Should we go straight to "maximum emphasis"?

**Proposed Resolution**:
- Test with scene 0204 (known violations)
- If attempt 2 still fails, adjust enhancement algorithm:
  - Make attempt 2 more aggressive (closer to attempt 3 level)
  - Reserve attempt 3 for "last resort" extreme emphasis
- Monitor success rate, iterate

**Needs Decision**: Test current approach first, adjust based on data? Or pre-emptively strengthen attempt 2?

---

## 8. Next Steps

### Immediate Actions (Before Starting Week 1)

1. **Review and Approve Part 2**:
   - Author reviews this document
   - Approves prompts, schemas, roadmap
   - Answers open questions (Section 7)
   - Provides any modifications needed

2. **Finalize Decisions**:
   - Q1: Modification limit → Decision: {author provides}
   - Q2: Fast-checker override → Decision: {author provides}
   - Q3: Validator timeout handling → Decision: {author provides}
   - Q4: Failed draft storage → Decision: {author provides}
   - Q5: Auto-approve mode → Decision: {author provides}
   - Q6: Context file selection → Decision: {author provides}
   - Q7: Retry enhancement strength → Decision: {author provides}

3. **Set Success Criteria Baselines**:
   - Define acceptable ranges for metrics:
     - Time per scene: 5-8 min target, up to 10 min acceptable?
     - First-attempt success rate: >80% target, >70% acceptable?
     - Auto-retry success rate: >90% target, >80% acceptable?

### Starting Week 1 Implementation

**Prerequisites**:
- Part 2 approved
- Open questions answered
- Success criteria defined

**First Tasks** (Day 1):
1. Create `.claude/agents/generation/blueprint-validator.md`
   - Copy Section 1.1 prompt
   - Adjust based on Q6 decision (context selection)
   - Save file
2. Create `.claude/agents/generation/verification-planner.md`
   - Copy Section 1.2 prompt
   - Adjust based on Q5 decision (auto-approve)
   - Save file
3. Create `.claude/agents/generation/blueprint-compliance-fast-checker.md`
   - Copy Section 1.4 prompt
   - Adjust based on Q2 decision (false positive handling)
   - Save file

**Follow roadmap** (Section 5) week by week.

### Monitoring & Iteration

**After Week 2** (Steps 1-5 working):
- Collect metrics from scene 0204 generation
- Analyze:
  - Did fast-checker catch violations?
  - How many attempts needed?
  - Was retry enhancement effective?
- Adjust:
  - Refine fast-checker sensitivity if needed
  - Strengthen constraint enhancement if attempt 2 fails often
  - Update prompts based on prose-writer behavior

**After Week 3** (Full workflow working):
- Generate 2-3 more scenes
- Track success rates
- Identify patterns:
  - Which constraints violated most often?
  - Which validators find most issues?
  - Where is time being spent?
- Optimize:
  - Add more specific constraints to templates if needed
  - Adjust timeout values if validators too slow/fast
  - Refine verification plan format based on user feedback

**After Week 5** (Production deployment):
- Monitor first 10 scenes
- Compare to success metrics baselines
- If success criteria met:
  - Declare FEAT-0001 complete
  - Archive Part 1 & Part 2 as reference
  - Update CLAUDE.md with final workflow
- If success criteria NOT met:
  - Identify root causes
  - Iterate on prompts/logic
  - Re-test until criteria met

---

## END OF TECHNICAL DESIGN PART 2

**Deliverable**: Implementation-ready specification with:
✅ Prompt templates (copy-paste ready)
✅ Retry logic (state machine + enhancement algorithm)
✅ Artifact schemas (JSON validated)
✅ Integration plan (backward compatible)
✅ Implementation roadmap (5 weeks, detailed)
✅ Testing strategy (unit, integration, E2E)
✅ Success metrics (quantifiable)
✅ Open questions (for author decision)

**Ready for**: Implementation Week 1 (upon author approval)

**Dependencies**: Author answers Section 7 questions before starting Week 1

---

**Version**: 1.0 FINAL
**Date**: 2025-10-31
**Author**: Claude (agent-architect)
**Status**: AWAITING APPROVAL
