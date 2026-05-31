# AUDITORÍA COMPLETA — Gemelo Digital de Almacén

> **Modo:** Solo lectura. No se modificó, creó ni eliminó ningún archivo de código ni se ejecutó ningún comando Git destructivo. Este documento es el único entregable.
> **Fecha de auditoría:** 2026-05-30
> **Rama auditada:** `main` (HEAD `4ea62e9`), más inspección de las 8 ramas restantes y del working dir sin commitear.
> **Auditor:** Claude (Opus 4.8) — Claude Code.

---

## 0. Cómo leer este informe (niveles de certeza)

Para respetar la regla de "no asumas", cada afirmación se etiqueta:

- **SÉ** — Verificado con evidencia directa (grep de imports, contenido leído, conteos de Git). Se cita la evidencia (`archivo:línea`).
- **SOSPECHO** — Inferencia fuerte por convención (nombres `_OLD`, duplicados) pero sin prueba de import en ambos sentidos.
- **INCIERTO** — No se puede determinar en solo lectura (scripts que podrían ejecutarse a mano, docs no leídos línea a línea, rutas ambiguas). Se explica por qué.

---

## 1. Resumen ejecutivo

El proyecto es un **simulador de gemelo digital de almacén en Python** con una arquitectura objetivo razonable (motor headless SimPy → archivo `.jsonl` de replay → visualizador Pygame + analytics Excel), pero **el repositorio está sedimentado por ~6 meses de iteraciones sucesivas sin limpieza estructural**. Los síntomas dominantes:

1. **El módulo canónico convive con copias huérfanas.** El paquete `src/` es el destino arquitectónico declarado, pero hay código vivo *fuera* de `src/` (p.ej. `simulation_buffer.py`, `visualizer.py`, `configurator.py` en la raíz) y copias muertas *dentro* de `src/` (p.ej. `src/shared/buffer.py`). No se puede asumir "raíz = viejo, src = nuevo": es caso por caso.
2. **Duplicación de carpetas de datos**: `layouts/` vs `data/layouts/`, `tilesets/` vs `data/tilesets/`, `assets/` vs `data/assets/`, `config.json` vs `data/config/config.json`, `dashboard_theme.json` vs `data/themes/`.
3. **Dos aplicaciones web** (`web_prototype/` viva, `web_dashboard/` huérfana) y **dos configuradores** (`configurator.py` de escritorio de 4146 líneas + el web).
4. **Tres dashboards de visualización solapados** (`dashboard.py` 2536 líneas, `dashboard_world_class.py` 1597, `dashboard_modern.py` 547), todos importados por el motor de replay, con la misma clase `DashboardWorldClass` definida en dos sitios.
5. **Documentación 1–2 versiones por detrás del código.** README/`setup.py`/INSTRUCCIONES dicen **V11**; los commits de `main` son **V12**; el working tree tiene una feature **V12.1** sin commitear. Varios docs exigen leer archivos que ya no existen (`ACTIVE_SESSION_STATE.md`).
6. **`main` ya absorbió casi todo.** De las 8 ramas restantes, 6 tienen **0 commits propios** respecto a `main`; solo 2 conservan trabajo único, y aun ese es viejo y probablemente superado (ver §6).
7. **Trabajo valioso sin commitear**: la "Allocation Layer V12.1" (asignación por stock disponible) está a medias en el working dir. Es coherente y debería preservarse.

**Veredicto de salud:** el *núcleo de simulación* (`src/subsystems/simulation/` + `src/engines/event_generator.py`) está sano y es claramente el activo principal. El desorden está en la periferia (raíz, `legacy/`, `tests/`, datos duplicados, docs) y es **deuda de organización, no de lógica**. Es un candidato ideal para una limpieza por fases de bajo riesgo.

---

## 2. Arquitectura actual

### 2.1 Stack tecnológico (SÉ — `requirements.txt`, `setup.py`, imports)

| Capa | Tecnología | Evidencia |
|---|---|---|
| Simulación de eventos discretos | **SimPy** ≥4.0 | `event_generator.py:10`, requirements |
| Visualización de replay | **Pygame / pygame-ce + pygame_gui** | `replay_engine.py:16,26`, requirements |
| Dashboard de WorkOrders | **PyQt6** (proceso aparte vía IPC) | `work_order_dashboard.py`, `communication/` |
| Mapas de almacén | **pytmx** (formato Tiled `.tmx`) | `layout_manager.py`, `server.py:12` |
| Reportes ejecutivos | **pandas + openpyxl** | `analytics_engine.py:7,12` |
| Persistencia de datos | **SQLite** (migración V12) | `src/subsystems/database/`, `warehouse.db` |
| Optimización de parámetros | **Optuna** | `src/tools/optimizer.py:22` |
| App web | **FastAPI + uvicorn + pydantic** | `web_prototype/server.py:7-11` |

> ⚠️ **Riesgo de dependencias (SÉ):** FastAPI, uvicorn y pydantic **no están en `requirements.txt`** pese a ser obligatorios para `web_prototype/server.py` y `web_dashboard/server.py`. Un `pip install -r requirements.txt` limpio **no levanta el servidor web**.

### 2.2 Estructura de carpetas (alto nivel)

