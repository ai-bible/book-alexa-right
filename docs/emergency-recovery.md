# Emergency Recovery Guide

Emergency procedures for recovering from FEAT-0003 Hierarchical Planning system failures.

**Last Updated**: 2025-11-15

---

## Quick Reference

| **Problem** | **Command** | **Time** |
|------------|-------------|----------|
| State database corrupted | `/rebuild-state` | 10-30s |
| MCP server crashed | Restart MCP | 5s |
| Hook blocking valid operation | Disable hook temporarily | 1min |
| State out of sync with files | `/rebuild-state` | 10-30s |
| Lost all backups | Check `backups/` directories | varies |
| Can't approve entity | Check parent status | 1min |

---

## Common Emergencies

### 1. Database Corruption

**Symptoms**:
- SQLite errors in MCP logs
- Commands failing with database errors
- "database disk image is malformed"

**Recovery**:

```bash
# 1. Stop MCP server (if running)
pkill -f generation_state_mcp.py

# 2. Backup corrupted database (for investigation)
mv workspace/planning-state.db workspace/planning-state.db.corrupted

# 3. Rebuild state from files
/rebuild-state

# 4. Verify recovery
/show-hierarchy

# 5. Restart MCP server
# (usually automatic, or restart manually)
```

**Prevention**:
- Regular backups: `cp workspace/planning-state.db backups/planning-state-$(date +%Y%m%d).db`
- Don't kill MCP server during writes
- Ensure sufficient disk space

---

### 2. MCP Server Not Responding

**Symptoms**:
- "MCP unavailable" errors
- Commands timeout
- Planning tools not found

**Recovery**:

```bash
# 1. Check if MCP server is running
ps aux | grep generation_state_mcp

# 2. Check logs
tail -f workspace/logs/mcp-server.log

# 3. Restart MCP server
# Method varies by setup:
# - If using systemd: systemctl restart mcp-server
# - If manual: pkill -f generation_state_mcp && python mcp-servers/generation_state_mcp.py &

# 4. Test connection
# Use any MCP tool:
get_entity_state(entity_type='act', entity_id='act-1')

# 5. If still failing, check:
# - Python dependencies installed
# - No port conflicts
# - File permissions correct
```

**Prevention**:
- Monitor MCP server health
- Set up automatic restart (systemd, supervisor)
- Review logs regularly

---

### 3. Hook Blocking Valid Operation

**Symptoms**:
- "Blocked by hook" errors
- Can't write files even though valid
- Hook false positive

**Emergency Override**:

```bash
# TEMPORARY SOLUTION - DO NOT USE REGULARLY

# 1. Disable problematic hook
mv .claude/hooks/hierarchy_validation_hook.py .claude/hooks/hierarchy_validation_hook.py.disabled

# 2. Perform operation
# (your command that was blocked)

# 3. Re-enable hook IMMEDIATELY
mv .claude/hooks/hierarchy_validation_hook.py.disabled .claude/hooks/hierarchy_validation_hook.py

# 4. Manually sync state
# Use MCP tools to update state for the entity you just modified
```

**Proper Fix**:
- Report hook bug
- Fix hook logic
- Test thoroughly before re-enabling

**Prevention**:
- Never disable hooks permanently
- Review hook logic carefully
- Test hooks with edge cases

---

### 4. State Out of Sync with Files

**Symptoms**:
- File exists but not in state
- State shows old version hash
- Hierarchy missing entities

**Recovery**:

```bash
# 1. Check discrepancy
/show-hierarchy
ls -la acts/  # Compare with actual files

# 2. Rebuild state
/rebuild-state --dry-run  # Preview
/rebuild-state             # Execute

# 3. Verify sync
/show-hierarchy

# 4. Check specific entities
get_entity_state(entity_type='chapter', entity_id='chapter-02')
```

**Prevention**:
- Use hooks (they auto-sync on file writes)
- Don't edit files outside of commands
- Run `/rebuild-state` after manual changes

---

### 5. Lost Planning State (Complete Loss)

