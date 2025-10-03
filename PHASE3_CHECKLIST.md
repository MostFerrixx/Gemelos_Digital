# PHASE 3 Checklist - Create Missing Subsystems Modules

**Estimated Time:** 1 hour REMAINING (was 3-4h)
**Status:** IN PROGRESS - 7/16 DONE (44%)
**Priority:** Continue with dispatcher.py, data_manager.py, assignment_calculator.py

---

## Progress Tracker

**Modules Created:** 7 / 16 (43.75%)
**Current Module:** Ready for next batch (dispatcher, data_manager, assignment_calculator)
**Last Updated:** 2025-10-03
**Commits:** 9d8a5ed, 62b904d, bd56371, f9e717c, 680fa92, 0354acb

---

## Module Creation Checklist

### 1. Config Modules (2/2 COMPLETE ✅)

#### [x] `src/subsystems/config/settings.py` ✅ DONE
**Priority:** 🔴 CRITICAL
**Lines:** 132 lines (commit 9d8a5ed)
**Contains:**
- SUPPORTED_RESOLUTIONS dict
- LOGICAL_WIDTH, LOGICAL_HEIGHT constants
- CAPACIDAD_TRASPALETA, CAPACIDAD_MONTACARGAS
- All global simulation constants

**Reference:**
```bash
grep -n "LOGICAL_WIDTH\|SUPPORTED_RESOLUTIONS" src/engines/simulation_engine.py
```

**Template:**
```python
# src/subsystems/config/settings.py
# -*- coding: utf-8 -*-
"""Global Settings and Constants"""

SUPPORTED_RESOLUTIONS = {
    "Pequena (800x800)": (800, 800),
    # ... more resolutions
}

LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1920
# ... more constants
```

#### [x] `src/subsystems/config/colors.py` ✅ DONE
**Priority:** 🔴 CRITICAL
**Lines:** 165 lines (commit 9d8a5ed)
**Contains:**
- COLOR_FONDO, COLOR_AGENTE_TERRESTRE, etc.
- All color constants for rendering

**Reference:**
```bash
grep -n "COLOR_" src/engines/simulation_engine.py
```

---

### 2. Simulation Modules (5/8 COMPLETE)

#### [x] `src/subsystems/simulation/warehouse.py` ✅ DONE
**Priority:** 🔴 CRITICAL
**Lines:** 334 lines (commit 62b904d)
**Contains:**
- class AlmacenMejorado
- Inventory management
- Order generation
- Dispatcher logic

**Reference:** Extract from `src/engines/simulation_engine.py` and `run_simulator.py`

**Key Methods:**
- `__init__(env, configuracion, ...)`
- `_crear_catalogo_y_stock()`
- `_generar_flujo_ordenes()`
- `simulacion_ha_terminado()`

#### [x] `src/subsystems/simulation/operators.py` ✅ DONE
**Priority:** 🔴 CRITICAL
**Lines:** 410 lines (commit bd56371)
**Contains:**
- def crear_operarios(env, almacen, configuracion, ...)
- class GroundOperator
- class Forklift
- Agent behavior logic

**Reference:**
```bash
grep -A 50 "class.*Operator\|def crear_operarios" run_simulator.py
```

#### [ ] `src/subsystems/simulation/dispatcher.py`
**Priority:** 🟡 HIGH
**Lines:** ~150 lines
**Contains:**
- WorkOrder assignment logic
- Priority queuing
- Agent-task matching

#### [x] `src/subsystems/simulation/layout_manager.py` ✅ DONE
**Priority:** 🔴 CRITICAL
**Lines:** 340 lines (commit f9e717c)
**Contains:**
- class LayoutManager
- TMX file loading (pytmx)
- Grid/pixel coordinate conversion
- Collision matrix generation

**Key Methods:**
- `__init__(tmx_file_path)`
- `grid_to_pixel(grid_x, grid_y)`
- `is_walkable(grid_x, grid_y)`

#### [x] `src/subsystems/simulation/pathfinder.py` ✅ DONE
**Priority:** 🔴 CRITICAL (A* algorithm)
**Lines:** 234 lines (commit 680fa92)
**Contains:**
- class Pathfinder
- A* pathfinding implementation
- Octile distance heuristic
- 8-directional movement

**Key Methods:**
- `find_path(start, goal)` - Returns path or None
- `heuristic(a, b)` - Octile distance
- `get_neighbors(pos)` - 8-directional neighbors with costs

#### [x] `src/subsystems/simulation/route_calculator.py` ✅ DONE
**Priority:** 🟡 HIGH
**Lines:** 346 lines (commit 0354acb)
**Contains:**
- class RouteCalculator
- Multi-stop tour optimization
- Route calculation with segments
- pick_sequence ordering strategy
- Greedy nearest-neighbor alternative

**Key Methods:**
- `calculate_route(start, work_orders, return_to_start)` - Full route info
- `order_work_orders_by_sequence(work_orders)` - Default ordering
- `calculate_greedy_nearest_neighbor(start, work_orders)` - Alternative TSP

#### [ ] `src/subsystems/simulation/assignment_calculator.py`
**Priority:** 🟡 HIGH
**Lines:** ~120 lines
**Contains:**
- class AssignmentCostCalculator
- Cost calculation for task assignment
- Agent-task affinity scoring