```
Gemelos Digital/
├── entry_points/         # Lanzadores (VIVO): run_generate_replay, run_replay_viewer, run_optimization
├── src/                  # Paquete principal (mayormente VIVO)
│   ├── engines/          # event_generator (headless), replay_engine (viewer), analytics_engine
│   ├── subsystems/
│   │   ├── simulation/   # NÚCLEO: warehouse, dispatcher, operators, order_strategies, data_manager...
│   │   ├── visualization/# 3 dashboards + renderer + state + replay_scrubber + work_order_dashboard
│   │   ├── config/       # settings, colors
│   │   ├── database/     # database_manager, importer, schema.sql (V12, SQLite)
│   │   └── utils/        # helpers (VIVO)
│   ├── core/             # config_manager, config_utils, replay_utils (VIVO)
│   ├── analytics/        # exporter_v2 (VIVO), exporter v1 (legado), context
│   ├── communication/    # IPC PyQt6: dashboard_communicator, lifecycle_manager, ipc_protocols (VIVO)
│   ├── shared/           # buffer + diagnostic_tools (MUERTO: nadie importa)
│   └── tools/            # optimizer (VIVO)
├── web_prototype/        # App web VIVA (FastAPI, puerto 8000)
├── web_dashboard/        # App web HUÉRFANA (puerto 8001)
├── legacy/               # *_OLD (MUERTO por diseño)
├── tools/                # Scripts sueltos: inspect_db (reciente), + duplicados muertos
├── utils/                # Isla MUERTA (solo se auto-importa)
├── tests/                # Mayormente ROTO (importa módulos borrados)
├── archived/             # Documentación histórica (.md)
├── docs/, data/layouts/  # Guías de usuario (.md) + mapas TMX
├── layouts/, tilesets/,  # ⚠️ DUPLICADOS de data/layouts, data/tilesets, data/assets
│   assets/, configurations/, custom_textures/, data/
├── simulation_buffer.py  # ReplayBuffer (VIVO — lo importa event_generator)
├── visualizer.py         # Generador de heatmap (VIVO — subprocess desde exporter_v2)
├── configurator.py       # Configurador de escritorio (VIVO, 4146 líneas)
├── analyze_events.py     # Script suelto (INCIERTO — sin referencias)
├── run_migration.py      # Migración Excel→SQLite (VIVO)
├── server_manager.py / start_hidden.py  # Gestión del servidor web (VIVO)
├── *.bat                 # start/stop/restart/status_server (VIVO)
├── files_to_delete.txt / generate_files_to_delete_list.py  # Restos de limpieza (MUERTO)
└── config.json           # Configuración principal (VIVO)
```

### 2.3 Flujo de ejecución real (SÉ — rastreo de imports)

Hay **cuatro puntos de entrada vivos**, cada uno con su cadena de dependencias:

**A) Generación headless** — `make sim` / `run.bat sim`
```
entry_points/run_generate_replay.py
  └─> engines.event_generator.EventGenerator            (event_generator.py:15)
        ├─> subsystems.simulation.warehouse.AlmacenMejorado
        │      ├─> .order_strategies (create_order_strategy)   (warehouse.py:10)
        │      └─> .dispatcher.DispatcherV11 (import diferido)  (warehouse.py:199)
        ├─> subsystems.simulation.{operators, layout_manager,
        │      assignment_calculator, data_manager, pathfinder, route_calculator}
        ├─> core.{config_manager, config_utils, replay_utils}
        ├─> analytics.exporter_v2.AnalyticsExporter           (event_generator.py:28)
        │      └─> engines.analytics_engine.AnalyticsEngine
        │      └─> (subprocess) ../../visualizer.py  →  heatmap PNG  (exporter_v2.py:369-403)
        ├─> analytics.context.SimulationContext
        └─> simulation_buffer.ReplayBuffer  [ARCHIVO RAÍZ]    (event_generator.py:32)
```

**B) Visualización de replay** — `make replay FILE=...`
```
entry_points/run_replay_viewer.py
  └─> engines.replay_engine.ReplayViewerEngine            (run_replay_viewer.py:15)
        ├─> communication.ipc_protocols (eventos Event Sourcing)
        ├─> communication.dashboard_communicator.DashboardCommunicator
        │      └─> communication.lifecycle_manager.ProcessLifecycleManager
        │      └─> (subproceso PyQt6) subsystems.visualization.work_order_dashboard
        ├─> subsystems.visualization.{state, renderer, dashboard,
        │      dashboard_modern, dashboard_world_class, replay_scrubber}
        ├─> subsystems.config.{settings, colors}
        ├─> subsystems.simulation.layout_manager
        └─> core.{config_manager, config_utils}
```

**C) Optimización** — `python entry_points/run_optimization.py`
```
run_optimization.py ─> src.tools.optimizer.SimulationOptimizer  (Optuna)
        └─> (subprocess) entry_points/run_generate_replay.py --config ... --output-metrics ...
```

**D) Servidor web** — `start_server.bat` / `server_manager.py start`
```
start_hidden.py / server_manager.py / start_server.bat
  └─> web_prototype/server.py  (FastAPI, puerto 8000)
        └─> web_prototype.{config_manager, simulation_runner}
                                  (simulation_runner orquesta run_generate_replay)
```

**Observación arquitectónica clave:** la comunicación entre subsistemas es razonablemente limpia *dentro* de `src/`, pero **la cohesión del paquete está rota**: hay nodos vivos del grafo que viven en la raíz (`simulation_buffer.py`, `visualizer.py`) y se invocan o por import directo o por `subprocess` con rutas relativas calculadas a mano (`exporter_v2.py:369`). Ver §3.

---

## 3. Dependencias y acoplamientos problemáticos

### 3.1 Caos de rutas de import (SÉ — RIESGO ALTO)

Conviven **cinco estilos de import distintos** para el mismo código:
- `from engines.event_generator import ...` (depende de que `src/` esté en `sys.path`)
- `from subsystems.simulation.warehouse import ...` (idem)
- `from src.tools.optimizer import ...` (con prefijo `src.`) — `run_optimization.py:25`
- `from src.communication.ipc_protocols import ...` — varios tests
- `from .order_strategies import ...` (relativo) — `warehouse.py:10`

Cada entry point parchea `sys.path` a mano (`run_generate_replay.py:12-13`, `run_replay_viewer.py:12`, `run_optimization.py:20-22`). Peor: **`replay_engine.py:9` inserta en el path una carpeta `'git'` inexistente** (`sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'git'))`) — residuo de un archivo accidental llamado `git` que vive en la rama `fix/configurator-tool` (ver §6). Esto hace el orden de import frágil y dependiente del directorio de trabajo.

**Causa raíz:** `setup.py` declara `find_packages(where="src")`, pero hay **código vivo fuera de `src/`** (`simulation_buffer.py`, `visualizer.py`, `configurator.py`, `web_prototype/`, `run_migration.py`, `server_manager.py`). El proyecto nunca se instala como paquete (`pip install -e .`), así que todo depende de `sys.path` en runtime.

### 3.2 Tres dashboards solapados (SÉ — RIESGO MEDIO)

`replay_engine.py:54-56` importa de los tres a la vez:
```python
from subsystems.visualization.dashboard import DashboardOriginal, DashboardGUI, DashboardWorldClass   # 2536 líneas
from subsystems.visualization.dashboard_modern import ModernDashboard                                  # 547 líneas
from subsystems.visualization.dashboard_world_class import DashboardWorldClass as DashboardWC          # 1597 líneas
```
La clase **`DashboardWorldClass` está definida en DOS archivos** (`dashboard.py` y `dashboard_world_class.py`) e importada con dos alias. ~4680 líneas de UI con responsabilidad solapada. Cuál se usa realmente en runtime es **INCIERTO** sin leer la lógica de selección en `replay_engine`.