**Symptoms**:
- `workspace/planning-state.db` deleted
- No JSON fallbacks exist
- Fresh start needed

**Recovery**:

```bash
# 1. Check if files still exist
ls -R acts/

# 2. If files exist, rebuild from them
/rebuild-state

# 3. Manually approve entities (state lost approval info)
# Check each file, then approve:
approve_entity(entity_type='act', entity_id='act-1')
approve_entity(entity_type='chapter', entity_id='chapter-01')
# ... etc

# 4. If files also lost, restore from backup
# (project-specific backup location)

# 5. If no backups, start fresh
/plan-act 1
```

**Prevention**:
- **Critical**: Backup `workspace/planning-state.db` daily
- Version control planning files (git)
- Use JSON fallback (dual storage)
- Cloud backup for critical projects

---

### 6. Cannot Approve Entity (Parent Not Approved)

**Symptoms**:
- "Parent not approved" error
- Hierarchical validation blocking

**Resolution**:

```bash
# 1. Check entity state
get_entity_state(entity_type='chapter', entity_id='chapter-02')

# 2. Check parent state
get_entity_state(entity_type='act', entity_id='act-1')

# 3. Approve parent first
approve_entity(entity_type='act', entity_id='act-1')

# 4. Then approve child
approve_entity(entity_type='chapter', entity_id='chapter-02')

# 5. Use force if absolutely needed (RARE)
approve_entity(entity_type='chapter', entity_id='chapter-02', force=True)
```

**Notes**:
- This is **by design** (hierarchical validation)
- Don't use `force=True` unless emergency
- Always approve parents before children

---

### 7. Cascade Invalidation Gone Wrong

**Symptoms**:
- Too many entities invalidated
- Cascade happened unexpectedly
- Need to undo invalidation

**Recovery**:

```bash
# 1. Check what was invalidated
/revalidate-all
# Lists all entities needing revalidation

# 2. Bulk approve if cascade was wrong
# If you're confident entities are still valid:
/revalidate-all --chapter 02
# Choose "Bulk Approve (All)"

# 3. Or revalidate individually
/revalidate-scene 0201  # Review each

# 4. If cascade was correct, regenerate
# Cascade happened because parent changed
# Review parent changes, then regenerate children:
/plan-scene 0201  # Choose "regenerate"
```

**Prevention**:
- Review parent changes carefully before approving
- Use backups before major regenerations
- Test regeneration on single chapter first

---

### 8. Backup System Failure

**Symptoms**:
- Backups not created on regeneration
- backup_id missing from MCP
- backups/ directory empty

**Recovery**:

```bash
# 1. Manual backup of current file
mkdir -p acts/act-1/chapters/chapter-02/backups
cp acts/act-1/chapters/chapter-02/plan.md \
   acts/act-1/chapters/chapter-02/backups/plan-$(date +%Y-%m-%d-%H-%M-%S).md

# 2. Check backup table
# Via MCP tool or direct SQLite:
sqlite3 workspace/planning-state.db "SELECT * FROM planning_entity_backups"

# 3. Manually log backup (if needed)
create_backup(
    entity_type='chapter',
    entity_id='chapter-02',
    reason='manual'
)

# 4. Verify backup logged
list_backups(entity_type='chapter', entity_id='chapter-02')
```

**Prevention**:
- Test backup creation regularly
- Check `backups/` directories exist
- Verify backup permissions
- Monitor disk space

---

## Data Recovery

### Recover from Git

If planning files are in version control:

```bash
# 1. Check git history
git log --oneline -- acts/act-1/chapters/chapter-02/plan.md

# 2. View old version
git show <commit>:acts/act-1/chapters/chapter-02/plan.md

# 3. Restore old version
git checkout <commit> -- acts/act-1/chapters/chapter-02/plan.md

# 4. Rebuild state
/rebuild-state

# 5. Commit restored version
git add acts/act-1/chapters/chapter-02/plan.md
git commit -m "Restore chapter-02 plan from <commit>"
```

### Recover from Backups Directory

