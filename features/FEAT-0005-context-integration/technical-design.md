# FEAT-0005: Context Integration After Generation - Technical Design

**Version**: 1.0.0
**Created**: 2025-11-28
**Status**: Technical Design Complete
**Author**: Agent-Architect

---

## Executive Summary

This document defines the complete technical architecture for implementing Step 8: Context Integration After Generation, which extends the current 7-step Generation Workflow to automatically extract and integrate character knowledge, emotional states, and relationship changes into persistent character context files.

**Key Architectural Decisions:**
1. **Two new agents**: `context-extractor` (analysis) and `context-integrator` (application)
2. **Tiered automation**: CRITICAL (always human approval) / SIGNIFICANT (AI suggests, user confirms) / ROUTINE (auto-apply)
3. **Optional trigger**: User prompted after Step 7, can skip if desired
4. **Storage format**: `context/characters/{name}/knowledge-timeline.md` (new file with rich schema)
5. **Integration with FEAT-0003**: Extends planning state MCP with integration status tracking
6. **Safety-first approach**: Snapshots before changes, atomic file operations, rollback capability

---

## 1. System Architecture Overview

### 1.1 Step 8 in Generation Workflow

```
┌────────────────────────────────────────────────────────┐
│           CURRENT WORKFLOW (Steps 1-7)                 │
│                                                        │
│  Step 1: File Check                                   │
│  Step 2: Blueprint Validation                         │
│  Step 3: Verification Plan → HUMAN APPROVAL           │
│  Step 4: Generation (with auto-retry)                 │
│  Step 5: Fast Compliance Check                        │
│  Step 6: Full Validation (7 validators parallel)      │
│  Step 7: Final Output                                 │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│           STEP 8: CONTEXT SYNTHESIS (NEW)              │
│                                                        │
│  Phase 1: Auto-Scan (30s)                             │
│    └─ context-extractor analyzes scene                │
│    └─ Extracts changes with confidence scores         │
│    └─ Classifies: CRITICAL / SIGNIFICANT / ROUTINE    │
│                                                        │
│  Phase 2: Categorized Preview (instant)               │
│    └─ Show diff: what will change in character files  │
│    └─ Color-coded by importance                       │
│                                                        │
│  Phase 3: Interactive Confirmation (30-60s)           │
│    └─ User: Approve All / Reject All / Edit / Skip    │
│    └─ CRITICAL always requires explicit approval      │
│                                                        │
│  Phase 4: Snapshot Creation (2s)                      │
│    └─ Backup current character files before changes   │
│                                                        │
│  Phase 5: Integration (3s)                            │
│    └─ context-integrator applies approved changes     │
│    └─ Atomic file operations with rollback            │
│                                                        │
│  Phase 6: Planning State Update (1s)                  │
│    └─ Mark scene as "integrated" in planning_state    │
│    └─ Update character metadata                       │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
        ✅ CONTEXT INTEGRATION COMPLETE
```

**Total Time:** ~2-3 minutes (including ~30s human approval)

---

## 2. Knowledge Timeline File Format

### 2.1 Schema Design

**File Location:** `context/characters/{character-name}/knowledge-timeline.md`

**Complete Schema:**

```markdown
# Knowledge Timeline: [Character Name]

**Last Updated:** Scene [CCSS] (YYYY-MM-DD)
**Character Status:** [Active/Retired/Deceased]

---

## Pre-Story Knowledge

### World Knowledge (Canon Level 1)
- **[System/Concept Name]**: [What character knows]
  - Source: [How they learned it]
  - Confidence: Certain/Probable/Uncertain
  - Classification: CRITICAL/SIGNIFICANT/ROUTINE

### Personal Knowledge
- **[Personal fact]**: [Description]
  - Source: [Origin]
  - Confidence: Certain
  - Classification: ROUTINE

### Unknown (Plot-Critical)
List of information character does NOT know (for tracking dramatic irony):
- [Hidden information 1]
- [Secret 2]

---

## Chapter [N]: [Chapter Title]

### Scene [CCSS]: [Scene Title]
**Timestamp:** Day X, HH:MM
**Location:** [Where scene takes place]

#### No New Knowledge
[Optional: If scene has no knowledge acquisition]

#### New Knowledge
1. **Item:** [What was learned]
   - **Source:** [From whom/what]
   - **Method:** [Direct observation/Dialogue/Inference/System notification]
   - **Confidence:** Certain/Probable/Uncertain
   - **Classification:** CRITICAL/SIGNIFICANT/ROUTINE
   - **Emotional Impact:** [How character felt about learning this]
   - **Evidence:** "[Direct quote from scene]" (lines XX-YY)

2. **Item:** [Another knowledge item]
   - [... same structure ...]

#### Emotional State Change
**Entry State:** [Emotional state at scene start]
**Exit State:** [Emotional state at scene end]
**Trigger:** [What caused the change]
**Development:** [Narrative significance of this change]

#### Relationship Changes
- **[Target Character Name]**: [Previous relationship] → [New relationship]
  - **Change Type:** Deepening/Straining/Neutral/Breaking
  - **Reason:** [What caused relationship change]
  - **Impact:** [How this affects future interactions]

#### Interactions
- **With:** [Character name]
  - **Type:** [Conversation/Collaboration/Conflict/Observation]
  - **Duration:** [~X minutes]
  - **Location:** [Where]

---

## Metadata

**Statistics:**
- Total knowledge items: [N]
- CRITICAL items: [N]
- SIGNIFICANT items: [N]
- ROUTINE items: [N]
- Emotional arc checkpoints: [N]
- Relationship developments: [N]

**Last Integrated Scene:** [CCSS]
**Integration Status:** ✅ Up to date / ⚠️ Pending updates / ❌ Out of sync

**Navigation:**
- [← Previous Chapter] | [Next Chapter →]
```

### 2.2 Design Rationale

**Per-Scene Granularity:**
- Allows precise tracking of when character learned what
- Supports continuity checking during planning
- Enables "time travel" queries ("What did Alexa know in scene 0204?")

**Evidence Quotes:**
- Validates extraction accuracy
- Provides context for future reference
- Enables debugging when inconsistencies arise

**Confidence Levels:**
- "Certain": Direct observation, explicit dialogue
- "Probable": Reasonable inference from events
- "Uncertain": Speculation, incomplete information

**Classification System:**
- Used for tiered automation (see Section 3)
- Determines approval requirements
- Guides future planning agents

---

## 3. Classification Logic

### 3.1 Three-Tier System

#### CRITICAL (Always Human Approval Required)

**Criteria:**
1. **Life/Death Events:** Learning about character death, severe injury, life-threatening situations
2. **Plot Twists:** Revelations that fundamentally change understanding of the world
3. **New World Elements:** Discovering previously unknown systems, technologies, or mechanics
4. **Identity Changes:** Learning true identity, hidden relationships, secret affiliations
5. **Betrayals:** Discovering someone is a traitor, enemy, or liar
6. **Mission-Critical Information:** Knowledge that directly enables/blocks main plot objectives

**Examples:**
- "Узнала, что дочь Реджинальда жива" → CRITICAL (contradicts assumed death)
- "Узнала об истинной цели системы компенсации" → CRITICAL (plot twist)
- "Узнала о новой технологии клонирования" → CRITICAL (new world element)

#### SIGNIFICANT (AI Suggests, User Confirms)

**Criteria:**
1. **Emotional Breakthroughs:** Major emotional revelations about self or others
2. **Relationship Developments:** Trust building, romantic developments, friendship deepening
3. **Personal History:** Learning about character's past, motivations, traumas
4. **Non-Critical World Details:** Details about existing systems (not fundamentally new)
5. **Strategic Information:** Useful but not mission-critical knowledge
6. **Character Capability Changes:** Learning new skills, overcoming fears

**Examples:**
- "Узнала о смерти дочери Реджинальда" → SIGNIFICANT (emotional context, affects relationship)
- "Видела работу системы компенсации" → SIGNIFICANT (confirms existing knowledge)
- "Научилась доверять Себастьяну" → SIGNIFICANT (relationship development)

#### ROUTINE (Auto-Apply with Notification)

**Criteria:**
1. **Factual World Knowledge:** Learning facts about the world that everyone knows
2. **Procedural Knowledge:** Learning how to do routine tasks
3. **Temporal Information:** Learning dates, times, schedules
4. **Location Knowledge:** Learning about places (not plot-critical)
5. **Social Conventions:** Learning about customs, etiquette, norms
6. **Minor Observations:** Noticing small details without major implications

**Examples:**
- "Узнала что медпалата на 247 этаже" → ROUTINE (location fact)
- "Узнала график работы Себастьяна" → ROUTINE (scheduling info)
- "Узнала как пользоваться новой консолью" → ROUTINE (procedural)

### 3.2 Detection Algorithm

**High-Level Logic:**

```python
def classify_knowledge_item(item, scene_context, world_context):
    """
    Classify knowledge item using multi-stage analysis.

    Returns: (classification: str, confidence: float)
    """
    # Stage 1: Keyword matching
    critical_keywords = [
        "смерть", "убийство", "предательство", "обман", "тайна",
        "истинный", "настоящий", "раскрытие", "секрет",
        "новая технология", "неизвестная система", "скрытая правда"
    ]

    significant_keywords = [
        "эмоциональный", "чувства", "переживание", "отношения",
        "доверие", "привязанность", "прошлое", "травма",
        "мотивация", "цель", "желание"
    ]

    routine_keywords = [
        "расписание", "процедура", "локация", "адрес",
        "факт", "дата", "время", "место"
    ]

    # Stage 2: Semantic checks
    if mentions_death_or_life_threat(item):
        return ("CRITICAL", 0.95)

    if reveals_plot_twist(item, scene_context):
        return ("CRITICAL", 0.90)

    if introduces_new_canon_element(item, world_context):
        return ("CRITICAL", 0.88)

    if affects_character_relationship(item, scene_context):
        return ("SIGNIFICANT", 0.85)

    if reveals_emotional_state(item):
        return ("SIGNIFICANT", 0.80)

    # Stage 3: Keyword scoring
    critical_score = count_keywords(item, critical_keywords)
    significant_score = count_keywords(item, significant_keywords)
    routine_score = count_keywords(item, routine_keywords)

    if critical_score > 0:
        return ("CRITICAL", 0.75 + critical_score * 0.05)
    elif significant_score > 0:
        return ("SIGNIFICANT", 0.70 + significant_score * 0.05)
    elif routine_score > 0:
        return ("ROUTINE", 0.65 + routine_score * 0.05)

    # Stage 4: Conservative default
    return ("SIGNIFICANT", 0.50)  # Default to SIGNIFICANT when uncertain
```

