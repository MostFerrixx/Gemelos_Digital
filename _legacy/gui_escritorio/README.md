# `_legacy/gui_escritorio/` — GUI de escritorio deprecadas

> **Decisión del Director (2026-05-31):** la **GUI web** (`web_prototype/`, FastAPI en
> http://localhost:8000) es la **evolución** de las tres interfaces de escritorio
> (visualizador Pygame, dashboard PyQt6 y configurador Tkinter). Se concentra el
> desarrollo en la web y se **deprecan** las de escritorio.
>
> **Nada se borró:** todo se movió con `git mv` (historial preservado) y es **reversible**.
> Base: mapa de dependencias por imports reales + prueba en vivo (importar el motor
> headless `event_generator` carga **0** módulos de aquí).

## Regla de oro
Si trabajas en el simulador headless, los reportes o la web, **ignora esta carpeta**.
Antes de mover cada cosa se verificó que **ningún módulo vivo la importa** (ni el headless,
ni los reportes Excel, ni `web_prototype/`).

## Qué se movió y por qué

| Origen | Aquí en | Qué es / por qué es solo-escritorio |
|---|---|---|
| `entry_points/run_replay_viewer.py` | `gui_escritorio/run_replay_viewer.py` | Lanzador del visualizador Pygame; solo invoca `replay_engine`. |
| `src/engines/replay_engine.py` | `gui_escritorio/replay_engine.py` | Motor del visualizador Pygame. **Único** importador de `visualization/`, `communication/` y `config/`. |
| `src/subsystems/visualization/` | `gui_escritorio/visualization/` | Render Pygame + dashboards (`dashboard`, `dashboard_world_class`, `dashboard_modern`, `renderer`, `state`, `replay_scrubber`) y el **dashboard PyQt6** (`work_order_dashboard`). Importado solo por `replay_engine` y `dashboard_communicator`. |
| `src/communication/` | `gui_escritorio/communication/` | IPC PyQt6 (`dashboard_communicator`, `lifecycle_manager`, `ipc_protocols`). Importado solo por `replay_engine`. El headless **no** usa `ipc_protocols` (escribe el `.jsonl` vía `simulation_buffer`/`replay_utils`). |
| `src/subsystems/config/` | `gui_escritorio/config_pygame/` | Constantes de **resolución/colores del viewer Pygame** (`settings.py`, `colors.py`). **OJO:** NO es el sistema de `config.json` (ése es `core/config_manager` + `web_prototype/config_manager`). Renombrado a `config_pygame/` para evitar confusión. Importado solo por `replay_engine`. |
| `configurator.py` (raíz, Tkinter) | `gui_escritorio/configurator.py` | Configurador de escritorio Tkinter (4146 líneas), standalone. **0** importadores. Su equivalente vivo es el configurador **web**. |

## Qué se quedó VIVO (NO está aquí, no confundir)
- **`visualizer.py` (raíz)** — genera el heatmap PNG de los **reportes Excel** por subprocess. No es GUI de escritorio.
- **`src/subsystems/simulation/layout_manager.py`** — compartido por el headless y (antes) el viewer; importa `pygame`. Por eso **`pygame-ce` sigue siendo dependencia** del headless aunque se deprecaron las GUI.
- Todo `simulation/`, `core/`, `analytics/`, `simulation_buffer.py`, los entry points `run_generate_replay.py` y `run_optimization.py`, y **`web_prototype/`** completo.

## Cambios asociados (en el repo vivo)
- `Makefile` y `run.bat`: se quitaron los comandos `replay` y `config`; quedan `sim` (headless) y `web`.
- `setup.py`: se eliminaron los `console_scripts` rotos / de escritorio.
- `requirements.txt`: se quitaron `PyQt6` y `pygame_gui` (solo-GUI); se mantiene `pygame-ce` (headless).
- `docs/PRUEBAS_GUI.md`: reescrito para documentar las pruebas de la **GUI web**.

## Cómo revertir
`git revert <hash>` del commit de archivado, o `git mv` inverso de cada ruta. Nada se perdió.