```bash
# 1. List backups
ls -lht acts/act-1/chapters/chapter-02/backups/

# 2. View backup content
cat acts/act-1/chapters/chapter-02/backups/plan-2025-11-14-10-30-00.md

# 3. Restore backup (via command)
restore_backup(
    entity_type='chapter',
    entity_id='chapter-02',
    backup_id=42  # Get from list_backups
)

# 4. Or manual restore
cp acts/act-1/chapters/chapter-02/backups/plan-2025-11-14-10-30-00.md \
   acts/act-1/chapters/chapter-02/plan.md

# 5. Rebuild state
/rebuild-state
```

---

## Nuclear Option: Complete Reset

**⚠️ WARNING**: Only use as last resort. All state will be lost.

```bash
# 1. BACKUP EVERYTHING FIRST
tar -czf emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
    acts/ workspace/ .claude/

# 2. Stop MCP server
pkill -f generation_state_mcp.py

# 3. Delete state database
rm workspace/planning-state.db

# 4. Delete JSON fallbacks
rm -rf workspace/planning-state/

# 5. Rebuild from files
/rebuild-state

# 6. Manually re-approve entities
# Check each file, approve as appropriate

# 7. Restart MCP server
# (automatic or manual restart)

# 8. Verify system
/show-hierarchy
get_entity_state(entity_type='act', entity_id='act-1')
```

---

## Diagnostic Commands

### Check System Health

```bash
# MCP server status
ps aux | grep generation_state_mcp

# Database integrity
sqlite3 workspace/planning-state.db "PRAGMA integrity_check;"

# Check hooks registered
cat .claude/hooks.json

# List entities in state
sqlite3 workspace/planning-state.db "SELECT entity_type, entity_id, status FROM planning_entities;"

# Check backups exist
find acts/ -type f -path "*/backups/*" | wc -l
```

### Debug State Issues

```bash
# Compare files vs state
echo "Files:"
find acts/ -name "*.md" -type f | grep -E "(strategic-plan|plan|blueprint)" | wc -l
echo "State entities:"
sqlite3 workspace/planning-state.db "SELECT COUNT(*) FROM planning_entities;"

# Find orphaned entities (no file)
# (manual check - compare above lists)

# Find missing entities (file but not in state)
/rebuild-state --dry-run | grep "new"
```

---

## Prevention Best Practices

1. **Regular Backups**:
   ```bash
   # Daily backup script
   cp workspace/planning-state.db backups/state-$(date +%Y%m%d).db
   ```

2. **Version Control**:
   - Git commit after major changes
   - Tag milestones: `git tag milestone-act1-complete`

3. **Health Monitoring**:
   - Check `/show-hierarchy` daily
   - Monitor MCP logs
   - Run `/rebuild-state --dry-run` weekly

4. **Graceful Operations**:
   - Don't kill MCP server during operations
   - Use proper shutdown procedures
   - Let hooks complete

5. **Testing Before Production**:
   - Test workflows on test act first
   - Validate backups can be restored
   - Verify cascade behavior on single chapter

---

## Support Resources

- **Documentation**: `.workflows/planning.md`, `.workflows/generation.md`
- **Technical Design**: `features/FEAT-0003-hierarchical-planning/technical-design.md`
- **MCP Server Logs**: `workspace/logs/mcp-server.log`
- **Hook Logs**: Check hook output in command responses

---

## Contact

If recovery procedures fail or data is unrecoverable:

1. Check git history for planning files
2. Search for backup archives
3. Review MCP server logs for errors
4. Check disk space and permissions
5. Consider starting fresh (last resort)

---

## Recovery Checklist

After any emergency recovery:

- [ ] Verify `/show-hierarchy` displays correctly
- [ ] Test approval workflow on one entity
- [ ] Check backup creation works
- [ ] Verify hooks are functioning
- [ ] Test MCP tools (get_entity_state, etc.)
- [ ] Review logs for errors
- [ ] Document what went wrong
- [ ] Update backups
- [ ] Commit recovered state to git
