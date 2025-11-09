# Evaluation Tests for Generation State Tracker MCP Server

**Version:** 1.0.0
**Created:** 2025-11-03
**Purpose:** Comprehensive testing of `generation_state_mcp.py` MCP server

---

## Overview

This directory contains evaluation scenarios for the Generation State Tracker MCP server. The evaluations test the MCP server's ability to:
- Read and parse state files correctly
- Calculate durations and timings
- Extract error messages
- Handle different workflow statuses
- Compare data across multiple scenes
- Filter and sort generation lists

---

## Directory Structure

```
tests/
├── README.md                   # This file
├── evaluation.xml              # 10 evaluation questions
└── test-states/                # Test state files
    ├── generation-state-0101.json  # COMPLETED workflow
    ├── generation-state-0202.json  # FAILED workflow
    └── generation-state-0303.json  # IN_PROGRESS workflow
```

---

## Test State Files

### Scene 0101 (COMPLETED)
- **Status**: COMPLETED
- **Total Duration**: 402 seconds (6m 42s)
- **Generation Attempts**: 1/3 (succeeded on first try)
- **All Steps**: Completed successfully
- **Use Case**: Test successful workflow reading

### Scene 0202 (FAILED)
- **Status**: FAILED
- **Current Step**: 4 (Generation)
- **Total Duration**: 667 seconds (11m 7s)
- **Generation Attempts**: 3/3 (max attempts reached)
- **Failure Reason**: Location constraint violated
- **Use Case**: Test error handling and resume calculation

### Scene 0303 (IN_PROGRESS)
- **Status**: IN_PROGRESS
- **Current Step**: 4 (Generation, attempt 2/3)
- **Total Duration**: 225 seconds (3m 45s, still running)
- **Generation Attempts**: 2/3 (first attempt failed)
- **Use Case**: Test in-progress workflow monitoring

---

## Running Evaluations

### Prerequisites

1. **MCP Server installed and configured**
   ```bash
   # Install dependencies
   pip install -r mcp-servers/requirements.txt

   # Configure in Claude Code (see mcp-servers/README.md)
   ```

2. **Claude Code with MCP support**
   - Ensure `generation-state-tracker` MCP server is loaded
   - Check with: `/mcp list`

### Setup

Copy test state files to workspace:

```bash
# From project root
cp mcp-servers/tests/test-states/*.json workspace/
```

Verify files copied:
```bash
ls workspace/generation-state-*.json
# Should show:
# workspace/generation-state-0101.json
# workspace/generation-state-0202.json
# workspace/generation-state-0303.json
```

### Run Evaluation Questions

Use the MCP tools to answer each question in `evaluation.xml`:

#### Example: Question 1
**Question:** What is the current workflow status of scene 0202, and at which step did it fail?

**How to Answer:**
```python
# Use MCP tool
get_generation_status(scene_id="0202")

# Look for:
# - workflow_status field
# - current_step field

# Expected Answer: "FAILED, Step 4"
```

#### Example: Question 7
**Question:** If we were to resume scene 0202 after fixing the blueprint, how many seconds would be saved by skipping already completed steps 1-3?

**How to Answer:**
```python
# Use MCP tool
get_generation_status(scene_id="0202", detailed=True)

# Calculate:
# step_1.duration_seconds (1) +
# step_2.duration_seconds (19) +
# step_3.duration_seconds (12)
# = 32 seconds

# Expected Answer: "32 seconds"
```

#### Example: Question 10
**Question:** Using list_generations tool to check all test scenes, how many scenes have workflow_status of FAILED?

**How to Answer:**
```python
# Use MCP tool
list_generations(filter="failed")

# Count results
# Expected Answer: "1" (only scene 0202)
```

### Cleanup

Remove test state files after evaluation:

```bash
rm workspace/generation-state-0101.json
rm workspace/generation-state-0202.json
rm workspace/generation-state-0303.json
```

---

## Evaluation Criteria