**Confidence Scoring:**
- **0.9-1.0:** High confidence → use classification directly
- **0.7-0.9:** Medium confidence → use classification with user review
- **0.5-0.7:** Low confidence → bump up one level for safety (ROUTINE → SIGNIFICANT)
- **0.0-0.5:** Very low confidence → always classify as CRITICAL (conservative safety)

**Conservative Safety Rule:**
If `classification_confidence < 0.7`, bump classification up one tier:
- ROUTINE → SIGNIFICANT
- SIGNIFICANT → CRITICAL

This ensures that uncertain items always get human review rather than being auto-applied incorrectly.

---

## 4. Agent Specifications

### 4.1 Agent: context-extractor

**File:** `.claude/agents/generation/context-extractor.md`

**Role:** Extract character knowledge, emotional state changes, and relationship developments from generated scene text.

**Inputs:**
- `scene_path`: Path to generated scene file (acts/.../content/scene-NNNN.md)
- `scene_id`: Scene identifier (e.g., "0204")
- `blueprint_path`: Path to scene blueprint for context
- `character_context_dir`: Path to context/characters/ directory

**Responsibilities:**
1. Read generated scene text
2. Identify all characters that appear or are mentioned
3. For each character, extract:
   - New knowledge acquired (facts, information, observations)
   - Emotional state changes (entry state → exit state)
   - Relationship developments (changes in connections with other characters)
   - Interactions/observations (who met whom, where, when)
4. Classify each item as CRITICAL/SIGNIFICANT/ROUTINE using algorithm from Section 3
5. Calculate confidence scores for classifications
6. Extract evidence quotes from scene text (with line numbers)
7. Generate structured extraction report (JSON format)

**Output Format:**

**File:** `workspace/artifacts/scene-{ID}-context-extraction.json`

```json
{
  "scene_id": "0204",
  "scene_path": "acts/act-1/chapters/chapter-02/content/scene-0204.md",
  "extracted_at": "2025-11-28T14:30:00Z",
  "execution_time_seconds": 28.5,
  "characters": [
    {
      "character_name": "Alexa Wright",
      "character_file": "context/characters/alexa-wright/knowledge-timeline.md",
      "file_exists": true,
      "changes": {
        "knowledge_items": [
          {
            "id": "knowledge_1",
            "item": "Узнала о смерти дочери Реджинальда",
            "source": "Witnessed during Memory Dive session",
            "method": "Direct observation",
            "confidence_level": "Certain",
            "classification": "SIGNIFICANT",
            "classification_confidence": 0.92,
            "classification_reasoning": "Emotional context + relationship impact + personal history revelation",
            "emotional_impact": "Empathy breakthrough (professional mask cracks)",
            "evidence": {
              "quote": "Alexa saw the memory fragment: young girl, hospital bed, Reginald's tears...",
              "line_range": "145-148"
            }
          },
          {
            "id": "knowledge_2",
            "item": "System auto-grants +2 months for painful memories",
            "source": "System notification after session",
            "method": "System interface",
            "confidence_level": "Certain",
            "classification": "ROUTINE",
            "classification_confidence": 0.88,
            "classification_reasoning": "Factual system knowledge, routine operation",
            "emotional_impact": "Professional satisfaction (system working as designed)",
            "evidence": {
              "quote": "The console displayed: +2 months life compensation granted automatically",
              "line_range": "210-211"
            }
          }
        ],
        "emotional_state": {
          "id": "emotion_1",
          "previous_state": "Professional detachment, routine work mask",
          "new_state": "Mask with cracks, genuine empathy emerging",
          "trigger": "Witnessing Reginald's profound trauma",
          "classification": "SIGNIFICANT",
          "classification_confidence": 0.88,
          "classification_reasoning": "Major emotional breakthrough, character arc milestone",
          "development": "First moment breaking professional boundaries - marks beginning of humanization arc",
          "evidence": {
            "previous_state_quote": "Alexa maintained her professional detachment, just another session",
            "new_state_quote": "But this time, something cracked. She felt his pain as her own.",
            "line_ranges": "12-15, 198-202"
          }
        },
        "relationships": [
          {
            "id": "relationship_1",
            "target_character": "Reginald Havenford",
            "previous_relationship": "Professional (редактор-клиент)",
            "new_relationship": "Sympathetic professional connection",
            "change_type": "Deepening",
            "reason": "Witnessed his deepest trauma, shared vulnerable moment",
            "impact": "Future interactions will be colored by this shared intimacy",
            "classification": "SIGNIFICANT",
            "classification_confidence": 0.85,
            "classification_reasoning": "Relationship development that affects future story beats",
            "evidence": {
              "quote": "In that moment, they weren't editor and client. They were two souls touching across grief.",
              "line_range": "203-205"
            }
          }
        ],
        "interactions": [
          {
            "id": "interaction_1",
            "with_character": "Reginald Havenford",
            "interaction_type": "Memory Dive session",
            "duration": "~30 minutes",
            "location": "Медпалата, Башня Книжников, 247 этаж",
            "classification": "ROUTINE",
            "notes": "Professional session with emotional turning point"
          }
        ]
      }
    },
    {
      "character_name": "Reginald Havenford",
      "character_file": "context/characters/reginald-havenford/knowledge-timeline.md",
      "file_exists": false,
      "warning": "Character file not found - will be created on integration",
      "changes": {
        "interactions": [
          {
            "id": "interaction_1",
            "with_character": "Alexa Wright",
            "interaction_type": "Memory Dive session (received)",
            "duration": "~30 minutes",
            "location": "Медпалата, Башня Книжников",
            "classification": "ROUTINE",
            "notes": "Relived traumatic memory of daughter's death"
          }
        ]
      }
    }
  ],
  "statistics": {
    "total_characters": 2,
    "total_changes": 5,
    "critical_changes": 0,
    "significant_changes": 3,
    "routine_changes": 2,
    "characters_with_knowledge": 1,
    "characters_with_emotions": 1,
    "characters_with_relationships": 1
  },
  "warnings": [
    "Character 'Reginald Havenford' file not found - will create on integration"
  ]
}
```

**Error Handling:**
- If scene file not found → return error with clear message
- If character not in context/ → create warning, continue extraction (file will be created on integration)
- If cannot classify → default to SIGNIFICANT (conservative approach)
- If evidence quote not found → log warning, continue without quote

**Context Provided:**
- **Minimal:** Only scene text + blueprint + character list from world-bible
- **DO NOT** read full world-bible or other contexts (agent isolation principle)

---

### 4.2 Agent: context-integrator

**File:** `.claude/agents/generation/context-integrator.md`

**Role:** Apply approved context changes to character knowledge timelines and related files.

**Inputs:**
- `extraction_report_path`: Path to context-extraction.json from context-extractor
- `approved_changes`: JSON object containing only user-approved changes (may be subset of extraction)
- `character_context_dir`: Path to context/characters/ directory
- `scene_id`: Scene identifier for logging