### 3.3 Dos configuradores y dos apps web (SÉ)

- **Configurador escritorio** (`configurator.py`, 4146 líneas, PyQt/Tk) + **configurador web** (`web_prototype/static/web_configurator/`). Funcionalidad equivalente, dos bases de código.
- **App web mapa** (`web_prototype`, puerto 8000, VIVA) + **App web tabla WO** (`web_dashboard`, puerto 8001, huérfana). Ambas con la **misma ruta hardcodeada** a un replay que probablemente ya no existe (`output/simulation_20251120_224852/replay_20251120_224852.jsonl`, en `server.py:57` y `web_dashboard/server.py:31-37`).

### 3.4 Acoplamiento a rutas absolutas de máquina (SÉ — RIESGO ALTO de portabilidad)

`config.json` (working dir) tiene:
```json
"order_file_path": "C:\\Users\\ferri\\OneDrive\\Escritorio\\Gemelos Digital\\uploads\\orders_ordenes_prueba_real.json"
```
Apunta a **OneDrive\Escritorio**, mientras que el repositorio auditado vive en **`D:\Documentos\Martin\Gemelos Digital`**. Es decir, la config apunta a *otra copia del proyecto*. Riesgo de ejecuciones que leen datos de una ubicación equivocada.

---

## 4. Inventario: ACTIVOS vs MUERTOS vs INCIERTOS

### 4.1 ACTIVOS (SÉ — con cadena de import o invocación verificada)

| Archivo / grupo | Por qué está vivo (evidencia) |
|---|---|
| `entry_points/run_generate_replay.py`, `run_replay_viewer.py`, `run_optimization.py` | Lanzadores referenciados en `Makefile`, `run.bat`, `README` |
| `src/engines/event_generator.py` | Importado por `run_generate_replay.py:15` |
| `src/engines/replay_engine.py` | Importado por `run_replay_viewer.py:15` |
| `src/engines/analytics_engine.py` | Importado por `analytics/exporter_v2.py:16` |
| `src/subsystems/simulation/*` (warehouse, dispatcher, operators, order_strategies, data_manager, layout_manager, assignment_calculator, pathfinder, route_calculator) | Cadena desde `event_generator`; `dispatcher` vía `warehouse.py:199`, `order_strategies` vía `warehouse.py:10` |
| `src/core/{config_manager, config_utils, replay_utils}` | Importados por ambos motores |
| `src/analytics/exporter_v2.py`, `context.py` | Importados por `event_generator.py:28-29` |
| `src/subsystems/visualization/{state, renderer, dashboard, dashboard_modern, dashboard_world_class, replay_scrubber, work_order_dashboard}` | Importados por `replay_engine.py:53-57` y `dashboard_communicator.py:211` |
| `src/subsystems/config/{settings, colors}` | Importados por `replay_engine.py:35-37` |
| `src/communication/{ipc_protocols, dashboard_communicator, lifecycle_manager, __init__}` | Cadena desde `replay_engine` |
| `src/subsystems/utils/helpers.py` | Importado por `exporter_v2.py:17` |
| `src/subsystems/database/{database_manager, importer, schema.sql}` | Importados por `run_migration.py:29-30` |
| `src/tools/optimizer.py` | Importado por `run_optimization.py:25` |
| **`simulation_buffer.py` (RAÍZ)** | Importado por `event_generator.py:32` — **es el buffer canónico, no `src/shared/buffer.py`** |
| **`visualizer.py` (RAÍZ)** | Ejecutado por subprocess desde `exporter_v2.py:369-403` (`script_dir` = raíz del proyecto) |
| `configurator.py` (RAÍZ) | Entry point en `Makefile:41`, `run.bat:47`, `README:49` (`python configurator.py`) |
| `run_migration.py`, `server_manager.py`, `start_hidden.py` (RAÍZ) | Migración DB / gestión servidor; referenciados en `README`, `start_server.bat:113` |
| `web_prototype/**` | App web lanzada por `start_hidden.py:6`, `server_manager.py:19`, `start_server.bat:4` |
| `*.bat` (start/stop/restart/status_server, run) | Scripts de operación |

### 4.2 MUERTOS (SÉ — sin imports de entrada + supersedido)

| Archivo / grupo | Evidencia de muerte |
|---|---|
| **`legacy/` (carpeta completa)** | Sufijo `_OLD`; `grep "import legacy"` = **0 resultados**; sus archivos importan módulos ya borrados (`engines.simulation_engine` en `run_live_simulation_OLD.py:19`). Muerto por diseño. |
| **`src/shared/buffer.py`** | Nadie importa `shared`/`src.shared` (grep = 0). Supersedido por `simulation_buffer.py` (raíz), que es el que importa `event_generator`. |
| **`src/shared/diagnostic_tools.py`** | Mismo motivo: sin imports de entrada. |
| **`src/shared/__init__.py`** | Paquete huérfano (su contenido no se importa). |
| **`utils/` (RAÍZ: `__init__.py`, `diagnostic_tools.py`)** | Solo se auto-importa (`utils/__init__.py:9`); ningún módulo externo importa `utils`. Isla muerta. |
| **`tools/configurator.py`** | Duplicado del `configurator.py` raíz; no se importa ni lo referencian scripts. |
| **`tools/visualizer.py`** | Duplicado del `visualizer.py` raíz (mismas líneas de ayuda CLI); el vivo es el de la raíz. |
| **`communication/` (RAÍZ, sin trackear) + `src/communication/test_dashboard_communicator.py`** | Importan `communication.simulation_data_provider`, módulo **borrado** (HANDOFF:101). Tests muertos. |
| **Gran parte de `tests/`** | Importan módulos inexistentes: `engines.simulation_engine` (`test_dashboard_cleanup.py:8`, `test_multi_operators_dashboard.py:39`), `communication.replay_data_provider` y `ReplayEngineDataProvider` (`test_dashboard_automation.py:117`), `communication.simulation_data_provider`. **No ejecutan.** |
| **`files_to_delete.txt`, `generate_files_to_delete_list.py`** | Herramienta de una limpieza pasada; residuo. |
| **`config_optimized_20251128_154628.json`, `config_optimized_20251128_182004.json` (RAÍZ)** | Salidas del optimizador commiteadas por error (deberían ir a `optimized_configs/`, que está en `.gitignore`). |

