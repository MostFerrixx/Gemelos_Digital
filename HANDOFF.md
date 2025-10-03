# HANDOFF GUIDE - V11 Migration

> **For New Claude Code Sessions:** Read this first!

---

## Current Status: 63% Complete (PHASE 3 in progress - 10/16 modules done)

**Branch:** `reconstruction/v11-complete`
**Last Updated:** 2025-10-03
**Next Task:** PHASE 3 - Continue creating subsystems (visualization modules next)

---

## What Has Been Done

✅ **PHASE 1:** Base structure created (24 directories + setup.py)
✅ **PHASE 2:** 61 files migrated to new structure
⏳ **PHASE 3:** 10/16 subsystem modules created (63% of phase)
✅ **SIMULATION SUBSYSTEM:** Complete (8/8 modules)

**Commits:** 21 total (f338a8a → current)

---

## What Needs to Be Done Next

### IMMEDIATE TASK: PHASE 3 Continue (20-30 min remaining)

**COMPLETED (10/16):**
✅ `subsystems/config/settings.py` (132 lines)
✅ `subsystems/config/colors.py` (165 lines)
✅ `subsystems/simulation/warehouse.py` (334 lines)
✅ `subsystems/simulation/operators.py` (410 lines)
✅ `subsystems/simulation/layout_manager.py` (340 lines)
✅ `subsystems/simulation/pathfinder.py` (234 lines) - A* algorithm
✅ `subsystems/simulation/route_calculator.py` (346 lines) - Multi-stop tours
✅ `subsystems/simulation/data_manager.py` (408 lines) - Excel/TMX data loader
✅ `subsystems/simulation/assignment_calculator.py` (403 lines) - Cost calculator
✅ `subsystems/simulation/dispatcher.py` (552 lines) - WorkOrder orchestration ✨ NEW

**NEXT PRIORITY (6 modules remaining):**
11. `subsystems/visualization/state.py` (CRITICAL)
12. `subsystems/visualization/renderer.py` (CRITICAL)
13. `subsystems/visualization/dashboard.py` (HIGH)
14. `subsystems/visualization/hud.py` (OPTIONAL)
15. `subsystems/utils/helpers.py` (HIGH)
16. One more module (to be determined)

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
