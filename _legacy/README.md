# `_legacy/` — Archivo de código obsoleto

> **Propósito:** separar físicamente el código **muerto/obsoleto** del código **activo**, para
> que en futuras sesiones de trabajo no se modifique por error un archivo que ya no sirve.
> **Nada aquí se borró:** todo se movió con `git mv` (historial preservado) y es **reversible**.
> **Fecha:** 2026-05-31 · **Rama:** `feature/allocation-layer-v12.1`
> Base del análisis: `AUDITORIA.md` + verificación de imports reales (grep de la cadena de dependencias).

## Regla de oro
Si trabajas en el código del simulador, **ignora esta carpeta**. Todo lo de aquí está
fuera de las 4 cadenas de ejecución vivas (generar replay, ver replay, optimizar, servidor web).
Antes de mover cada elemento se verificó que **ningún archivo activo lo importa o referencia**.

## Qué se movió y por qué

| Elemento (origen) | Aquí en | Motivo (evidencia) |
|---|---|---|
| `legacy/` | `_legacy/legacy/` | Carpeta `*_OLD` por diseño. 0 imports activos (la única mención de "legacy" en el código vivo es un comentario en `operators.py`). Sus archivos importan módulos ya borrados (`engines.simulation_engine`). |
| `src/shared/` (`buffer.py`, `diagnostic_tools.py`, `__init__.py`) | `_legacy/src_shared/` | 0 imports de entrada. Superado por `simulation_buffer.py` (raíz), que es el buffer que realmente importa `event_generator.py:32`. |
| `utils/` (raíz) | `_legacy/utils_root/` | Isla muerta: solo se auto-importa; ningún módulo externo importa el paquete `utils`. |
| `tools/configurator.py` | `_legacy/tools_duplicados/` | Duplicado muerto del `configurator.py` de la raíz (el vivo, 4146 líneas, lanzado por `Makefile`/`run.bat`). |
| `tools/visualizer.py` | `_legacy/tools_duplicados/` | **Byte-idéntico** al `visualizer.py` de la raíz (el vivo, invocado por subprocess desde `exporter_v2.py:370`). |
| `tools/inspector_tmx.py` | `_legacy/tools_duplicados/` | **Byte-idéntico** a `tools/inspect_tmx.py` (se conserva ese como canónico). |
| `web_dashboard/` | `_legacy/web_dashboard/` | App web huérfana (puerto 8001): 0 imports, ningún `.bat` la arranca, ruta de replay hardcodeada y obsoleta. **Mini-app completa y revivible** si algún día se quiere recuperar. |
| `analyze_events.py` | `_legacy/analyze_events.py` | 0 referencias; usa el esquema de eventos **anterior** al Event Sourcing (campo `'tipo'`), ya no compatible con `ipc_protocols.EventType`. |
| `config_optimized_20251128_154628.json`, `config_optimized_20251128_182004.json` | `_legacy/` | Salidas del optimizador Optuna commiteadas por error (deberían ir a `optimized_configs/`, que está en `.gitignore`). |
| `files_to_delete.txt`, `generate_files_to_delete_list.py` | `_legacy/` | Restos de una herramienta de limpieza de una sesión pasada. |
| 7 tests rotos (`tests/integration/` y `tests/manual/`) | `_legacy/tests_rotos/` | Importan módulos borrados (`simulation_engine`, `simulation_data_provider`, `replay_data_provider`, `ReplayEngineDataProvider`). No ejecutan. Se mantienen en `tests/` los que sí resuelven imports. |
| `tests/` completo (bugfixes, integration, manual, unit) | `_legacy/tests_gui/` | **MEJ-1, 2026-07-04:** todo el `tests/` restante era legacy de las GUI archivadas (dashboard PyQt6, viewer Pygame, tecla "O") o de configs antiguas; no compilaba contra la cadena viva. Reemplazado por la suite pytest nueva en `tests/` (ver `docs/antiguos/PLAN_MEJORA_1_RED_SEGURIDAD.md`). |

## Qué NO se movió (y por qué)
- **`simulation_buffer.py` y `visualizer.py` (raíz):** parecen "sueltos" pero están **vivos** (los usa `event_generator` y `exporter_v2` por subprocess). Se quedan.
- **Duplicación de datos `data/` vs raíz** (`layouts/`, `assets/`, `config`, `tilesets/`): **pendiente**, no se tocó aquí. Hay un *bug de correctitud* (la simulación y `run_migration.py` leen `Warehouse_Logic.xlsx` de ubicaciones distintas) que merece una decisión y sesión dedicada, no un simple movimiento.
- **`src/subsystems/visualization/dashboard_modern.py` y clases duplicadas:** importadas pero (sospecha) nunca instanciadas; podarlas requiere confirmar que no haya instanciación condicional por config. Refactor, no archivo.

## Cómo revertir
Cada movimiento es un `git mv` inverso. Para deshacer todo: `git revert <hash-del-commit-de-reorganización>` o `git mv` manual de vuelta. Nada se perdió.