### 4.3 Funcionalmente muerto pero técnicamente cargado (SÉ — matiz importante)

| Archivo | Situación |
|---|---|
| **`src/analytics/exporter.py` (V1)** | `grep` confirma que **nadie** hace `from analytics.exporter import` directamente. PERO `src/analytics/__init__.py:10` lo re-exporta como `AnalyticsExporterV1`, así que se carga como efecto colateral al importar `analytics.exporter_v2`. **El que se usa es V2.** Candidato a eliminación, pero requiere editar también `__init__.py`. |
| `legacy/analytics_OLD/__init__.py:10` | Misma estructura V1, dentro de `legacy/` (doblemente muerto). |

### 4.4 INCIERTOS (no determinable en solo lectura)

| Archivo / grupo | Por qué es incierto |
|---|---|
| **`analyze_events.py` (RAÍZ, 147 líneas)** | No se importa ni lo referencian scripts/bat (grep = 0). Probable utilidad de análisis manual. No puedo descartar que el usuario lo ejecute a mano. |
| **`web_dashboard/` (carpeta)** | Tiene propósito **distinto** de `web_prototype` (tabla de WO en puerto 8001 vs mapa en 8000; su README dice "ambos pueden ejecutarse simultáneamente"). PERO ningún script lo arranca y su ruta de replay está hardcodeada y obsoleta. **SOSPECHO abandonado**, pero es una mini-app completa y revivible. |
| **`tools/inspect_tmx.py` vs `tools/inspector_tmx.py`** | Par casi idéntico de inspectores TMX, ambos standalone, sin referencias. Al menos uno es redundante (SOSPECHO), pero no sé cuál usa el usuario. |
| **`tools/inspect_db.py`** | Añadido en el commit más reciente (`4ea62e9`, "database inspection script"). Standalone, sin imports de entrada → se ejecuta a mano. Probablemente VIVO/útil, pero por uso manual (INCIERTO formalmente). |
| **`layouts/` vs `data/layouts/`** | **Ambos referenciados por código distinto**: `exporter_v2.py:371` usa `layout_file` con default `'layouts/WH1.tmx'` (raíz); `web_prototype/server.py:55` apunta a `data/layouts/layout_v2.tmx` (que **no existe** en el repo). **Resuelto en §13.8:** raíz canónico; falta arreglar la ruta web rota (`data/layouts/layout_v2.tmx` no existe). |
| `tilesets/`, `assets/`, `config.json`, `dashboard_theme.json` (raíz) vs sus copias en `data/` | **Resuelto en §13.8:** la raíz es la fuente viva; `data/` solo lo usa código muerto/roto; `assets/` (ambas copias) están muertas. |
| Archivos `.md` en `docs/` y `data/layouts/` | No leídos línea a línea (ver §7). |

---

## 5. Estado de las ramas (Git — solo lectura)

`git rev-list --count` y `git log main..<rama>` sobre las 9 ramas locales:

| Rama | Adelante de `main` | Detrás de `main` | Último commit | Veredicto |
|---|---:|---:|---|---|
| **`main`** ⭐ | — | — | (HEAD `4ea62e9`) | **Canónica. La más avanzada.** |
| `backup-main-damaged` | **0** | 92 | 2025-10-10 | Backup obsoleto. Nada que rescatar. |
| `backup-main-damaged-20251010-141528` | **0** | 135 | 2025-09-26 | Backup más viejo. Nada que rescatar. |
| `experimental-tiled-migration` | **0** | 192 | 2025-08-15 | Migración TMX ya absorbida en `main`. |
| `feat/replay-scrubber` | **0** | 90 | 2025-10-10 | Ya fusionada en `main` (0 commits propios). |
| `feature/event-sourcing-impl-1` | **0** | 78 | 2025-10-13 | Ya fusionada en `main`. |
| `reconstruction/v11-complete` | **0** | 93 | 2025-10-10 | Ya fusionada en `main`. |
| `feat/realtime-workorder-dashboard` | **14** | 87 | 2025-10-12 | ⚠️ Commits propios, pero ver abajo. |
| `fix/configurator-tool` | **13** | 135 | 2025-10-02 | ⚠️ Commits propios, muy viejos, ver abajo. |

### 5.1 Desmontando el mito del "trabajo disperso"

Contrario a lo temido, **`main` ya consolidó el grueso del trabajo**: 6 de 8 ramas tienen **0 commits únicos** (todo lo suyo está en `main`). Los dos backups `*-damaged` confirman que `main` se reconstruyó en algún momento (oct-2025) y la reconstrucción ya está en `main`.

**Solo dos ramas tienen contenido único, y ambas son sospechosas de estar superadas:**

- **`feat/realtime-workorder-dashboard`** (14 commits, hasta 2025-10-12; 87 detrás). Aporta el dashboard PyQt6 de WorkOrders en tiempo real (+456 líneas en `work_order_dashboard.py`, +320 en `replay_engine.py`, +177 en `dashboard_communicator.py`) y 3 docs de auditoría (`AUDITORIA_ARQUITECTURA_DASHBOARD_PYQT6.md`, etc.). **PERO `main` YA contiene `work_order_dashboard.py`, `dashboard_communicator.py`, `lifecycle_manager.py` e `ipc_protocols.py`** — la feature parece haberse integrado en `main` por otra vía. **INCIERTO si quedan fixes no portados**; sus 14 commits podrían ser una versión paralela/anterior. **Recomendación: diff de contenido dirigido antes de descartar; no borrar a ciegas.**

- **`fix/configurator-tool`** (13 commits, hasta 2025-10-02; 135 detrás — muy vieja). Aporta un `configurator.py` muy reescrito (+1438), `docs/MIGRATION_V11.md` (+719), `layouts/WH1_sequence.csv`, y **`run_simulator.py` (+2529 líneas)** — el monolito pre-refactor que ya **no existe en `main`** (fue partido en `engines/`). También arrastra un **archivo llamado literalmente `git`** (causa del `sys.path.insert(...,'git')` de `replay_engine.py:9`). El monolito es claramente obsoleto; lo único potencialmente rescatable son mejoras de UI del configurador, pero la rama es de hace ~8 meses. **INCIERTO; bajo valor esperado.**

> **No se mezcló ni se modificó ninguna rama.** Las recomendaciones de consolidación/borrado están en §9, fase 0.

---

## 6. Riesgos y deuda técnica

