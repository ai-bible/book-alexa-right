# Versioning System Update for FEAT-0001

**Date**: 2025-10-31
**Purpose**: Document corrections to Technical Design Part 1 & Part 2

---

## Root Cause Analysis: The Real Problem

### What We Initially Thought:
- "Plan v3 is good, v2 is bad"
- "Agents need to check for v3 compliance"

### What Actually Happened:
Plans were rewritten **3 times into DIFFERENT FILES**:
```
plan.md (original)
  ↓
plan-revised.md (rewrite #1)
  ↓
plan-v2.md (rewrite #2)
  ↓
plan-v3.md (rewrite #3)
```

**Problem:** Agents didn't know which file was current!
- prose-writer read `plan-v2.md`
- blueprint-validator expected `plan-v3.md`
- coordinator looked for `plan.md`
→ Chaos, inconsistency, constraint violations

### Same Issue with Blueprints:
```
scene-0204-blueprint.md
scene-0204-blueprint-revised.md
scene-0204-blueprint-v2.md
```

---

## Correct Solution: ONE Canonical File

### File Naming Standard

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

### Versioning Method: Timestamped Backups

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
    ├── plan-2025-10-27-14-30.md      (backup before major edit)
    ├── plan-2025-10-25-09-15.md      (previous backup)
    └── scene-0204-blueprint-2025-10-29-16-45.md
```

**Backup Naming:**
```
{original-name}-{YYYY-MM-DD-HH-MM}.md

Examples:
plan-2025-10-31-10-30.md
scene-0204-blueprint-2025-10-31-15-45.md
```

### Agent Rules

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
- plan-v3.md

ACTION REQUIRED:
1. Decide which file is current
2. Rename it to plan.md (if not already)
3. Move others to backups/:
   mv plan-revised.md backups/plan-2025-10-25.md
   mv plan-v3.md backups/plan-2025-10-27.md
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

## Changes Required in Technical Designs

### In Part 1: Agent Specifications

**blueprint-validator agent:**

❌ **Remove:**
- "Check blueprint version >= v3.0"
- "plan_v3_constraints input parameter"
- "v3 compliance checks"
- References to "v3 changes", "v3 removals"

✅ **Replace with:**
- Check for file naming: `scene-{ID}-blueprint.md` (no version suffix)
- Check for multiple blueprint files → error if found
- Check plan file is named `plan.md` (no version suffix)
- Check for multiple plan files → error if found
- Cross-reference with current `plan.md` for consistency

**All agents:**

❌ **Remove mentions of:**
- "v3 plan"
- "plan-v3.md"
- "v3 changes"
- "removed in v3"
- "v3 compliance"

✅ **Replace with:**
- "current plan" (always refers to `plan.md`)
- "plan.md" (explicit file name)
- "changes documented in plan" (not "v3 changes")
- "removed per plan" (not "removed in v3")
- "plan compliance" (not "v3 compliance")

### In Part 2: Prompts

**All prompt templates:**

❌ **Remove:**
```markdown
### V3 CRITICAL CHANGES
- Себастьян Грей (removed in v3)
- Location (changed in v3)
```

✅ **Replace with:**
```markdown
### CURRENT PLAN REQUIREMENTS
(Extracted from acts/act-1/chapters/chapter-02/plan.md)

**Characters to exclude:**
- Себастьян Грей (removed per chapter plan)

**Location requirements:**
- Use: Башня Книжников медпалата
- Do NOT use: больница, медицинский центр
```

**Key principle:** Constraints come from CURRENT `plan.md`, not from "v3" concept.

---

## Why This Matters

### Old Approach (WRONG):
```
Agent thinks: "I need v3 compliance"
Agent looks for: plan-v3.md
Agent finds: plan.md, plan-revised.md, plan-v3.md
Agent picks: plan-v3.md (guesses this is latest)
Result: Maybe right, maybe wrong
```

### New Approach (CORRECT):
```
Agent thinks: "I need current plan"
Agent looks for: plan.md (standard name)
Agent finds: plan.md, plan-revised.md
Agent stops: "ERROR: Multiple files. Clean up first."
Result: Unambiguous, reliable
```

---

## Implementation Checklist

### Part 1 Updates:
- [ ] Remove "v3" from agent descriptions
- [ ] Update blueprint-validator: check for file naming and duplicates
- [ ] Update all agents: reference "plan.md" not "plan-v3.md"
- [ ] Add "file migration" logic to agents
- [ ] Update artifact schemas: remove "blueprint_version" field

### Part 2 Updates:
- [ ] Remove "V3 CRITICAL CHANGES" from prompt templates
- [ ] Replace with "CURRENT PLAN REQUIREMENTS"
- [ ] Update all examples (scene 0204) to reference `plan.md`
- [ ] Remove "plan_v3_constraints" parameters
- [ ] Update retry logic: don't mention "v3"

### DECISIONS.md:
- [x] Added "File Versioning System" section (already done)
- [x] Explained root cause
- [x] Documented solution

### README.md (Feature Brief):
- [ ] Update examples to use `plan.md` not `plan-v3.md`
- [ ] Add section about file naming standards
- [ ] Update edge cases with "multiple files detected" scenario

---

## Key Takeaway

**The problem was NEVER about plan version numbers.**

The problem was **multiple files with different names**, causing ambiguity.

**Solution:**
- ONE canonical file with standard name
- Versions tracked via backups/ directory with timestamps
- Agents enforce single-file rule, error on duplicates

This is a **File System Discipline** issue, not a "version compliance" issue.

---

END OF DOCUMENT
