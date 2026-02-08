# Constraint Extraction Guide

How to extract constraints from blueprint for `02-constraints.json`.

## Source Locations

Constraints come from these blueprint sections:

1. **Hard Constraints** section (explicit list)
2. **Verification Plan** section (implicit constraints)
3. **Beat definitions** (character presence, locations)

## JSON Structure

```json
{
  "scene_id": "XXXX",
  "constraints": {
    "temporal": {
      "description": "Time-related constraints",
      "items": []
    },
    "spatial": {
      "description": "Location constraints",
      "items": []
    },
    "characters": {
      "present": [],
      "absent": [],
      "pov": ""
    },
    "mechanics": {
      "description": "World mechanics that must be shown",
      "items": []
    },
    "style": {
      "word_count": "",
      "language": "Russian",
      "banned_patterns": []
    }
  }
}
```

## Extraction Process

### Step 1: Find Hard Constraints

Look for section `## Hard Constraints` or `## Constraints`:

```markdown
## Hard Constraints

- Timer: на обратной стороне век
- Injection: в шею
- Glitches: exactly 2
```

Extract each as constraint item.

### Step 2: Extract Character Constraints

From `## Characters` or beat definitions:

```markdown
### Characters Present
- Alexa Wright (POV, all beats)
- David (Beat 4 only)

### Characters Absent
- Lina (only as glitches)
```

### Step 3: Extract Temporal Constraints

From timeline or beat definitions:

```markdown
### Timeline
- 23:47 - Operation starts
- 00:15 - Scene ends
```

### Step 4: Extract Mechanical Constraints

From world mechanics mentioned:

```markdown
### Mechanics
- Timer shows "2 hours 14 minutes" BEFORE injection
- Timer shows "30 days 2 hours 14 minutes" AFTER injection
```

### Step 5: Extract Style Constraints

From style requirements:

```markdown
### Style
- Word count: 3,000-3,500
- Language: Russian
- Banned: lists, parentheses, named emotions
```

## Example Output

```json
{
  "scene_id": "0101",
  "constraints": {
    "temporal": {
      "items": [
        {"key": "timer_before", "value": "2 hours 14 minutes", "critical": true},
        {"key": "timer_after", "value": "30 days 2 hours 14 minutes", "critical": true}
      ]
    },
    "characters": {
      "present": ["Alexa Wright (POV)", "David (Beat 4)"],
      "absent": ["Lina (glitches only)"],
      "pov": "Alexa Wright"
    },
    "mechanics": {
      "items": [
        {"key": "timer_location", "value": "back of eyelids", "critical": true},
        {"key": "injection_location", "value": "neck", "critical": true},
        {"key": "glitch_count", "value": 2, "critical": true}
      ]
    },
    "style": {
      "word_count": "3000-3500",
      "language": "Russian",
      "banned_patterns": ["lists", "parentheses", "named emotions"]
    }
  }
}
```

## Validation

After extraction, verify:

1. All critical constraints marked as `"critical": true`
2. No conflicting constraints
3. Character presence matches beat definitions
4. Word count range is reasonable for beat count