| # | Riesgo / deuda | Severidad | Evidencia |
|---|---|---|---|
| R1 | `requirements.txt` no declara FastAPI/uvicorn/pydantic → la app web no instala limpia | **Alta** | `server.py:7-11` vs `requirements.txt` |
| R2 | `setup.py` referencia entry points inexistentes (`run_live_simulation`, `run_simulation`, `tools.configurator`) e `install_requires` no coincide con `requirements.txt` | **Alta** | `setup.py:39-43, 23-31` |
| R3 | Rutas absolutas de máquina en `config.json` apuntando a otra copia (OneDrive) | **Alta** | `config.json` (working dir) |
| R4 | `warehouse.db` (binario SQLite), `uploads/`, `ordenes_prueba_real.json` **sin trackear y sin gitignorar** → riesgo de commitear binarios/datos | **Media** | `git status` |
| R5 | `sys.path` parcheado a mano en cada entry point + ruta fantasma `'git'` | **Media** | `replay_engine.py:9`, entry points |
| R6 | 3 dashboards solapados con clase `DashboardWorldClass` duplicada | **Media** | `replay_engine.py:54-56` |
| R7 | Rutas de replay/TMX hardcodeadas y obsoletas en ambas apps web | **Media** | `server.py:55-57`, `web_dashboard/server.py:31-37` |
| R8 | `tests/` mayormente roto (importa módulos borrados) → falsa sensación de cobertura | **Media** | §4.2 |
| R9 | `.gitignore` de **605 líneas** acumulando patrones de decenas de sesiones de debug; ignora `test_*.py` pero hay tests trackeados igual (inconsistente) | **Baja** | `.gitignore`, `git ls-files tests/` |
| R10 | Monolitos: `configurator.py` 4146, `dashboard.py` 2536, `dispatcher.py` 1318, `operators.py` 1128, `web_prototype/server.py` 1167 | **Baja-Media** | conteo de líneas |
| R11 | Duplicación de datos (`layouts/` vs `data/layouts/`, etc.) sin fuente de verdad única | **Media** | §4.4 |
| R12 | Documentación 1–2 versiones por detrás; exige leer archivos inexistentes | **Media** | §7 |

### 6.1 Código duplicado confirmado (SÉ)

- `visualizer.py` (raíz, vivo) ≡ `tools/visualizer.py` (muerto).
- `configurator.py` (raíz, vivo) ≈ `tools/configurator.py` (muerto).
- `simulation_buffer.py` (raíz, vivo) ≈ `src/shared/buffer.py` (muerto).
- `diagnostic_tools`: `src/shared/` (muerto) vs `utils/` (muerto) vs `src/subsystems/utils/helpers.py` (vivo).
- `analytics`: `exporter.py` V1 (legado) vs `exporter_v2.py` (vivo); duplicado a su vez en `legacy/analytics_OLD/`.
- `dashboard.py::DashboardWorldClass` ≡ `dashboard_world_class.py::DashboardWorldClass`.
- `tools/inspect_tmx.py` ≈ `tools/inspector_tmx.py`.

---

## 7. Documentación `.md`: vigente vs obsoleta

| Documento | Estado | Justificación |
|---|---|---|
| `README.md` | **Parcialmente obsoleto** | Arquitectura headless+replay correcta, pero dice "V11", no menciona SQLite/DB (V12) ni la allocation layer; sección "Estructura" omite `web_prototype`, `database/`. |
| `HANDOFF.md` | **Obsoleto + corrupto** | Su contenido está **duplicado internamente** (se repite ~2 veces, líneas 44–250 ≈ 250–447): corrupción por merge. Última fecha 2025-11-25, no refleja V12. |
| `INSTRUCCIONES.md` | **Parcialmente vigente** | Estructura `src/` correcta y útil, pero "V11", sin DB ni web server. Fecha 2025-10-27. |
| `.cursorrules` | **Obsoleto** | Exige leer `ACTIVE_SESSION_STATE.md` y `PLAN_SISTEMA_SLOTS_CONFIGURACION.md`, **ambos inexistentes en `main`**. Apunta a rama `reconstruction/v11-complete` (ya superada). |
| `.cursor/rules/documentation_update.mdc` | INCIERTO | No leído en detalle; presumiblemente reglas de doc para Cursor. |
| `setup.py` (no es .md pero documenta) | **Obsoleto** | Ver R2. |
| `web_dashboard/README.md` | **Describe app huérfana** | Documenta correctamente una app que ningún script arranca (ver §4.4). |
| `web_prototype/` | **Sin README** | La app web viva no tiene documentación propia. |
| `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md` | **Probablemente vigente (técnico)** | El "doble barrido" sigue en `dispatcher.py` (HANDOFF lo confirma). No leído íntegro → INCIERTO en detalles. |
| `docs/DYNAMIC_LAYOUTS_USER_GUIDE.md`, `docs/TILES_REFERENCE.md` | **Presumiblemente vigentes** | Guías del sistema de layouts TMX, que es núcleo. No auditadas línea a línea → INCIERTO. |
| `data/layouts/INSTRUCCIONES_LAYOUTS.md`, `INSTRUCCIONES_LAYOUT_PERSONALIZADO.md`, `TUTORIAL_EXPLICACION.md` | **Presumiblemente vigentes** | Guías de usuario de layouts. No leídas en detalle. |
| `archived/**` (16 archivos) | **Histórico por diseño** | Auditorías y planes de limpieza pasados. Vigentes *como registro histórico*, no como doc operativa. Mantener en `archived/` o mover a una carpeta de histórico. |
| **`ACTIVE_SESSION_STATE.md`** | **AUSENTE** | Referenciado como "obligatorio" por HANDOFF/.cursorrules pero **no existe en `main`** (sí en la rama `feat/realtime-workorder-dashboard`). Documentación rota. |

---

## 8. Working dir sin commitear: Allocation Layer V12.1 (SÉ — `git diff`)

Los 4 cambios sin commitear **no son ruido: son una feature coherente en desarrollo**. `git diff --stat`: 184 inserciones / 9 borrados en 4 archivos.