Each question must:
- ✅ **Independent**: Can be answered without dependencies on other questions
- ✅ **Read-only**: Uses only `get_generation_status` and `list_generations` tools
- ✅ **Complex**: Requires parsing JSON, calculations, or cross-scene comparison
- ✅ **Realistic**: Based on actual use cases
- ✅ **Verifiable**: Has single, clear answer that can be verified by string comparison
- ✅ **Stable**: Answer won't change (based on static test files)

---

## Expected Results

All 10 questions should be answerable using the MCP server tools:

| Question | Tool(s) Required | Complexity |
|----------|------------------|------------|
| Q1 | `get_generation_status` | Basic field reading |
| Q2 | `get_generation_status` (detailed) | Nested field reading |
| Q3 | `get_generation_status` (detailed) | Error array parsing |
| Q4 | `get_generation_status` (detailed) | Duration calculation |
| Q5 | `get_generation_status` (detailed) | Step duration comparison |
| Q6 | `get_generation_status` (detailed) | Status analysis |
| Q7 | `get_generation_status` (detailed) | Multi-step duration sum |
| Q8 | `get_generation_status` (x2) | Cross-scene comparison |
| Q9 | `get_generation_status` (detailed) | Attempt history parsing |
| Q10 | `list_generations` | Filtering and counting |

---

## Troubleshooting

### MCP Server Not Responding

1. Check server is configured:
   ```bash
   /mcp list
   ```

2. Verify server path in config:
   ```json
   {
     "mcpServers": {
       "generation-state-tracker": {
         "command": "python",
         "args": ["E:\\sources\\book-alexa-right\\mcp-servers\\generation_state_mcp.py"]
       }
     }
   }
   ```

3. Restart Claude Code

### State Files Not Found

1. Verify files copied to `workspace/`:
   ```bash
   ls workspace/generation-state-*.json
   ```

2. Check file permissions (should be readable)

3. Verify JSON is valid:
   ```bash
   python -m json.tool workspace/generation-state-0202.json
   ```

### Wrong Answers

1. Verify you're using correct MCP tool parameters
2. Check JSON parsing (use `detailed=True` when needed)
3. Review calculation logic (durations, counts)
4. Compare answer format with expected format in `evaluation.xml`

---

## Performance Benchmarks

Expected performance for evaluation questions:

- **Simple queries (Q1, Q6)**: <100ms
- **Detailed queries (Q2-Q5, Q7, Q9)**: <150ms
- **Cross-scene queries (Q8)**: <200ms
- **List queries (Q10)**: <300ms

If queries take significantly longer, check:
- State file sizes (should be <100KB each)
- File system performance
- MCP server overhead

---

## Extending Evaluations

To add new evaluation questions:

1. **Create new test state file** (if needed)
   ```json
   {
     "scene_id": "0404",
     "workflow_status": "CANCELLED",
     ...
   }
   ```

2. **Add question to evaluation.xml**
   ```xml
   <qa_pair>
     <question>Your question here?</question>
     <answer>Expected answer</answer>
     <rationale>Explanation of what this tests</rationale>
   </qa_pair>
   ```

3. **Verify question meets criteria**
   - [ ] Independent
   - [ ] Read-only
   - [ ] Complex
   - [ ] Realistic
   - [ ] Verifiable
   - [ ] Stable

4. **Test manually** before adding to evaluation suite

---

## Version History

**v1.0.0** (2025-11-03)
- Initial evaluation suite
- 10 questions covering core functionality
- 3 test state files (COMPLETED, FAILED, IN_PROGRESS)
- Documentation and setup instructions

---

## Related Documentation

- **MCP Server**: `../README.md`
- **MCP Server Code**: `../generation_state_mcp.py`
- **FEAT-0002 Spec**: `../../features/FEAT-0002-workflow-state-tracking/README.md`
- **Skill Spec**: `../../.claude/skills/generation-state.md`

---

**Last Updated:** 2025-11-03
**Status:** Ready for Testing