**Responsibilities:**
1. Read extraction report
2. Filter to only approved changes (user may have rejected some items)
3. Create snapshot directory and backup all files to be modified
4. For each character:
   - Read existing knowledge-timeline.md (or create if doesn't exist)
   - Apply changes in correct chronological order (by scene ID)
   - Maintain markdown formatting and structure
   - Update metadata section (statistics, last integrated scene, timestamp)
5. Write updated files atomically (write to temp → move to target)
6. Verify changes applied correctly (file exists, reasonable size, valid markdown)
7. Generate integration report

**Output Format:**

**File:** `workspace/artifacts/scene-{ID}-integration-report.md`

```markdown
# Integration Report: Scene 0204

**Execution Time:** 2025-11-28T14:35:22Z
**Duration:** 2.3 seconds
**Scene:** acts/act-1/chapters/chapter-02/content/scene-0204.md

---

## Files Modified

### 1. context/characters/alexa-wright/knowledge-timeline.md
**Status:** ✅ Updated successfully

**Changes Applied:** 3
1. Added knowledge item: "Узнала о смерти дочери Реджинальда" (SIGNIFICANT)
2. Updated emotional state: "Professional detachment" → "Mask with cracks" (SIGNIFICANT)
3. Added relationship change: Reginald Havenford (Professional → Sympathetic) (SIGNIFICANT)

**Statistics Updated:**
- Total knowledge items: 5 → 7 (+2)
- SIGNIFICANT items: 2 → 4 (+2)
- Emotional arc checkpoints: 3 → 4 (+1)

**Backup Created:**
- workspace/snapshots/scene-0204-pre-integration/alexa-wright-knowledge-timeline-2025-11-28T14-35-20.md

---

### 2. context/characters/reginald-havenford/knowledge-timeline.md
**Status:** ✅ Created (new character file)

**Changes Applied:** 1
1. Added interaction: Memory Dive session with Alexa Wright (ROUTINE)

**File Structure:**
- Pre-Story Knowledge section created
- Chapter 1 section created
- Scene 0204 section populated
- Metadata section initialized

**Backup Created:** N/A (new file, no previous version)

---

## Summary

**Total Characters Updated:** 2
- Alexa Wright: 3 changes applied
- Reginald Havenford: 1 change applied (new file created)

**Total Changes Applied:** 4
- CRITICAL changes: 0
- SIGNIFICANT changes: 3
- ROUTINE changes: 1

**Execution Status:** ✅ SUCCESS
- All files updated successfully
- All backups created
- Markdown structure validated
- Planning state update pending (Phase 6)

---

## Next Steps

✅ **Updated contexts will be used in next planning session**
- Character states accurate as of Scene 0204
- Emotional arcs reflect recent developments
- Relationship dynamics updated

💡 **Recommendations:**
- Review character emotional arcs after Chapter 2 completion
- Consider planning scene 0205 with updated Alexa-Reginald relationship context
- Monitor Alexa's humanization arc progression

---

**Integration completed successfully at 2025-11-28T14:35:22Z**
```

**File Operations (Detailed):**

1. **Snapshot Creation:**
   ```
   workspace/snapshots/scene-{ID}-pre-integration/
   ├── {character-1}-knowledge-timeline-{timestamp}.md
   ├── {character-2}-knowledge-timeline-{timestamp}.md
   └── ...
   ```

2. **Atomic Write Process:**
   ```python
   # Pseudo-code for atomic write
   def apply_changes_atomically(file_path, changes):
       # 1. Read entire file
       content = read_file(file_path)

       # 2. Apply transformations in memory
       new_content = apply_transformations(content, changes)

       # 3. Write to temp file in same directory
       temp_path = f"{file_path}.tmp.{timestamp}"
       write_file(temp_path, new_content)

       # 4. Verify temp file written correctly
       if not verify_file(temp_path):
           delete_file(temp_path)
           raise IntegrationError("Temp file verification failed")

       # 5. Atomic move (replaces target)
       move_file(temp_path, file_path)  # Atomic operation on most filesystems

       # 6. Final verification
       if not verify_file(file_path):
           # Rollback from snapshot
           restore_from_snapshot(file_path)
           raise IntegrationError("Final verification failed, rolled back")
   ```

3. **Verification Checks:**
   - File exists after write
   - File size reasonable (>0 bytes, <10MB)
   - Markdown structure valid (has headers, no broken syntax)
   - Required sections present (# Knowledge Timeline, ## Metadata)

**Error Handling:**
- If file write fails → rollback from snapshot, return error details
- If file read fails → report error, continue with other characters
- If markdown parse fails → warn user but write anyway (manual fix possible)
- If snapshot creation fails → ABORT integration, don't proceed

**Context Provided:**
- **Minimal:** Only extraction report + character context files being modified
- **DO NOT** read scene text or blueprint (not needed for integration)

---

## 5. User Interaction Flow

### 5.1 Optional Prompt After Step 7

```
┌────────────────────────────────────────────────────────┐
│  [STEP 7 COMPLETES]                                    │
│  ✅ СЦЕНА 0204 ГОТОВА                                  │
│  📄 File: acts/act-1/.../scene-0204.md                 │
│  📊 Validation: 7/7 PASSED                             │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  [STEP 8 OPTIONAL PROMPT]                              │
│                                                        │
│  Обновить контексты персонажей для сцены 0204?        │
│                                                        │
│  Это добавит Step 8: Context Synthesis (~2-3 мин)     │
│  который:                                              │
│  • Извлечёт изменения персонажей                       │
│  • Покажет предпросмотр обновлений                     │
│  • Применит изменения после вашего одобрения           │
│                                                        │
│  [Y/Enter] Да, интегрировать изменения                │
│  [N]       Нет, пропустить интеграцию                 │
│  [L]       Later - сохранить на потом (создать задачу) │
└────────────────────────────────────────────────────────┘
```

**User Options:**

**Option Y (Yes):** Proceed with Step 8
```
User: Y

⏳ Анализирую сцену 0204...
[Proceeds to Phase 1: Auto-Scan]
```

**Option N (No):** Skip Step 8 entirely
```
User: N

ℹ️  Интеграция пропущена

Контексты персонажей НЕ обновлены.
Вы можете интегрировать позже командой:
  /integrate-scene 0204

🎯 ЧТО ДАЛЬШЕ?
[Shows next steps as usual]
```

**Option L (Later):** Defer to batch processing
```
User: L

💾 Сохранено на потом

Создана задача: workspace/pending-integrations/scene-0204.json

Вы можете интегрировать позже:
  • Одну сцену: /integrate-pending 0204
  • Все сцены: /integrate-pending --all

[Proceeds to next steps]
```

### 5.2 Phase 2: Diff Preview Interface

```
═══════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ КОНТЕКСТА - СЦЕНА 0204
═══════════════════════════════════════════════════════════

📊 СТАТИСТИКА:
- Персонажей затронуто: 2 (Alexa Wright, Reginald Havenford)
- 🔴 КРИТИЧНО: 0 изменений
- 🟡 ЗНАЧИМО: 3 изменения (требуют подтверждения)
- 🟢 РУТИННО: 2 изменения (будут применены автоматически)

───────────────────────────────────────────────────────────
👤 ПЕРСОНАЖ: Alexa Wright
───────────────────────────────────────────────────────────

🟡 ЗНАЧИМОЕ ИЗМЕНЕНИЕ #1: Новое знание
  ✅ ДЕЙСТВИЕ: Добавить в knowledge-timeline
  📝 ЧТО: Узнала о смерти дочери Реджинальда
  📍 ГДЕ: Сцена 0204
  🔍 КАК: Witnessed during Memory Dive session
  💯 УВЕРЕННОСТЬ: Certain
  💔 ЭМОЦИЯ: Empathy breakthrough
  📊 AI CONFIDENCE: 92%

  📄 ДОКАЗАТЕЛЬСТВО:
  "Alexa saw the memory fragment: young girl, hospital bed,
   Reginald's tears washed over her like a wave"
  (lines 145-148)

🟡 ЗНАЧИМОЕ ИЗМЕНЕНИЕ #2: Эмоциональное состояние
  ✅ ДЕЙСТВИЕ: Обновить emotional arc

  БЫЛО: "Professional detachment, routine work mask"
  СТАНЕТ: "Mask with cracks, genuine empathy emerging"

  📝 ТРИГГЕР: Witnessing Reginald's profound trauma
  📝 РАЗВИТИЕ: First moment breaking professional boundaries
  💡 ВАЖНОСТЬ: Character arc milestone - humanization begins
  📊 AI CONFIDENCE: 88%

🟡 ЗНАЧИМОЕ ИЗМЕНЕНИЕ #3: Отношения
  ✅ ДЕЙСТВИЕ: Обновить relationships

  С КЕМ: Reginald Havenford
  БЫЛО: "Professional (редактор-клиент)"
  СТАНЕТ: "Sympathetic professional connection"

  📝 ПРИЧИНА: Witnessed his deepest trauma, shared vulnerable moment
  💡 ВЛИЯНИЕ: Future interactions will be colored by this intimacy
  📊 AI CONFIDENCE: 85%

🟢 РУТИННОЕ ИЗМЕНЕНИЕ #1: Факт о системе
  ✅ ДЕЙСТВИЕ: Добавить (auto-applied)

  📝 ЧТО: System auto-grants +2 months for painful memories
  📍 ГДЕ: Сцена 0204
  🔍 КАК: System notification

  ℹ️  Это рутинное изменение будет применено автоматически

🟢 РУТИННОЕ ИЗМЕНЕНИЕ #2: Взаимодействие
  ✅ ДЕЙСТВИЕ: Добавить interaction log (auto-applied)

  📝 ВЗАИМОДЕЙСТВИЕ: Memory Dive session with Reginald
  ⏱️  ПРОДОЛЖИТЕЛЬНОСТЬ: ~30 minutes
  📍 ЛОКАЦИЯ: Медпалата, Башня Книжников

───────────────────────────────────────────────────────────
👤 ПЕРСОНАЖ: Reginald Havenford
───────────────────────────────────────────────────────────

⚠️  ФАЙЛ НЕ НАЙДЕН: knowledge-timeline.md will be created

🟢 РУТИННОЕ ИЗМЕНЕНИЕ #1: Interaction log
  ✅ ДЕЙСТВИЕ: Создать файл + добавить (auto-applied)

  📝 ВЗАИМОДЕЙСТВИЕ: Memory Dive session with Alexa Wright
  ⏱️  ПРОДОЛЖИТЕЛЬНОСТЬ: ~30 minutes

  ℹ️  Будет создан новый файл для персонажа

═══════════════════════════════════════════════════════════

КОМАНДЫ:
[A] Approve All      - Применить все изменения (3 ЗНАЧИМЫХ требуют подтверждения)
[R] Reject All       - Отменить всю интеграцию
[E] Edit             - Редактировать отдельные изменения
[S] Skip SIGNIFICANT - Применить только РУТИННЫЕ, остальное вручную позже
[?] Подробности      - Показать подробный анализ с полными цитатами

Ваш выбор: _
```

### 5.3 User Flow Options

#### Option A: Approve All

```
User: A

⏳ Создаю snapshot...
✓ Snapshot created: workspace/snapshots/scene-0204-pre-integration/

⏳ Применяю изменения...
✓ Alexa Wright: knowledge-timeline.md обновлён (+3 items)
✓ Alexa Wright: emotional arc записан
✓ Reginald Havenford: knowledge-timeline.md создан (+1 interaction)

✓ Обновляю planning state...

✅ ИНТЕГРАЦИЯ ЗАВЕРШЕНА

Обновлено файлов: 2
- context/characters/alexa-wright/knowledge-timeline.md
- context/characters/reginald-havenford/knowledge-timeline.md

Изменений применено: 5
- SIGNIFICANT: 3
- ROUTINE: 2

Создан snapshot: workspace/snapshots/scene-0204-pre-integration/
Execution time: 2.3 seconds

───────────────────────────────────────────────────────────
📊 INTEGRATION REPORT
───────────────────────────────────────────────────────────
[Shows full integration-report.md content]

🎯 ЧТО ДАЛЬШЕ?
- Генерировать сцену 0205?
- Планировать следующую сцену?
- Завершить работу?
```

#### Option R: Reject All

```
User: R

❌ ИНТЕГРАЦИЯ ОТМЕНЕНА

Никакие изменения НЕ применены.
Контексты персонажей остались без изменений.

ℹ️  Вы можете вернуться к интеграции позже:
  /integrate-scene 0204

🎯 ЧТО ДАЛЬШЕ?
[Shows standard next steps]
```

#### Option E: Edit Individual Items

```
User: E

Какое изменение редактировать? (номер)

ALEXA WRIGHT:
1. Знание о смерти дочери (SIGNIFICANT) - AI confidence 92%
2. Эмоциональное состояние (SIGNIFICANT) - AI confidence 88%
3. Отношения с Reginald (SIGNIFICANT) - AI confidence 85%
4. Факт о системе (ROUTINE, auto) - AI confidence 88%
5. Взаимодействие (ROUTINE, auto) - AI confidence 95%

REGINALD HAVENFORD:
6. Взаимодействие (ROUTINE, auto) - AI confidence 95%

[B] Back to preview
[A] Approve current changes and continue

Ваш выбор: _

User: 2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
РЕДАКТИРОВАНИЕ: Alexa - Эмоциональное состояние
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AI ПРЕДЛОЖЕНИЕ:
БЫЛО: "Professional detachment, routine work mask"
СТАНЕТ: "Mask with cracks, genuine empathy emerging"

РАЗВИТИЕ: First moment breaking professional boundaries

AI CONFIDENCE: 88%

ОПЦИИ:
[A] Accept           - Принять как есть
[M] Modify           - Изменить формулировку
[I] Increase Impact  - Усилить изменение (bigger emotional shift)
[D] Decrease Impact  - Ослабить изменение (more subtle change)
[R] Reject           - Не применять это изменение вообще
[C] Cancel           - Вернуться к списку

Ваш выбор: _

User: D

ОСЛАБЛЕННОЕ ИЗМЕНЕНИЕ:
БЫЛО: "Professional detachment, routine work mask"
СТАНЕТ: "Professional detachment with subtle empathy undercurrent"

РАЗВИТИЕ: First subtle crack in professional boundaries, not yet breaking

Сохранить это изменение? [Y/n]: Y

✓ Изменение сохранено

Вернуться к списку? [Y/n]: Y

[Shows updated change list with modified item marked as "✏️ EDITED"]
```

#### Option S: Skip SIGNIFICANT

```
User: S

⏳ Применяю только РУТИННЫЕ изменения...

✓ Alexa Wright: Факт о системе добавлен (auto-applied)
✓ Alexa Wright: Взаимодействие добавлено (auto-applied)
✓ Reginald Havenford: Взаимодействие добавлено, файл создан (auto-applied)

✅ РУТИННЫЕ ИЗМЕНЕНИЯ ПРИМЕНЕНЫ (2 изменения)

⚠️  ОТЛОЖЕНО НА ПОТОМ (3 SIGNIFICANT изменения):
1. Alexa - Знание о смерти дочери
2. Alexa - Эмоциональное состояние
3. Alexa - Отношения с Reginald

💾 Создана задача: workspace/pending-integrations/scene-0204-significant-changes.json

Вы можете интегрировать эти изменения позже командой:
  /integrate-pending 0204

───────────────────────────────────────────────────────────
📊 PARTIAL INTEGRATION REPORT
───────────────────────────────────────────────────────────

Обновлено файлов: 2
Изменений применено: 2 (ROUTINE only)
Отложено: 3 (SIGNIFICANT)

[Shows abbreviated report]

🎯 ЧТО ДАЛЬШЕ?
[Shows next steps]
```

---

## 6. Integration with FEAT-0003 (Hierarchical Planning)

### 6.1 Planning State Extensions

**New MCP Tools:**

```python
# Add to planning_state_mcp.py (existing MCP server)

def update_scene_integration_status(scene_id: str, status: str,
                                    characters_updated: List[str],
                                    changes_count: int) -> dict:
    """
    Update scene entity with integration metadata.

    Args:
        scene_id: Scene identifier (e.g., "scene-0204")
        status: Integration status ("integrated", "pending", "skipped")
        characters_updated: List of character IDs affected
        changes_count: Total number of changes applied

    Returns:
        {"success": bool, "message": str}
    """
    # Update scene metadata in planning_entities table
    db.execute("""
        UPDATE planning_entities
        SET metadata = json_set(
            metadata,
            '$.integration_status', ?,
            '$.integration_timestamp', ?,
            '$.characters_updated', ?,
            '$.context_changes_count', ?
        )
        WHERE entity_type = 'scene' AND entity_id = ?
    """, (status, now(), json.dumps(characters_updated), changes_count, scene_id))

    return {"success": True, "message": f"Scene {scene_id} integration status updated"}


def get_integration_pending_scenes(act_id: str = None) -> List[dict]:
    """
    Get list of scenes with integration_status = 'pending'.

    Args:
        act_id: Optional filter by act (e.g., "act-1")

    Returns:
        List of scene entities with pending integration
    """
    query = """
        SELECT entity_id, file_path, created_at
        FROM planning_entities
        WHERE entity_type = 'scene'
        AND json_extract(metadata, '$.integration_status') = 'pending'
    """

    if act_id:
        # Extract act number from act_id (e.g., "act-1" → "01")
        act_num = act_id.split("-")[1].zfill(2)
        query += f" AND entity_id LIKE 'scene-{act_num}%'"

    query += " ORDER BY entity_id"

    return db.execute(query).fetchall()


def get_integration_status_summary(act_id: str = None) -> dict:
    """
    Get summary of integration status across scenes.

    Args:
        act_id: Optional filter by act

    Returns:
        Statistics about integration status
    """
    query = """
        SELECT
            COUNT(*) as total_scenes,
            SUM(CASE WHEN json_extract(metadata, '$.integration_status') = 'integrated' THEN 1 ELSE 0 END) as integrated,
            SUM(CASE WHEN json_extract(metadata, '$.integration_status') = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN json_extract(metadata, '$.integration_status') = 'skipped' THEN 1 ELSE 0 END) as skipped,
            SUM(CASE WHEN json_extract(metadata, '$.integration_status') IS NULL THEN 1 ELSE 0 END) as not_started
        FROM planning_entities
        WHERE entity_type = 'scene'
    """

    if act_id:
        act_num = act_id.split("-")[1].zfill(2)
        query += f" AND entity_id LIKE 'scene-{act_num}%'"

    result = db.execute(query).fetchone()

    return {
        "total_scenes": result["total_scenes"],
        "integrated": result["integrated"],
        "pending": result["pending"],
        "skipped": result["skipped"],
        "not_started": result["not_started"],
        "completion_percentage": round((result["integrated"] / result["total_scenes"]) * 100, 1) if result["total_scenes"] > 0 else 0
    }
```

### 6.2 Scene Entity Metadata Schema Extension

**SQLite Schema Update:**

```sql
-- No schema changes needed, using JSON metadata field

-- Example scene entity with integration metadata:
UPDATE planning_entities
SET metadata = json_object(
    'integration_status', 'integrated',
    'integration_timestamp', '2025-11-28T14:35:22Z',
    'characters_updated', json_array('alexa-wright', 'reginald-havenford'),
    'context_changes_count', 5,
    'integration_report_path', 'workspace/artifacts/scene-0204-integration-report.md'
)
WHERE entity_type = 'scene' AND entity_id = 'scene-0204';
```

### 6.3 Coordination Flow with Planning State

```
[Step 7: Final Output]
generation-coordinator completes scene 0204

[Step 8 Optional Prompt]
coordinator: "Обновить контексты?"

[User: Y]

[Phase 1: Extract]
context-extractor analyzes scene → extraction.json

[Phase 2: Review]
coordinator shows diff, user approves

[Phase 3: Snapshot]
Create backups in workspace/snapshots/

[Phase 4: Integrate]
context-integrator applies changes → integration-report.md

[Phase 5: Update Planning State]  ← NEW INTEGRATION POINT
coordinator calls MCP:
  update_scene_integration_status(
    scene_id="scene-0204",
    status="integrated",
    characters_updated=["alexa-wright", "reginald-havenford"],
    changes_count=5
  )

[Step 8 Complete]
coordinator: "✅ КОНТЕКСТЫ ОБНОВЛЕНЫ"
```

### 6.4 New Command: /show-integration-status

**File:** `.claude/commands/show-integration-status.md`

**Usage:** `/show-integration-status [--act <N>]`

**Example Output:**

```
═══════════════════════════════════════════════════════════
СТАТУС ИНТЕГРАЦИИ: АКТ 1
═══════════════════════════════════════════════════════════

Глава 1:
  ✅ scene-0101: Integrated (2025-11-25 14:30) - 2 characters, 3 changes
  ✅ scene-0102: Integrated (2025-11-26 10:15) - 2 characters, 5 changes
  ✅ scene-0103: Integrated (2025-11-27 16:45) - 1 character, 2 changes
  ✅ scene-0104: Integrated (2025-11-27 18:20) - 3 characters, 7 changes

Глава 2:
  ✅ scene-0201: Integrated (2025-11-28 09:30) - 2 characters, 4 changes
  ✅ scene-0202: Integrated (2025-11-28 11:00) - 3 characters, 6 changes
  ⏸️  scene-0203: Pending integration (generated 2025-11-28 13:45)
  📝 scene-0204: Not started (draft blueprint)
  📝 scene-0205: Not started (draft blueprint)

ОБЩАЯ СТАТИСТИКА:
════════════════════════════════════════════════════════════
Всего сцен:              9
Интегрировано:           6 (66.7%)
Ожидают интеграции:      1 (11.1%)
Пропущено:               0 (0.0%)
Не начато:               2 (22.2%)

Всего обновлений:        27 changes across 6 scenes
Персонажей затронуто:    5 unique characters
Средняя длина интеграции: 2.1 minutes

════════════════════════════════════════════════════════════

⚠️  ВНИМАНИЕ:
Сцена 0203 требует интеграции перед планированием 0204.
Рекомендуется: /integrate-pending 0203

КОМАНДЫ:
  /integrate-pending 0203       - Интегрировать scene 0203
  /integrate-pending --all      - Интегрировать все pending scenes
  /show-integration-status      - Обновить этот статус
```

### 6.5 Planning Workflow Integration

**When planning next scene:**

```python
# In planning-coordinator agent

def plan_scene(scene_id):
    # 1. Check previous scene integration status
    prev_scene_id = get_previous_scene_id(scene_id)

    if prev_scene_id:
        prev_scene_state = get_entity_state("scene", prev_scene_id)
        integration_status = prev_scene_state.get("metadata", {}).get("integration_status")

        if integration_status == "pending":
            warning = f"""
            ⚠️  ПРЕДУПРЕЖДЕНИЕ: Предыдущая сцена {prev_scene_id} не интегрирована

            Рекомендуется интегрировать контексты перед планированием {scene_id},
            чтобы учесть актуальное состояние персонажей.

            ОПЦИИ:
            [I] Интегрировать {prev_scene_id} сейчас (recommended)
            [C] Продолжить без интеграции (not recommended)
            [A] Отменить планирование
            """

            user_choice = ask_user(warning)

            if user_choice == "I":
                # Trigger integration for previous scene
                integrate_scene(prev_scene_id)
            elif user_choice == "A":
                return  # Abort planning

    # 2. Read current character states from knowledge-timelines
    characters = get_characters_for_scene(scene_id)

    for char in characters:
        timeline_path = f"context/characters/{char}/knowledge-timeline.md"
        if file_exists(timeline_path):
            current_knowledge = read_knowledge_timeline(timeline_path)
            # Inject into planning context
            inject_character_state(char, current_knowledge)

    # 3. Proceed with planning phases 1-5
    ...
```

---

## 7. Error Handling & Rollback

### 7.1 Snapshot Mechanism

**Directory Structure:**

```
workspace/snapshots/
└── scene-{ID}-pre-integration/
    ├── alexa-wright-knowledge-timeline-{timestamp}.md
    ├── reginald-havenford-knowledge-timeline-{timestamp}.md
    ├── snapshot-metadata.json
    └── ...
```

**Snapshot Metadata:**

```json
{
  "scene_id": "0204",
  "created_at": "2025-11-28T14:35:20Z",
  "files_backed_up": [
    {
      "original_path": "context/characters/alexa-wright/knowledge-timeline.md",
      "backup_path": "workspace/snapshots/scene-0204-pre-integration/alexa-wright-knowledge-timeline-2025-11-28T14-35-20.md",
      "file_hash": "a7f3b9d2c8e1f4..."
    },
    {
      "original_path": "context/characters/reginald-havenford/knowledge-timeline.md",
      "backup_path": "workspace/snapshots/scene-0204-pre-integration/reginald-havenford-knowledge-timeline-2025-11-28T14-35-20.md",
      "file_hash": null,
      "note": "File did not exist, created new"
    }
  ],
  "integration_report_path": "workspace/artifacts/scene-0204-integration-report.md",
  "extraction_report_path": "workspace/artifacts/scene-0204-context-extraction.json"
}
```

### 7.2 Rollback Procedure

**Triggered By:**
- File write failure during integration
- User manual rollback request (`/rollback-integration 0204`)
- Verification failure after integration

**Rollback Steps:**

```python
def rollback_integration(scene_id):
    """
    Rollback integration by restoring from snapshot.
    """
    snapshot_dir = f"workspace/snapshots/scene-{scene_id}-pre-integration"

    # 1. Check snapshot exists
    if not exists(snapshot_dir):
        raise RollbackError("Snapshot not found - cannot rollback")

    # 2. Read snapshot metadata
    metadata_path = f"{snapshot_dir}/snapshot-metadata.json"
    metadata = read_json(metadata_path)

    # 3. Restore each file
    for file_info in metadata["files_backed_up"]:
        original_path = file_info["original_path"]
        backup_path = file_info["backup_path"]

        if file_info.get("note") == "File did not exist, created new":
            # Delete newly created file
            if exists(original_path):
                delete_file(original_path)
                log(f"Deleted newly created file: {original_path}")
        else:
            # Restore from backup
            copy_file(backup_path, original_path)
            log(f"Restored {original_path} from snapshot")

    # 4. Update planning state
    update_scene_integration_status(
        scene_id=f"scene-{scene_id}",
        status="pending",  # Mark as pending again
        characters_updated=[],
        changes_count=0
    )

    # 5. Clean up integration artifacts
    delete_file(metadata["integration_report_path"])

    return {
        "success": True,
        "message": f"Integration for scene {scene_id} rolled back successfully",
        "files_restored": len(metadata["files_backed_up"])
    }
```

### 7.3 Error Scenarios & Handling

| Error Scenario | Handling Strategy | User Impact |
|----------------|-------------------|-------------|
| **Extraction fails** | Return error, don't proceed to integration | User sees error, no files modified |
| **File write fails** | Automatic rollback from snapshot | User sees error, files restored to pre-integration state |
| **Snapshot creation fails** | ABORT integration before any changes | User sees error, integration cancelled safely |
| **Markdown parse fails** | Warn user, write anyway (manual fix possible) | Integration proceeds with warning |
| **Missing character file** | Create new file with default structure | New character file created (logged in report) |
| **Concurrent integration** | Queue integration, process sequentially | Second integration waits for first to complete |
| **MCP state update fails** | Log warning, continue (file changes still applied) | Integration succeeds, state may be out of sync |
| **Verification fails** | Automatic rollback, return error | User sees error, files restored |

### 7.4 Transaction Semantics

**File Operation Guarantees:**

1. **Atomicity:** Either all files updated or none (via snapshot rollback)
2. **Consistency:** Markdown structure validated before/after
3. **Isolation:** Snapshots prevent concurrent modification conflicts
4. **Durability:** Changes flushed to disk before completion

**Implementation Pattern:**

```python
def integrate_with_transaction(extraction, approved_changes):
    """
    Integrate changes with full transaction semantics.
    """
    # BEGIN TRANSACTION
    snapshot = None

    try:
        # 1. Create snapshot (commit point 1)
        snapshot = create_snapshot(extraction["scene_id"])

        # 2. Apply changes to temp files
        temp_files = []
        for character in approved_changes["characters"]:
            temp_file = apply_changes_to_temp(character)
            temp_files.append(temp_file)

        # 3. Verify all temp files
        for temp_file in temp_files:
            if not verify_file(temp_file):
                raise IntegrationError(f"Verification failed: {temp_file}")

        # 4. Atomic move temp → target (commit point 2)
        for temp_file in temp_files:
            atomic_move(temp_file, get_target_path(temp_file))

        # 5. Update planning state (commit point 3)
        update_planning_state(extraction["scene_id"], "integrated")

        # COMMIT
        return {"success": True, "snapshot": snapshot}

    except Exception as e:
        # ROLLBACK
        if snapshot:
            rollback_from_snapshot(snapshot)

        # Clean up temp files
        cleanup_temp_files()

        return {"success": False, "error": str(e)}
```

---

## 8. Implementation Phases

### Phase 1: Foundation - MCP Extensions & Agent Creation (Week 1)

**Deliverables:**
- [ ] Extend `planning_state_mcp.py` with integration status tracking
- [ ] Implement new MCP tools: `update_scene_integration_status`, `get_integration_pending_scenes`, `get_integration_status_summary`
- [ ] Update SQLite metadata usage (no schema changes, uses existing JSON field)
- [ ] Create `context-extractor` agent specification file
- [ ] Create `context-integrator` agent specification file
- [ ] Unit tests for MCP tools (pytest)

**Files Created/Modified:**
- `mcp-servers/planning_state_mcp.py` (extend existing)
- `.claude/agents/generation/context-extractor.md` (new)
- `.claude/agents/generation/context-integrator.md` (new)
- `mcp-servers/tests/test_integration_status.py` (new)

**Testing:**
- MCP tools correctly update scene metadata with integration status
- SQLite queries return pending scenes correctly
- Integration status summary calculates percentages accurately
- Agents load without syntax errors
- MCP tools handle missing/invalid scene IDs gracefully

**Success Criteria:**
- All MCP unit tests pass (>95% coverage)
- Agents callable via Task tool
- No breaking changes to existing planning state functionality
- Documentation complete for new MCP tools

---

### Phase 2: Extraction Logic & Classification (Week 2)

**Deliverables:**
- [ ] Implement classification algorithm (CRITICAL/SIGNIFICANT/ROUTINE)
- [ ] Implement confidence scoring system with bump-up logic
- [ ] Complete context-extractor agent prompt with classification logic
- [ ] Create extraction JSON schema documentation
- [ ] Test context-extractor with sample scenes (5+ test cases)
- [ ] Validate classification accuracy via manual review

**Files Created:**
- `context-extractor` agent implementation (complete prompt)
- `workspace/artifacts/extraction-schema.json` (documentation)
- Test fixtures: 5 sample scenes with expected extractions

**Testing:**
- Run context-extractor on 5 diverse test scenes
- Manual validation: Are classifications reasonable?
- Confidence scores align with human judgment?
- Evidence quotes correctly extracted with line numbers?
- No false negatives on CRITICAL items (100% recall target)

**Success Criteria:**
- Classification accuracy: 80%+ vs. human labels (measured on test set)
- No CRITICAL false negatives: 100% (all critical items detected)
- ROUTINE false positives: <10% (conservative, but not over-conservative)
- Evidence quotes present for 90%+ of knowledge items
- Execution time: <30 seconds for typical 3000-word scene

---

### Phase 3: Integration Logic & File Operations (Week 3)

**Deliverables:**
- [ ] Implement knowledge-timeline.md update logic (markdown manipulation)
- [ ] Implement snapshot creation before integration
- [ ] Implement atomic file writes with temp → move pattern
- [ ] Implement rollback from snapshot on failure
- [ ] Complete context-integrator agent prompt
- [ ] Test context-integrator with sample extractions (10+ test cases)
- [ ] Validate markdown formatting preserved after integration

**Files Created:**
- `context-integrator` agent implementation (complete prompt)
- Snapshot utility functions (reusable)
- Integration report template

**Testing:**
- Apply approved changes to test knowledge-timeline files
- Verify snapshot created in correct directory
- Test rollback on simulated write failure (restore from snapshot)
- Test atomic write guarantees (no partial updates)
- Verify markdown structure valid after integration (headers, lists, formatting)
- Test creating new character file when doesn't exist

**Success Criteria:**
- No data loss during integration (100% snapshot success rate)
- Rollback works correctly on all failure modes
- Markdown formatting preserved: 95%+ (manual validation)
- Integration reports accurate and complete
- Execution time: <5 seconds for typical scene (2-3 characters)

---

### Phase 4: Coordinator Integration & User Flow (Week 4)

**Deliverables:**
- [ ] Update `generation-coordinator` to add Step 8 optional prompt
- [ ] Implement diff preview UI (formatted output with colors/emojis)
- [ ] Implement user approval/rejection/editing flow
- [ ] Integrate with MCP for planning state updates (Phase 5)
- [ ] Implement "Skip SIGNIFICANT" and "Later" options
- [ ] Create pending integrations storage system

**Files Modified:**
- `.claude/agents/generation/generation-coordinator.md` (add Step 8 logic)

**Testing:**
- End-to-end test: Generate scene → Step 8 → integration → planning state update
- Test all user flows:
  - Approve All (Y)
  - Reject All (N)
  - Edit individual items (E)
  - Skip SIGNIFICANT (S)
  - Later (L)
- Verify planning state updated correctly after integration
- Test "Later" option creates pending integration file
- Test diff preview formatting (readable, color-coded, clear)

**Success Criteria:**
- User can complete full workflow without errors
- All options (A/R/E/S/L) work correctly
- Planning state reflects integration status consistently
- Snapshots created consistently before integration
- Diff preview clear and understandable (user feedback)

---

### Phase 5: Polish, Documentation & Recovery (Week 5)

**Deliverables:**
- [ ] Create `/show-integration-status` command
- [ ] Create `/integrate-pending` command (for deferred integrations)
- [ ] Create `/rollback-integration` command (manual rollback)
- [ ] Update `.workflows/generation.md` with Step 8 documentation
- [ ] Create user tutorial: "How to Use Context Integration"
- [ ] Performance testing: 1-10 characters per scene
- [ ] Error handling: test all failure modes and edge cases

**Files Created:**
- `.claude/commands/show-integration-status.md` (new)
- `.claude/commands/integrate-pending.md` (new)
- `.claude/commands/rollback-integration.md` (new)
- `docs/context-integration-tutorial.md` (new)
- `.workflows/generation.md` (update with Step 8 section)

**Testing:**
- Test with 0 character changes (no context updates → skip gracefully)
- Test with 1, 5, 10 character updates per scene (scalability)
- Test with missing character file (creates new with default structure)
- Test with corrupted knowledge-timeline (rollback? or warn and proceed?)
- Test planning next scene when previous pending (warning shown)
- Test concurrent integration (queue mechanism)
- Manual user acceptance testing (full workflow with real scenes)

**Success Criteria:**
- Complete documentation exists for all commands and workflow
- All edge cases handled gracefully with clear error messages
- Performance: <30s extraction, <5s integration for typical scene
- User tutorial clear and comprehensive (tested with 2+ users)
- Recovery procedures documented and tested
- No critical bugs remaining (severity 1/2 issues)

---

### Optional Phase 6: Advanced Features (Future)

**Out of Scope for Initial Implementation:**
- Batch integration for multiple scenes (`/integrate-batch 0201-0210`)
- Confidence threshold customization (per-user settings)
- Learning from user corrections (ML-based classification improvement)
- Integration with storyline progress tracking (auto-update storyline milestones)
- Multi-modal emotion detection (analyze prose style, dialogue rhythm)
- Character knowledge contradiction detection (flag inconsistencies automatically)
- Timeline visualization (interactive character knowledge graphs)

**Future Consideration:**
These features add significant complexity and are not critical for MVP. Consider after Phase 5 complete and system proven stable with user feedback.

---

**Total Timeline:** 5 weeks core implementation + 1 week buffer = **6 weeks**

**Comparison to FEAT-0003:** Faster timeline (6 weeks vs. 7 weeks) because:
- No hooks needed (uses existing agent system)
- No complex cascade logic (simpler state updates)
- Smaller scope (2 agents vs. 4 hooks + 10 MCP tools in FEAT-0003)
- Builds on existing MCP infrastructure (planning_state_mcp)
- No new database tables (uses existing JSON metadata field)

---

## 9. Testing Strategy

### 9.1 Unit Tests (Automated)

#### MCP Tools Tests

**File:** `mcp-servers/tests/test_integration_status_mcp.py`

```python
import pytest
from planning_state_mcp import (
    update_scene_integration_status,
    get_integration_pending_scenes,
    get_integration_status_summary
)

def test_update_scene_integration_status():
    """Test updating scene with integration metadata"""
    # Setup: Create scene entity
    create_test_scene_entity("scene-0204")

    # Test: Update integration status
    result = update_scene_integration_status(
        scene_id="scene-0204",
        status="integrated",
        characters_updated=["alexa-wright", "reginald-havenford"],
        changes_count=5
    )

    # Assert: Success
    assert result["success"] == True

    # Assert: Metadata updated correctly
    entity = get_entity_state("scene", "scene-0204")
    assert entity["metadata"]["integration_status"] == "integrated"
    assert entity["metadata"]["characters_updated"] == ["alexa-wright", "reginald-havenford"]
    assert entity["metadata"]["context_changes_count"] == 5

def test_get_integration_pending_scenes():
    """Test querying pending scenes"""
    # Setup: Create 3 scenes with different statuses
    create_test_scene("scene-0201", integration_status="integrated")
    create_test_scene("scene-0202", integration_status="pending")
    create_test_scene("scene-0203", integration_status="skipped")
    create_test_scene("scene-0204", integration_status="pending")

    # Test: Get pending scenes
    pending = get_integration_pending_scenes()

    # Assert: Only pending returned
    assert len(pending) == 2
    assert pending[0]["entity_id"] == "scene-0202"
    assert pending[1]["entity_id"] == "scene-0204"

def test_get_integration_pending_scenes_filtered_by_act():
    """Test querying pending scenes for specific act"""
    # Setup: Create scenes across multiple acts
    create_test_scene("scene-0102", integration_status="pending")  # Act 1
    create_test_scene("scene-0204", integration_status="pending")  # Act 1
    create_test_scene("scene-0305", integration_status="pending")  # Act 2

    # Test: Get pending for Act 1 only
    pending = get_integration_pending_scenes(act_id="act-1")

    # Assert: Only Act 1 scenes returned
    assert len(pending) == 2
    assert all(s["entity_id"].startswith("scene-01") or s["entity_id"].startswith("scene-02") for s in pending)

def test_get_integration_status_summary():
    """Test summary statistics calculation"""
    # Setup: Create scenes with various statuses
    create_test_scene("scene-0101", integration_status="integrated")
    create_test_scene("scene-0102", integration_status="integrated")
    create_test_scene("scene-0103", integration_status="pending")
    create_test_scene("scene-0104", integration_status="skipped")
    create_test_scene("scene-0105", integration_status=None)  # Not started

    # Test: Get summary
    summary = get_integration_status_summary()

    # Assert: Correct counts
    assert summary["total_scenes"] == 5
    assert summary["integrated"] == 2
    assert summary["pending"] == 1
    assert summary["skipped"] == 1
    assert summary["not_started"] == 1
    assert summary["completion_percentage"] == 40.0  # 2/5 = 40%
```

#### context-extractor Tests

**File:** `mcp-servers/tests/test_context_extractor.py`

```python
def test_classification_critical_death():
    """Test CRITICAL classification for death/life events"""
    scene_text = """
    Alexa узнала страшную правду: дочь Реджинальда жива.
    Все эти годы её скрывали. Это меняет всё.
    """

    extraction = context_extractor.extract(scene_text, scene_id="0204")

    # Should detect life/death revelation as CRITICAL
    knowledge_item = extraction["characters"][0]["changes"]["knowledge_items"][0]
    assert knowledge_item["classification"] == "CRITICAL"
    assert knowledge_item["classification_confidence"] > 0.8
    assert "жива" in knowledge_item["evidence"]["quote"].lower()

def test_classification_significant_emotional():
    """Test SIGNIFICANT for emotional breakthroughs"""
    scene_text = """
    Alexa почувствовала что-то новое - сочувствие к Реджинальду.
    Её профессиональная маска дала трещину, впервые за годы.
    """

    extraction = context_extractor.extract(scene_text, scene_id="0204")

    # Should detect emotional shift as SIGNIFICANT
    emotional_change = extraction["characters"][0]["changes"]["emotional_state"]
    assert emotional_change["classification"] == "SIGNIFICANT"
    assert "сочувствие" in emotional_change["trigger"].lower()
    assert emotional_change["classification_confidence"] > 0.7

def test_classification_routine_location():
    """Test ROUTINE for factual knowledge"""
    scene_text = """
    Alexa узнала, что медпалата находится на 247 этаже Башни Книжников.
    Работает с 8:00 до 20:00 ежедневно.
    """

    extraction = context_extractor.extract(scene_text, scene_id="0101")

    # Should classify location info as ROUTINE
    knowledge_item = extraction["characters"][0]["changes"]["knowledge_items"][0]
    assert knowledge_item["classification"] == "ROUTINE"
    assert "247" in knowledge_item["item"]

def test_confidence_bump_up():
    """Test bumping classification when confidence low"""
    scene_text = """
    Alexa чувствовала что-то странное. Невозможно было понять что именно.
    """

    extraction = context_extractor.extract(scene_text, scene_id="0204")

    # Low confidence emotional change
    if extraction["characters"][0]["changes"]["emotional_state"]:
        emotional_change = extraction["characters"][0]["changes"]["emotional_state"]

        # If confidence < 0.7, should bump ROUTINE → SIGNIFICANT
        if emotional_change["classification_confidence"] < 0.7:
            assert emotional_change["classification"] in ["SIGNIFICANT", "CRITICAL"]

def test_evidence_extraction():
    """Test evidence quotes extracted with line numbers"""
    scene_text = """
Line 1: Something happened.
Line 2: Alexa saw the memory: young girl, hospital bed, tears.
Line 3: Reginald's grief washed over her.
Line 4: Something else.
"""

    extraction = context_extractor.extract(scene_text, scene_id="0204")

    knowledge_item = extraction["characters"][0]["changes"]["knowledge_items"][0]

    # Should have evidence quote
    assert "evidence" in knowledge_item
    assert "young girl" in knowledge_item["evidence"]["quote"]

    # Should have line range
    assert "line_range" in knowledge_item["evidence"]
    # Should be roughly lines 2-3
    assert "2" in knowledge_item["evidence"]["line_range"]

def test_multiple_characters_extraction():
    """Test extracting changes for multiple characters"""
    scene_text = """
    Alexa узнала о трагедии Реджинальда.
    Reginald поделился своей болью с Алексой.
    Они оба почувствовали связь между собой.
    """

    extraction = context_extractor.extract(scene_text, scene_id="0204")

    # Should extract for both characters
    assert len(extraction["characters"]) >= 2

    character_names = [c["character_name"] for c in extraction["characters"]]
    assert "Alexa Wright" in character_names or "Alexa" in character_names
    assert "Reginald Havenford" in character_names or "Reginald" in character_names
```

#### context-integrator Tests

**File:** `mcp-servers/tests/test_context_integrator.py`

```python
def test_snapshot_creation():
    """Test backup snapshot before integration"""
    # Setup: Existing knowledge-timeline
    timeline_content = """
# Knowledge Timeline: Alexa Wright

## Chapter 1
### Scene 0101
**New Knowledge:**
- Item 1
"""
    create_file("context/characters/alexa-wright/knowledge-timeline.md", timeline_content)

    # Test: Integrate changes (will create snapshot)
    extraction = create_test_extraction("0204", ["alexa-wright"])
    approved_changes = approve_all(extraction)

    result = context_integrator.integrate(extraction, approved_changes, scene_id="0204")

    # Assert: Snapshot created
    snapshot_dir = "workspace/snapshots/scene-0204-pre-integration"
    assert dir_exists(snapshot_dir)

    snapshot_file = f"{snapshot_dir}/alexa-wright-knowledge-timeline-*.md"
    assert glob_exists(snapshot_file)

    # Assert: Snapshot contains original content
    snapshot_content = read_first_matching_file(snapshot_file)
    assert "Item 1" in snapshot_content

def test_atomic_write_rollback():
    """Test rollback on write failure"""
    # Setup: Existing timeline
    original_content = """
# Knowledge Timeline: Alexa Wright
## Chapter 1
"""
    create_file("context/characters/alexa-wright/knowledge-timeline.md", original_content)

    # Setup: Mock write failure
    mock_file_write_to_fail_on_target()

    # Test: Try to integrate (will fail)
    extraction = create_test_extraction("0204", ["alexa-wright"])
    approved_changes = approve_all(extraction)

    result = context_integrator.integrate(extraction, approved_changes, scene_id="0204")

    # Assert: Integration failed
    assert result["success"] == False
    assert "write failed" in result["error"].lower()

    # Assert: File unchanged (rolled back from snapshot)
    current_content = read_file("context/characters/alexa-wright/knowledge-timeline.md")
    assert current_content == original_content

def test_markdown_structure_preservation():
    """Test markdown formatting preserved after integration"""
    # Setup: Timeline with specific formatting
    original = """
# Knowledge Timeline: Alexa Wright

**Last Updated:** Scene 0101

## Pre-Story Knowledge
- World knowledge item

## Chapter 1

### Scene 0101
**New Knowledge:**
- Item 1

## Metadata
**Statistics:** Total knowledge items: 1
"""
    create_file("context/characters/alexa-wright/knowledge-timeline.md", original)

    # Test: Add new scene section
    extraction = create_test_extraction("0102", ["alexa-wright"], knowledge_items=["New item"])
    approved_changes = approve_all(extraction)

    result = context_integrator.integrate(extraction, approved_changes, scene_id="0102")

    # Assert: Structure preserved
    new_content = read_file("context/characters/alexa-wright/knowledge-timeline.md")

    assert "# Knowledge Timeline: Alexa Wright" in new_content
    assert "## Pre-Story Knowledge" in new_content
    assert "## Chapter 1" in new_content
    assert "### Scene 0101" in new_content
    assert "### Scene 0102" in new_content  # New section added
    assert "## Metadata" in new_content
    assert "Total knowledge items: 2" in new_content  # Updated count

def test_create_new_character_file():
    """Test creating new character file when doesn't exist"""
    # Setup: No existing file for character
    assert not file_exists("context/characters/reginald-havenford/knowledge-timeline.md")

    # Test: Integrate for new character
    extraction = create_test_extraction("0204", ["reginald-havenford"])
    approved_changes = approve_all(extraction)

    result = context_integrator.integrate(extraction, approved_changes, scene_id="0204")

    # Assert: File created
    assert file_exists("context/characters/reginald-havenford/knowledge-timeline.md")

    # Assert: File has correct structure
    content = read_file("context/characters/reginald-havenford/knowledge-timeline.md")
    assert "# Knowledge Timeline: Reginald Havenford" in content
    assert "## Pre-Story Knowledge" in content
    assert "## Chapter " in content
    assert "## Metadata" in content
```

### 9.2 Integration Tests (End-to-End)

**File:** `tests/integration/test_step8_workflow.py`

```python
def test_full_workflow_with_approval():
    """Test complete Step 8 workflow from generation to integration"""
    # Setup: Generate scene (mock Step 7 complete)
    scene_text = generate_test_scene("0204", characters=["Alexa Wright", "Reginald Havenford"])
    scene_path = "acts/act-1/chapters/chapter-02/content/scene-0204.md"
    write_file(scene_path, scene_text)

    # Step 8 Phase 1: Extract context
    extraction = invoke_agent("context-extractor", {
        "scene_path": scene_path,
        "scene_id": "0204",
        "blueprint_path": "acts/act-1/chapters/chapter-02/scenes/scene-0204-blueprint.md"
    })

    # Assert: Extraction successful
    assert extraction["statistics"]["total_characters"] >= 2
    assert extraction["statistics"]["total_changes"] > 0

    # Step 8 Phase 3: User approval (simulate "Approve All")
    approved_changes = extraction  # User approved all

    # Step 8 Phase 5: Integrate
    report = invoke_agent("context-integrator", {
        "extraction_report_path": save_json(extraction, "workspace/artifacts/scene-0204-context-extraction.json"),
        "approved_changes": approved_changes,
        "scene_id": "0204"
    })

    # Assert: Integration successful
    assert report["success"] == True
    assert report["total_characters_updated"] >= 2

    # Step 8 Phase 6: Verify planning state updated
    scene_entity = get_entity_state("scene", "scene-0204")
    assert scene_entity["metadata"]["integration_status"] == "integrated"
    assert len(scene_entity["metadata"]["characters_updated"]) >= 2

    # Verify: Files updated
    alexa_timeline = read_file("context/characters/alexa-wright/knowledge-timeline.md")
    assert "Scene 0204" in alexa_timeline

    reginald_timeline = read_file("context/characters/reginald-havenford/knowledge-timeline.md")
    assert "Scene 0204" in reginald_timeline or file_exists(reginald_timeline)

def test_skip_significant_flow():
    """Test skipping SIGNIFICANT changes, applying only ROUTINE"""
    # Setup: Extract with mixed classifications
    extraction = create_test_extraction(
        scene_id="0204",
        critical=0,
        significant=3,
        routine=2
    )

    # User selects "Skip SIGNIFICANT"
    approved_changes = filter_only_routine(extraction)

    # Integrate
    report = invoke_agent("context-integrator", {
        "extraction_report_path": save_json(extraction),
        "approved_changes": approved_changes,
        "scene_id": "0204"
    })

    # Assert: Only ROUTINE applied
    assert report["total_changes_applied"] == 2  # Only routine

    # Assert: Pending file created for SIGNIFICANT
    pending_path = "workspace/pending-integrations/scene-0204-significant-changes.json"
    assert file_exists(pending_path)

    pending_data = read_json(pending_path)
    assert len(pending_data["deferred_changes"]) == 3  # 3 SIGNIFICANT deferred

def test_planning_next_scene_with_updated_context():
    """Test that planning uses updated character knowledge"""
    # Setup: Scene 0204 integrated with character knowledge
    integrate_test_scene("0204", characters=["Alexa Wright"])

    # Update Alexa's knowledge timeline with test data
    add_knowledge_to_timeline(
        character="Alexa Wright",
        scene="0204",
        knowledge="Knows about Reginald's daughter's death"
    )

    # Test: Plan next scene (0205)
    planning_context = invoke_agent("planning-coordinator", {
        "command": "/plan-scene 0205",
        "level": "scene"
    })

    # Assert: Planning context includes updated knowledge
    assert "Reginald's daughter" in planning_context or "daughter's death" in planning_context
    # Planning should inject character state into agents
```

### 9.3 Performance Tests

**File:** `tests/performance/test_step8_performance.py`

```python
import time

def test_extraction_performance_typical_scene():
    """Test extraction completes in <30 seconds for typical scene"""
    scene_text = load_realistic_scene(words=3000, characters=3)

    start = time.time()
    extraction = invoke_agent("context-extractor", {
        "scene_path": save_temp_scene(scene_text),
        "scene_id": "perf-test"
    })
    duration = time.time() - start

    assert duration < 30, f"Extraction took {duration:.1f}s (target: <30s)"
    assert extraction["execution_time_seconds"] < 30

def test_integration_performance_typical_changes():
    """Test integration completes in <5 seconds for typical scene"""
    extraction = create_test_extraction(
        scene_id="perf-test",
        characters=3,
        knowledge_items_per_char=2,
        emotional_changes=2,
        relationship_changes=1
    )

    approved_changes = approve_all(extraction)

    start = time.time()
    report = invoke_agent("context-integrator", {
        "extraction_report_path": save_json(extraction),
        "approved_changes": approved_changes,
        "scene_id": "perf-test"
    })
    duration = time.time() - start

    assert duration < 5, f"Integration took {duration:.1f}s (target: <5s)"

def test_scalability_10_characters():
    """Test performance with large number of characters"""
    extraction = create_test_extraction(
        scene_id="scale-test",
        characters=10,
        knowledge_items_per_char=1,
        emotional_changes=5,
        relationship_changes=3
    )

    approved_changes = approve_all(extraction)

    start = time.time()
    report = invoke_agent("context-integrator", {
        "extraction_report_path": save_json(extraction),
        "approved_changes": approved_changes,
        "scene_id": "scale-test"
    })
    duration = time.time() - start

    # Should still complete in reasonable time
    assert duration < 15, f"Integration with 10 characters took {duration:.1f}s (target: <15s)"
```

### 9.4 Manual Testing Checklist

**User Acceptance Testing:**

- [ ] **Full Workflow:** User completes Step 7 → Step 8 → integration without errors
- [ ] **Diff Preview:** Diff is readable, clear, and accurately represents changes
- [ ] **Approve All (A):** All changes applied correctly, files updated, planning state reflects integration
- [ ] **Reject All (R):** No changes applied, files unchanged, planning state remains pending
- [ ] **Edit (E):** Can edit individual items, modifications saved correctly
- [ ] **Skip SIGNIFICANT (S):** Only ROUTINE applied, SIGNIFICANT deferred to pending file
- [ ] **Later (L):** Creates pending integration task, can be resumed with /integrate-pending
- [ ] **Integration Report:** Report accurate, files listed, statistics correct
- [ ] **Planning State:** /show-integration-status displays correct status

**Edge Cases:**

- [ ] **0 Changes:** Scene with no character changes → Step 8 shows "No significant changes detected", gracefully skips
- [ ] **10+ Characters:** Scene with 10+ characters → extraction and integration complete in reasonable time (<60s total)
- [ ] **Missing Character File:** Character file doesn't exist → creates new file with proper structure
- [ ] **Corrupted Timeline:** Timeline has broken markdown → warns user, offers rollback or manual fix
- [ ] **Concurrent Integration:** Two scenes updating same character simultaneously → queues properly, no race conditions
- [ ] **User Cancels Mid-Approval:** User quits during approval → state consistent, no partial integration

**Recovery & Error Handling:**

- [ ] **Rollback on Write Failure:** Simulated write failure → automatic rollback from snapshot, files unchanged
- [ ] **Snapshot Restore:** Manual `/rollback-integration 0204` → files restored to pre-integration state
- [ ] **Pending Integration Resume:** Create pending integration → resume with `/integrate-pending 0204` → completes successfully
- [ ] **Integration Status Command:** `/show-integration-status` displays accurate statistics for all scenes

**Performance Validation:**

- [ ] **Extraction Time:** Typical 3000-word scene with 2-3 characters: <30 seconds
- [ ] **Integration Time:** Typical integration with 5 changes: <5 seconds
- [ ] **Full Workflow Time:** Step 7 completion → Step 8 completion: <3 minutes (including user approval)

---

### 9.5 Success Metrics

**Technical Metrics:**

- **Classification Accuracy:** 80%+ vs. human-labeled test set (measured on 20+ diverse scenes)
- **No CRITICAL False Negatives:** 100% recall on CRITICAL items (never miss important changes)
- **Integration Success Rate:** 95%+ (successful integration without rollback)
- **Performance:**
  - Extraction: <30 seconds for typical scene
  - Integration: <5 seconds for typical changes
- **Markdown Preservation:** 95%+ formatting preserved after integration

**User Experience Metrics:**

- **Workflow Completion:** 90%+ users complete full workflow without assistance
- **Approval Satisfaction:** 80%+ users approve changes without edits (AI suggestions accurate)
- **Time Savings:** <3 minutes per scene vs. 10+ minutes manual tracking (70% reduction)
- **User Feedback:** Positive feedback on workflow clarity, diff preview readability

**System Reliability:**

- **Rollback Success:** 100% (no data loss in any failure scenario)
- **State Consistency:** 100% (planning state always reflects file state)
- **Error Recovery:** 95%+ errors handled gracefully with clear messages

---

## 10. Risk Analysis & Mitigation

### Risk 1: Classification Accuracy

**Risk:** AI incorrectly classifies CRITICAL items as ROUTINE, leading to auto-application of important changes without human review.

**Impact:** HIGH - Could cause narrative inconsistencies, character knowledge contradictions.

**Likelihood:** MEDIUM - Classification logic relies on keywords and semantic analysis which may miss edge cases.

**Mitigation:**
- Conservative classification: Default to SIGNIFICANT when uncertain (confidence < 0.7)
- Confidence bump-up: Low confidence ROUTINE → SIGNIFICANT, SIGNIFICANT → CRITICAL
- Evidence quotes: Always show evidence so user can validate AI reasoning
- Post-integration review: /show-integration-status command to audit changes
- Learning system: Track user corrections to improve classification over time (Phase 6)

**Monitoring:**
- Track classification accuracy vs. user corrections
- Alert if CRITICAL false negative rate > 0% (zero tolerance)
- Weekly review of misclassifications to refine algorithm

---

### Risk 2: File Corruption During Integration

**Risk:** Atomic write fails, markdown structure corrupted, partial integration leaves files in inconsistent state.

**Impact:** HIGH - Data loss, broken character contexts, manual recovery needed.

**Likelihood:** LOW - Atomic file operations are well-tested patterns.

**Mitigation:**
- Snapshot before any changes (mandatory, not optional)
- Atomic write pattern: write temp → verify → move (OS-level atomic operation)
- Verification after write: check file exists, size reasonable, markdown valid
- Automatic rollback on failure: restore from snapshot immediately
- File locking: prevent concurrent writes to same file (queue integration)

**Recovery:**
- Snapshot directory always contains pre-integration state
- `/rollback-integration {scene_id}` command for manual rollback
- Snapshot metadata includes file hashes for integrity verification

---

### Risk 3: Planning State Drift

**Risk:** File content changes outside of integration workflow (manual edits), planning state becomes out of sync with actual file state.

**Impact:** MEDIUM - Integration status incorrect, /show-integration-status misleading.

**Likelihood:** MEDIUM - Users may manually edit character timelines.

**Mitigation:**
- Documentation: Warn against manual edits to knowledge-timelines (use agents instead)
- `/rebuild-integration-state` command: Scan files, detect changes, update planning state
- Periodic consistency checks: Cron job or manual command to detect drift
- Hash-based verification: Store file hash in planning state, detect changes

**Recovery:**
- `/rebuild-integration-state --fix` scans all character files, updates planning state
- User notified when drift detected: "Character file modified externally"

---

### Risk 4: Performance Degradation at Scale

**Risk:** With 10+ characters per scene, extraction/integration becomes slow, user frustrated by wait times.

**Impact:** MEDIUM - User experience degraded, workflow interrupted.

**Likelihood:** LOW - Current scale is 2-5 characters per scene typically.

**Mitigation:**
- Performance benchmarks: Test with 10 characters, ensure <60s total time
- Parallel processing: Extract characters in parallel (Phase 6 optimization)
- Progress indicators: Show "Extracting character 3/10..." during long operations
- Skip option: Allow user to skip Step 8 if too slow

**Monitoring:**
- Track execution time per scene
- Alert if extraction >60s or integration >15s
- Optimize hot paths based on profiling data

---

### Risk 5: User Confusion with Tiered System

**Risk:** Users don't understand CRITICAL/SIGNIFICANT/ROUTINE distinctions, make incorrect approval decisions.

**Impact:** LOW-MEDIUM - Suboptimal workflow, but no data loss.

**Likelihood:** MEDIUM - New concept, requires learning.

**Mitigation:**
- Clear visual indicators: 🔴 CRITICAL, 🟡 SIGNIFICANT, 🟢 ROUTINE
- Inline help: Explain each tier in diff preview (hover tooltips?)
- Tutorial documentation: Step-by-step guide with examples
- Conservative defaults: When in doubt, classify higher (better safe than sorry)

**User Education:**
- Tutorial in `docs/context-integration-tutorial.md`
- Example scenarios showing each tier
- FAQ section addressing common questions

---

## 11. Open Questions for Implementation

### Q1: Should ROUTINE changes show individual items in diff or just summary?

**Option A:** Show all ROUTINE items individually (verbose)
**Option B:** Show summary: "2 ROUTINE changes will be auto-applied" (concise)

**Recommendation:** Option B with expandable details ([?] to show full list)

---

### Q2: How to handle character name variations (Alexa vs. Alexa Wright)?

**Option A:** Strict matching (require exact name)
**Option B:** Fuzzy matching with confirmation ("Did you mean Alexa Wright?")

**Recommendation:** Option B - use character registry from world-bible for canonical names, match variations

---

### Q3: Should integration create new scene sections chronologically or append to end?

**Option A:** Insert in chronological order (Scene 0203 between 0202 and 0204)
**Option B:** Always append to end (simpler, less markdown manipulation)

**Recommendation:** Option A - maintain chronological order for readability, use scene ID for sorting

---

### Q4: What to do when planning state MCP unavailable?

**Option A:** Block integration until MCP available
**Option B:** Complete integration, log warning about state drift, manual sync later

**Recommendation:** Option B - prioritize file integrity over state consistency, allow manual sync

---

## 12. Success Criteria

The implementation is successful when:

✅ **Core Functionality:**
- Step 8 completes end-to-end without errors
- Extraction correctly identifies knowledge, emotions, relationships
- Classification achieves 80%+ accuracy with 0% CRITICAL false negatives
- Integration updates files atomically with rollback capability
- Planning state reflects integration status consistently

✅ **User Experience:**
- User can complete full workflow (Step 7 → 8) in <3 minutes
- Diff preview is clear, readable, and actionable
- All approval options (A/R/E/S/L) work correctly
- Integration reports are accurate and comprehensive
- Error messages are clear with actionable recovery steps

✅ **Performance:**
- Extraction: <30 seconds for typical 3000-word scene
- Integration: <5 seconds for typical 2-3 character changes
- Scalability: <60 seconds total for 10 characters

✅ **Reliability:**
- 95%+ integration success rate
- 100% rollback success (no data loss)
- Markdown formatting preserved in 95%+ cases
- State consistency maintained across all operations

✅ **Integration:**
- Planning workflow uses updated character contexts
- /show-integration-status displays accurate statistics
- Pending integrations can be resumed successfully
- Snapshots enable reliable recovery

---

## 13. Appendix

### A. Complete File Structure

```
/project-root
├── mcp-servers/
│   ├── planning_state_mcp.py          # Extended with integration status
│   └── tests/
│       └── test_integration_status.py
│
├── .claude/
│   ├── agents/generation/
│   │   ├── context-extractor.md       # NEW
│   │   ├── context-integrator.md      # NEW
│   │   └── generation-coordinator.md  # MODIFIED (add Step 8)
│   │
│   └── commands/
│       ├── show-integration-status.md # NEW
│       ├── integrate-pending.md       # NEW
│       └── rollback-integration.md    # NEW
│
├── context/characters/
│   └── {character-name}/
│       ├── knowledge-timeline.md      # NEW (created by integrator)
│       └── ...
│
├── workspace/
│   ├── artifacts/
│   │   ├── scene-{ID}-context-extraction.json
│   │   └── scene-{ID}-integration-report.md
│   │
│   ├── snapshots/
│   │   └── scene-{ID}-pre-integration/
│   │       ├── {character}-knowledge-timeline-{timestamp}.md
│   │       └── snapshot-metadata.json
│   │
│   └── pending-integrations/
│       └── scene-{ID}-significant-changes.json
│
├── features/FEAT-0004-context-integration/
│   ├── README.md                      # Feature Brief
│   └── technical-design.md            # This document
│
├── docs/
│   └── context-integration-tutorial.md # NEW (user guide)
│
└── .workflows/
    └── generation.md                  # MODIFIED (add Step 8 documentation)
```

### B. Knowledge Timeline Example (Complete)

See Section 2.1 for complete schema with example.

### C. MCP Tool Signatures (Complete)

See Section 6.1 for complete MCP tool implementations.

### D. Agent Prompt Templates (Excerpts)

**context-extractor prompt structure:**
```markdown
You are the context-extractor agent. Your role is to...

INPUT FORMAT:
- scene_path: {path}
- scene_id: {id}

TASK:
1. Read scene text
2. Identify characters
3. Extract changes:
   - Knowledge items
   - Emotional states
   - Relationships
   - Interactions
4. Classify each change using criteria...
5. Calculate confidence scores...
6. Extract evidence quotes...

OUTPUT FORMAT:
Return JSON matching schema in Section 4.1...

CLASSIFICATION LOGIC:
[Include classification criteria from Section 3]

ERROR HANDLING:
[Include error handling rules from Section 4.1]
```

**context-integrator prompt structure:**
```markdown
You are the context-integrator agent. Your role is to...

INPUT FORMAT:
- extraction_report_path: {path}
- approved_changes: {json}

TASK:
1. Read extraction report
2. Filter to approved changes only
3. Create snapshot directory
4. For each character:
   - Read existing timeline (or create new)
   - Apply changes chronologically
   - Update metadata
5. Write files atomically
6. Verify integrity
7. Generate integration report

OUTPUT FORMAT:
Return markdown report matching schema in Section 4.2...

FILE OPERATIONS:
[Include atomic write procedure from Section 4.2]

ERROR HANDLING:
[Include rollback procedure from Section 7]
```

---

**END OF TECHNICAL DESIGN**

This document provides the complete technical architecture for FEAT-0004: Context Integration After Generation. Implementation can proceed in 5 phases over approximately 6 weeks, with comprehensive testing and error handling at every layer.

**Next Steps:**
1. Review and approve this technical design
2. Begin Phase 1 (MCP extensions & agent creation)
3. Iterative implementation following phased approach
4. User acceptance testing after Phase 4
5. Documentation and tutorial creation in Phase 5
6. Production deployment with monitoring

**Maintenance:**
- Update this document as implementation reveals necessary adjustments
- Track actual vs. estimated timelines and performance metrics
- Collect user feedback and iterate on UX improvements

**Version History:**
- v1.0.0 (2025-11-28) - Initial technical design complete