| Archivo | Cambio | Detalle |
|---|---|---|
| `src/subsystems/simulation/data_manager.py` | +64 | Nuevos métodos de stock (`get_available_stock(sku_code)`, consultas SQLite) para la capa de asignación |
| `src/subsystems/simulation/order_strategies.py` | +112 | `DeterministicOrderStrategy` ahora valida stock disponible (algoritmo FCFS) antes de crear WorkOrders; `ValidationResult` registra `unfilled_demand` y `allocation_summary` |
| `src/subsystems/simulation/warehouse.py` | +15 | `WorkOrder` ahora distingue `qty_requested` vs `qty_allocated` y marca `is_partial` (cumplimiento parcial por stock insuficiente) |
| `config.json` | ±2 | `order_file_path` cambiado a `uploads/orders_ordenes_prueba_real.json`, `total_ordenes: 150` |

**Veredicto:** trabajo de valor sobre la ruta de código viva (`order_strategies` y `data_manager` están confirmados activos). **Recomendación: preservar y commitear** en una rama propia antes de cualquier limpieza, para no perderlo. Está claramente etiquetado en el propio código como `ALLOCATION LAYER (V12.1)`.

---

## 9. Plan de limpieza / refactorización por fases

> Todas las fases son **propuestas**. Nada de esto se ejecutó en esta sesión. Orden pensado para minimizar riesgo: primero asegurar, luego borrar lo inequívoco, luego reorganizar, por último refactorizar.

### Fase 0 — Asegurar el estado actual (antes de tocar nada)
1. Crear rama `feature/allocation-layer-v12.1` y **commitear los cambios del working dir** (§8) para no perder la feature.
2. Añadir a `.gitignore`: `warehouse.db`, `uploads/`, `*.db`. Sacar del control de versiones `config_optimized_*.json` de la raíz.
3. Hacer un `git tag` de respaldo de `main` (p.ej. `pre-cleanup-2026-05-30`) — ya existe precedente (`pre-cleanup-20251125-171903`).

### Fase 1 — Borrado de muerto inequívoco (riesgo ~nulo, §4.2)
4. Eliminar `legacy/` completa.
5. Eliminar `src/shared/`, `utils/` (raíz), `communication/` (raíz), `tools/configurator.py`, `tools/visualizer.py`.
6. Eliminar `files_to_delete.txt`, `generate_files_to_delete_list.py`.
7. Eliminar/segregar `tests/` roto (los que importan `simulation_engine`, `simulation_data_provider`, `replay_data_provider`). Decidir si se reescriben o se borran.
> Validar tras cada borrado: `python entry_points/run_generate_replay.py` y `run_replay_viewer.py` deben seguir funcionando.

### Fase 2 — Resolver duplicación de datos y dependencias (§3, §4.4)
8. Consolidar la fuente de datos en la **raíz** (es la que lee el código vivo; ver §13.8): borrar `data/config/`, `data/assets/` y `assets/` (muertas), rescatar las guías de `data/layouts/` → `docs/`, evaluar los Excel extra `Warehouse_Logic_WA/_Zonas.xlsx`, y arreglar la ruta rota `web_prototype/server.py:55`. **Unificar `Warehouse_Logic.xlsx`** (raíz vs `data/layouts/`) — es un bug de correctitud (§13.8).
9. Arreglar `requirements.txt` (añadir fastapi, uvicorn, pydantic) y `setup.py` (entry points reales, deps alineadas) — o consolidar en `pyproject.toml`.
10. Reemplazar rutas absolutas de `config.json` por rutas relativas al proyecto.
11. Eliminar el `sys.path.insert(...,'git')` de `replay_engine.py:9`.

### Fase 3 — Reorganización del paquete (§3.1)
12. Mover el código vivo de la raíz a `src/` (`simulation_buffer.py` → `src/shared/buffer.py` *reusando* el nombre, `visualizer.py` → `src/tools/`, etc.) y unificar el estilo de import.
13. Hacer el proyecto instalable (`pip install -e .`) para eliminar los parches de `sys.path`.
14. Decidir el futuro de `web_dashboard/` (revivir y wirear, o archivar).

### Fase 4 — Refactor de monolitos (§6.1, opcional, mayor riesgo)
15. Unificar los 3 dashboards: decidir cuál es el canónico y deprecar los otros (resolver la doble `DashboardWorldClass`).
16. Partir `configurator.py` (4146) y `dashboard.py` (2536) en módulos.

### Fase 5 — Documentación (§7)
17. Reescribir `README.md`/`INSTRUCCIONES.md` a V12, regenerar `HANDOFF.md` (eliminar la duplicación), borrar o actualizar `.cursorrules`.
18. Crear `CLAUDE.md` y `STATUS.md` (borradores en §10–11).

---

## 10. Borrador propuesto de `CLAUDE.md` (NO creado — solo descrito)

Debería ser un documento **corto y operativo** (metodología + convenciones), no un changelog. Contenido sugerido:

- **Identidad del proyecto** (1 párrafo): qué es (simulador de almacén SimPy headless + replay), versión actual real (V12.x).
- **Cómo ejecutar**: los 4 entry points reales (generar replay, ver replay, optimizar, servidor web) con sus comandos exactos.
- **Mapa mental de la arquitectura**: el grafo de §2.3 condensado, señalando que el núcleo vivo es `src/subsystems/simulation/` + `src/engines/`.
- **Convenciones de código** (reglas que ya aparecen dispersas): solo ASCII en código; estilo de imports unificado (definir uno); idioma de comentarios.
- **Reglas de "no tocar"**: `config.json` es crítico; el flujo es headless→jsonl→replay (la live simulation fue eliminada, no reintroducir).
- **Gotchas conocidos**: el caos de `sys.path`, dónde vive realmente el buffer/visualizer, las rutas hardcodeadas.
- **Qué NO usar** (mientras no se limpie): `legacy/`, `src/shared/`, `web_dashboard/`, tests rotos.
- **Flujo de trabajo Git**: ramas feature, no commitear binarios (`warehouse.db`), `main` es la verdad.

> Sustituir las reglas obsoletas de `.cursorrules` (que mandan leer archivos inexistentes) por este `CLAUDE.md`.

## 11. Borrador propuesto de `STATUS.md` (NO creado — solo descrito)

Documento de **estado vivo**, que reemplaza al ausente `ACTIVE_SESSION_STATE.md`. Secciones:

- **Versión actual**: V12.1 (allocation layer en progreso, sin commitear a fecha de auditoría).
- **Qué funciona hoy** (verificado): generación headless, replay viewer, analytics Excel + heatmap, migración SQLite, servidor web (puerto 8000), optimizador Optuna.
- **En progreso**: Allocation Layer V12.1 (cumplimiento parcial por stock) — ver §8.
- **Trabajo pendiente / próxima acción**: (a definir por el usuario) p.ej. commitear V12.1, ejecutar Fase 0–1 de limpieza.
- **Deuda conocida priorizada**: tabla R1–R12 de §6.
- **Mapa de ramas**: tabla de §5 (qué borrar, qué revisar).
- **Riesgos abiertos**: rutas absolutas en `config.json`, deps web sin declarar.

