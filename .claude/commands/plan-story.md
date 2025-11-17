---
name: plan-story
---

Start interactive story planning session. Usage:

**IMPORTANT - Hierarchical Planning (FEAT-0003):**
For structured hierarchical planning with state tracking, use the dedicated commands:
- `/plan-act <act_number>` - Plan entire act (enforces hierarchy)
- `/plan-chapter <chapter_number>` - Plan specific chapter (requires approved act)
- `/plan-scene <scene_id>` - Plan specific scene (requires approved chapter)

These commands provide:
- Parent-child validation (can't plan chapter without approved act)
- Automatic state tracking via MCP
- Version management and cascade invalidation
- Context injection from parent plans

**Legacy Mode (Backward Compatibility):**
The following modes are still supported but don't enforce hierarchical validation:
- `/plan-story act [act-number]` - Plan entire act (legacy mode, routes to /plan-act)
- `/plan-story chapter [chapter-number]` - Plan specific chapter (legacy mode, routes to /plan-chapter)
- `/plan-story scene [scene-description]` - Plan specific scene (legacy mode, routes to /plan-scene)

**Interactive Mode:**
- `/plan-story` - Start with guided questions about what you want to plan
  - Uses planning-coordinator agent for exploratory planning
  - Outputs to `/workspace/planning-session-[ID]/`
  - Useful for brainstorming and exploring possibilities

**Process:**
The planning-coordinator will guide you through:
1. Understanding your vision (where are we, where are we going)
2. Exploring possibilities and consequences
3. Breaking down into concrete events/scenes
4. Creating detailed plans with dependencies

---

## Routing Logic

**If user calls `/plan-story act N`:**
→ Detect intent and route to: `/plan-act N`
→ This ensures hierarchical validation is enforced

**If user calls `/plan-story chapter N`:**
→ Detect intent and route to: `/plan-chapter N`
→ This ensures parent act is approved before planning

**If user calls `/plan-story scene XXYY`:**
→ Detect intent and route to: `/plan-scene XXYY`
→ This ensures parent chapter is approved before planning

**If user calls `/plan-story` (no arguments):**
→ Launch planning-coordinator in interactive mode
→ Use for exploratory planning without structure

---

## Recommended Workflow

1. **Start with acts**: `/plan-act 1` (plan Act 1)
2. **Approve act**: `approve_entity(entity_type='act', entity_id='act-1')`
3. **Plan chapters**: `/plan-chapter 1`, `/plan-chapter 2`, etc.
4. **Approve chapters**: `approve_entity(entity_type='chapter', entity_id='chapter-01')`
5. **Plan scenes**: `/plan-scene 0101`, `/plan-scene 0102`, etc.
6. **Approve scenes**: `approve_entity(entity_type='scene', entity_id='scene-0101')`
7. **Generate prose**: `"Generate scene 0101"`

---

## Migration Notes

If you have existing plans created with old `/plan-story` command:
- They will continue to work (backward compatible)
- To enable hierarchical tracking, run: `/rebuild-state` (rebuilds MCP state from files)
- Then approve entities using: `approve_entity(entity_type=..., entity_id=...)`

---

## See Also

- `/plan-act` - Hierarchical act planning with validation
- `/plan-chapter` - Hierarchical chapter planning with parent context injection
- `/plan-scene` - Hierarchical scene planning with blueprint creation
- `approve_entity()` - Approve plans to enable child planning
- `get_entity_state()` - Check planning entity status
- `get_hierarchy_tree()` - View complete act hierarchy
