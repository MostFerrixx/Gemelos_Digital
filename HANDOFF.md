# HANDOFF GUIDE - V11 Migration

> **For New Claude Code Sessions:** Read this first!

---

## Current Status: 31% Complete (PHASE 3 in progress - 5/16 modules done)

**Branch:** `reconstruction/v11-complete`
**Last Updated:** 2025-10-03
**Next Task:** PHASE 3 - Continue creating subsystems (pathfinder.py next)

---

## What Has Been Done

✅ **PHASE 1:** Base structure created (24 directories + setup.py)
✅ **PHASE 2:** 61 files migrated to new structure
⏳ **PHASE 3:** 5/16 subsystem modules created (31% of phase)

**Commits:** 16 total (f338a8a → f9e717c)

---

## What Needs to Be Done Next

### IMMEDIATE TASK: PHASE 3 Continue (1-2 hours remaining)

**COMPLETED (5/16):**
✅ `subsystems/config/settings.py` (132 lines)
✅ `subsystems/config/colors.py` (165 lines)
✅ `subsystems/simulation/warehouse.py` (334 lines)
✅ `subsystems/simulation/operators.py` (410 lines)
✅ `subsystems/simulation/layout_manager.py` (340 lines)

**NEXT PRIORITY:**
6. `subsystems/simulation/pathfinder.py` (CRITICAL - A* algorithm)
7. `subsystems/visualization/state.py` (CRITICAL)
8. `subsystems/visualization/renderer.py` (CRITICAL)
9. ... (8 more modules)

**How to Create Them:**
- Analyze `src/engines/simulation_engine.py` lines 31-46 for imports
- Extract logic from `run_simulator.py` (root)
- Infer class structures from usage patterns

---

## Quick Commands

```bash
# 1. Verify branch
git checkout reconstruction/v11-complete
git status

# 2. See what's done
git log --oneline -8

# 3. View structure
find src/subsystems/ -type d

# 4. Read full status
cat docs/V11_MIGRATION_STATUS.md

# 5. Read master plan
cat docs/MIGRATION_V11.md
```

---

## Key Files to Reference

- `docs/V11_MIGRATION_STATUS.md` ← **FULL STATUS** (436 lines)
- `docs/MIGRATION_V11.md` ← Master plan (719 lines)
- `src/engines/simulation_engine.py` ← Extract imports/logic
- `run_simulator.py` (root) ← V9 baseline reference

---

## Critical Info

- **Original files preserved** in root (don't delete!)
- **Tests in .gitignore** - use `git add -f` to add them
- **git/ directory is empty** - that's why we're rebuilding as subsystems/
- **setup.py ready** - just needs modules to import

---

## Success Criteria for PHASE 3

- [ ] 16 modules created in `src/subsystems/`
- [ ] Can import: `from subsystems.config.settings import LOGICAL_WIDTH`
- [ ] Can import: `from subsystems.simulation.warehouse import AlmacenMejorado`
- [ ] No ModuleNotFoundError when importing

---

## After PHASE 3

- **PHASE 4:** Refactor imports (update all files)
- **PHASE 5:** Testing and validation
- **PHASE 6:** Archive legacy code
- **PHASE 7:** Documentation
- **PHASE 8:** Tag V11.0.0

---

**Questions?** Read `docs/V11_MIGRATION_STATUS.md` for complete details.