---

## 12. Anexo — Tabla rápida de decisiones para el usuario

| Elemento | Recomendación | Certeza |
|---|---|---|
| Cambios working dir (V12.1) | **Commitear ya** en rama propia | SÉ |
| `legacy/`, `src/shared/`, `utils/` raíz | Borrar (Fase 1) | SÉ |
| `tools/configurator.py`, `tools/visualizer.py` | Borrar (duplicados muertos) | SÉ |
| `tests/` rotos | Borrar o reescribir | SÉ |
| 6 ramas con 0 commits propios | Borrar (nada se pierde) | SÉ |
| `feat/realtime-workorder-dashboard` | **Borrar** tras tag de respaldo: confirmado superada, no contiene el stack web ni la DB (ver §13.1) | SÉ |
| `fix/configurator-tool` | **Borrar** tras tag: aún más atrasada; el `configurator.py` raíz ya es la versión buena (ver §13.1) | SÉ |
| `web_dashboard/` | **Dejar documentada** y revisar más adelante si aún sirve o ya fue reemplazada (decisión del usuario; nadie recuerda su propósito) | INCIERTO |
| `analyze_events.py` | **Archivar** (el usuario no recuerda su uso; además usa esquema de eventos pre-Event-Sourcing, §13.3) | SOSPECHO |
| Datos duplicados (`layouts/`, `config.json`, `assets/`, `tilesets/`, themes) | **Raíz = fuente única**; `data/` solo lo usa código muerto/roto; `assets/` muerta; **unificar `Warehouse_Logic.xlsx`** (bug) — ver §13.8 | SÉ |
| `tools/inspect_tmx.py` ≡ `tools/inspector_tmx.py` | Borrar uno: son **byte-idénticos** (ver §13.4) | SÉ |
| `dashboard_modern.py`, `DashboardGUI`, `dashboard.py::DashboardWorldClass` | Importados pero nunca instanciados → poda (ver §13.2) | SOSPECHO |
| `layouts/` vs `data/layouts/` | Elegir fuente única, actualizar consumidores | Requiere decisión |
| `requirements.txt` / `setup.py` | Arreglar deps web y entry points | SÉ |
| `config.json` rutas absolutas | Volver relativas | SÉ |
| Docs (README/HANDOFF/INSTRUCCIONES/.cursorrules) | Actualizar a V12; HANDOFF está corrupto | SÉ |

---

## 13. Continuación — Resolución de los puntos marcados INCIERTO

> Esta sección se añadió en una sesión de continuación (tras corte por cuota). Cierra, con evidencia adicional de solo lectura, los puntos que en §1–§12 quedaron como INCIERTO o como veredictos tentativos. **Donde difiera, esta sección manda.**

### 13.1 Ramas con commits propios → confirmadas SUPERADAS (INCIERTO → **SÉ**)
Diff neto de **dos puntos** entre los *tips* actuales (no vs merge-base):
- `git diff --stat main feat/realtime-workorder-dashboard` → **143 archivos, +19.555 / −25.582**. Entre lo que "falta" en la rama aparecen `web_prototype/**` y `web_dashboard/**` completos y la capa de DB → **la rama es anterior a toda la plataforma web/SQLite**. Mergearla destruiría main.
- `git diff --stat main fix/configurator-tool` → **200 archivos, +13.326 / −47.453**; misma ausencia del stack web; además arrastra `run_simulator.py` (monolito ya borrado en main) y el archivo basura `git`.
- **Conclusión:** ninguna de las 9 ramas contiene trabajo no consolidado rescatable. `main` es, sin ambigüedad, la única rama buena. Las 8 restantes son backups/divergencias obsoletas → borrar tras un `git tag` de respaldo; **respecto a `main` no se pierde nada**.

### 13.2 Dashboards → identificado el vivo y los muertos (INCIERTO → **SÉ/SOSPECHO**)
Instanciaciones reales (`grep "Clase("` en todo `src/`, excluyendo los propios `dashboard*.py`):
- `replay_engine.py:167` → `DashboardWC(...)` = **`dashboard_world_class.py::DashboardWorldClass`** → dashboard de replay **VIVO**.
- `renderer.py:781` → `DashboardOriginal()` = **`dashboard.py::DashboardOriginal`** → **VIVO** (delegación de render).
- `ModernDashboard` (`dashboard_modern.py`, 547 líneas): importado en `replay_engine.py:55` pero **sin ninguna instanciación** → **SOSPECHO muerto**.
- `DashboardGUI` (`dashboard.py`): importado pero **sin instanciación** (`self.dashboard_gui = None`) → **SOSPECHO muerto**.
- `dashboard.py::DashboardWorldClass`: importado en `replay_engine.py:54` pero el instanciado es el de `dashboard_world_class.py` → **duplicado muerto** dentro de `dashboard.py`.

**Implicación:** `dashboard.py` (2536 líneas) está solo *parcialmente* vivo (únicamente `DashboardOriginal`). La Fase 4 de refactor tiene ahora objetivo claro: conservar `DashboardOriginal` (render) + `DashboardWorldClass` (replay) y podar `ModernDashboard`, `DashboardGUI` y el `DashboardWorldClass` duplicado. *(SOSPECHO: confirmar antes de borrar que no exista instanciación condicional por config.)*

### 13.3 `analyze_events.py` → SOSPECHO obsoleto (era INCIERTO)
Script standalone (147 líneas) que busca el `output/raw_events_*.json` más reciente y cuenta tipos con el campo `'tipo'` y nombres `'estado_agente'` / `'work_order_completed'` / `'task_completed'`: **esquema antiguo previo al Event Sourcing** (el actual usa `ipc_protocols.EventType`). No lo importa/referencia ningún script (grep = 0) y `raw_events_*.json` está gitignorado. → Utilidad de depuración manual desfasada; archivar o reescribir contra el esquema actual.

### 13.4 `tools/inspect_tmx.py` ≡ `tools/inspector_tmx.py` → duplicado exacto (INCIERTO → **SÉ**)
`diff` entre ambos = vacío (exit 0); 180 líneas cada uno, **byte-idénticos**. Uno es 100% redundante.