#### [ ] `src/subsystems/simulation/data_manager.py`
**Priority:** 🟡 HIGH
**Lines:** ~150 lines
**Contains:**
- class DataManager
- Excel data loading (openpyxl)
- Picking point extraction
- Work area mapping

---

### 3. Visualization Modules (4 files)

#### [ ] `src/subsystems/visualization/state.py`
**Priority:** 🔴 CRITICAL (global state)
**Lines:** ~100 lines
**Contains:**
- estado_visual dict (global)
- def inicializar_estado(...)
- def toggle_pausa()
- def aumentar_velocidad()
- def disminuir_velocidad()

**Structure:**
```python
estado_visual = {
    "operarios": {},
    "work_orders": {},
    "metricas": {},
    "pausa": False,
    "velocidad": 1.0
}
```

#### [ ] `src/subsystems/visualization/renderer.py`
**Priority:** 🔴 CRITICAL (rendering)
**Lines:** ~250 lines
**Contains:**
- class RendererOriginal
- def renderizar_agentes(...)
- def renderizar_mapa_tmx(...)
- Pygame rendering logic

#### [ ] `src/subsystems/visualization/dashboard.py`
**Priority:** 🟡 HIGH
**Lines:** ~180 lines
**Contains:**
- class DashboardOriginal
- Pygame UI for side panel
- Metrics display

#### [ ] `src/subsystems/visualization/hud.py`
**Priority:** 🟢 OPTIONAL
**Lines:** ~80 lines
**Contains:**
- HUD overlay rendering
- On-screen indicators

---

### 4. Utils Modules (1 file)

#### [ ] `src/subsystems/utils/helpers.py`
**Priority:** 🟡 HIGH
**Lines:** ~100 lines
**Contains:**
- def exportar_metricas(...)
- def mostrar_metricas_consola(...)
- General helper functions

---

## Creation Strategy

### Step 1: Start with Config (Required by Everything)
1. Create `settings.py` with all constants
2. Create `colors.py` with all color definitions
3. Test import: `python -c "from subsystems.config.settings import LOGICAL_WIDTH"`

### Step 2: Core Simulation Classes
1. Create `warehouse.py` with AlmacenMejorado
2. Create `operators.py` with agent classes
3. Create `layout_manager.py` for TMX
4. Create `pathfinder.py` for A*

### Step 3: Support Classes
1. Create `dispatcher.py`
2. Create `route_calculator.py`
3. Create `assignment_calculator.py`
4. Create `data_manager.py`

### Step 4: Visualization
1. Create `state.py` with global state
2. Create `renderer.py` with rendering logic
3. Create `dashboard.py` with UI
4. (Optional) Create `hud.py`

### Step 5: Utils
1. Create `helpers.py` with utilities

---

## Validation Commands

After creating each module:

```bash
# Test import
python -c "from subsystems.config.settings import LOGICAL_WIDTH"

# Check syntax
python -m py_compile src/subsystems/config/settings.py

# List what's created
find src/subsystems/ -name "*.py" ! -name "__init__.py"
```

---

## Commit Strategy

Commit after each logical group:

```bash
# After config modules
git add src/subsystems/config/
git commit -m "feat(v11): Create config subsystem (settings, colors)"

# After simulation core
git add src/subsystems/simulation/warehouse.py operators.py layout_manager.py pathfinder.py
git commit -m "feat(v11): Create core simulation modules"

# And so on...
```

---

## Reference Commands

### Extract info from existing code:

```bash
# Find class definitions
grep -n "^class " run_simulator.py

# Find function definitions
grep -n "^def " run_simulator.py

# Find all UPPERCASE constants
grep -n "^[A-Z_]* =" run_simulator.py src/engines/simulation_engine.py

# See how modules are imported
grep -n "from.*import" src/engines/simulation_engine.py
```

### Analyze usage patterns:

```bash
# See how AlmacenMejorado is used
grep -n "AlmacenMejorado\|almacen\." src/engines/simulation_engine.py

# See how LayoutManager is used
grep -n "LayoutManager\|layout_manager\." src/engines/simulation_engine.py
```

---

## Success Criteria

PHASE 3 is complete when:

- [ ] All 16 modules exist
- [ ] All modules have at least minimal implementation
- [ ] No syntax errors in any module
- [ ] Can import all critical classes:
  - `from subsystems.config.settings import LOGICAL_WIDTH`
  - `from subsystems.simulation.warehouse import AlmacenMejorado`
  - `from subsystems.simulation.operators import crear_operarios`
  - `from subsystems.visualization.state import estado_visual`
  - `from subsystems.visualization.renderer import RendererOriginal`
- [ ] All __init__.py files export the classes
- [ ] Committed with descriptive messages

---

## After PHASE 3

Move to **PHASE 4: Refactor Imports**
- Update all files in `src/` to use new imports
- Remove `sys.path.insert()` hacks
- Validate all imports resolve correctly

---

**Need Help?** See `docs/V11_MIGRATION_STATUS.md` section "PHASE 3: Create Missing Subsystems Modules"