### 13.5 Ruta canónica de layouts → "split-brain" confirmado
- Flujo simulación/analytics resuelve a **`layouts/` (raíz)**: `exporter_v2.py:371` usa `config['layout_file']` con default `'layouts/WH1.tmx'`; la guía `docs/DYNAMIC_LAYOUTS_USER_GUIDE.md` también instruye `layouts/`.
- Flujo web apunta a **`data/layouts/layout_v2.tmx`** (`server.py:55`), archivo que **no existe**.
- `config.json` (working dir) no fija `layout_file` → cae al default raíz.
- **Conclusión:** `layouts/` (raíz) es la fuente efectiva del flujo principal; `data/layouts/` es la fuente (rota) del flujo web. Unificar y arreglar la ruta web rota.

### 13.6 Docs restantes → cierre de Fase E
- `docs/DYNAMIC_LAYOUTS_USER_GUIDE.md`, `docs/TILES_REFERENCE.md`: **VIGENTES** (guía y referencia del sistema TMX, activo vía `layout_manager` + `pytmx`).
- `DOCUMENTO_IMPLEMENTACION_DOBLE_BARRIDO.md`: **vigente como referencia técnica** (el doble barrido está en `dispatcher.py`), pero es un doc de implementación ya ejecutada (2025-10-27) → mover a `archived/`.
- `.cursor/rules/documentation_update.mdc`: **OBSOLETO y dañino** — `alwaysApply: true` obliga a leer `CURSOR_DOCUMENTATION_RULES.md` y `ACTIVE_SESSION_STATE.md`, **ambos inexistentes** → contamina toda sesión de IA. Actualizar/eliminar (apuntar al futuro `CLAUDE.md`).
- `data/layouts/INSTRUCCIONES_LAYOUTS.md`: **OBSOLETO** — describe un "problema actual / solución temporal" antiguo y archivos `layout_funcional.tmx` / `mi_layout_personalizado.tmx` que ya no existen.
- `data/layouts/INSTRUCCIONES_LAYOUT_PERSONALIZADO.md`, `TUTORIAL_EXPLICACION.md`: no releídos en esta continuación → siguen INCIERTOS (presumiblemente guías de usuario; baja prioridad).

### 13.8 Fuentes de datos duplicadas → veredicto por par y recomendación (resuelve §4.4)
El árbol `data/` fue un intento de migración (la "arquitectura profesional V11" que menciona `requirements.txt`) **iniciado y abandonado**: el código que corre hoy lee de la **raíz**, y `data/` solo lo consumen código muerto o roto.

| Par duplicado | Quién lo lee realmente (evidencia) | Veredicto |
|---|---|---|
| `config.json` (raíz) vs `data/config/config.json` | Entry points usan el de **raíz** por defecto; `.gitignore` lo protege | **Raíz canónico.** `data/config/` = copia muerta → borrar |
| `layouts/` (raíz) vs `data/layouts/` | `config.json` → `layout_file:"layouts/WH1.tmx"`, `sequence_file:"layouts/Warehouse_Logic.xlsx"`; `event_generator.py:108` resuelve a `project_root/layouts/` | **Raíz canónico** |
| `assets/` vs `data/assets/` (`agent_config.json`, `work_area_config.json`) | **Nadie.** La config de agentes vive dentro de `config.json` (`agent_types[]`); los `agent_config` de `warehouse.py`/`operators.py` son variables locales sobre ese array, no leen el archivo | **Ambas muertas** → borrar las dos |
| `tilesets/` (raíz) vs `data/tilesets/` | Los `.tmx` referencian su tileset internamente; siguen al layout | Seguir a `layouts/` (raíz) |
| `dashboard_theme.json` (raíz) vs `data/themes/` | `data/themes/dashboard_theme_modern.json` solo lo lee `ModernDashboard` (**muerto**, §13.2); consumidor del de raíz no localizado | Semi-muertas; verificar el tema del dashboard vivo antes de tocar |

**⚠️ Bug de correctitud (SÉ):** la simulación lee `layouts/Warehouse_Logic.xlsx` (raíz) pero **`run_migration.py:75` lee `data/layouts/Warehouse_Logic.xlsx`** (otra copia). Son dos Excel que pueden divergir → la base SQLite y la simulación podrían describir almacenes distintos. **Unificar es obligatorio**, gane raíz o `data/`.

**Recomendación (fundamentada):** hacer **la raíz la fuente única** y eliminar el árbol `data/` de datos activos. Motivos: (1) todo el código que corre ya resuelve a raíz; (2) `data/` solo lo tocan código muerto (`ModernDashboard`), roto (`server.py:55` → `data/layouts/layout_v2.tmx`, **inexistente**) o un único script (`run_migration.py`); (3) consolidar a raíz cambia 2-3 rutas, mientras que completar la migración a `data/` cambiaría config.json + event_generator + configurator + web (más riesgo, sin beneficio funcional). **Antes de borrar `data/`**, rescatar lo que solo existe ahí: las guías `.md` (→ `docs/`) y los Excel `Warehouse_Logic_WA.xlsx` / `Warehouse_Logic_Zonas.xlsx` (evaluar uso). *Alternativa válida:* si en el futuro quieres separación estricta código/datos, completar la migración a `data/` es la opción "de manual", pero como decisión deliberada, no como parte de esta limpieza de bajo riesgo.

### 13.9 Estado de cobertura tras la continuación
**Resueltos:** ramas (§13.1), dashboards (§13.2), `analyze_events.py` (§13.3), `inspect_tmx`/`inspector_tmx` (§13.4), ruta de layouts (§13.5), docs `docs/*` + `.cursor` + `DOBLE_BARRIDO` + `INSTRUCCIONES_LAYOUTS` (§13.6), **fuentes de datos duplicadas (§13.8)**.
**Siguen INCIERTOS por requerir decisión del usuario (no por falta de evidencia):** destino de `web_dashboard/` (dejar documentada y revisar luego, según tu indicación) y 2 guías de usuario de layouts de baja prioridad (`INSTRUCCIONES_LAYOUT_PERSONALIZADO.md`, `TUTORIAL_EXPLICACION.md`).

---

*Fin de la auditoría. No se modificó código ni estado de Git (solo lectura + actualización del propio informe). Próximo paso sugerido: revisar este informe y, si estás de acuerdo, autorizar la Fase 0 (asegurar el working dir y backups) en una sesión de escritura.*
