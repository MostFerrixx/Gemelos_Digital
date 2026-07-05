# Gemelo Digital de Almacen

**Version:** V12.1 (Allocation Layer + INIT-1/3/4 + MEJ-1/2/3/4)
**Estado:** En desarrollo activo - todo en `main`, ver `docs/STATE.md` para
el detalle operativo vigente (rama, baseline, decisiones pendientes)
**Arquitectura:** Headless (SimPy) + Replay + GUI web
**Actualizado:** 2026-07-05

---

## 1. Que es

Simulador de operaciones logisticas de almacen (Warehouse Digital Twin). Reproduce
el flujo de mercancias y agentes sobre un mapa fisico real (layouts TMX de Tiled)
para detectar cuellos de botella y subir el throughput.

La mecanica es una **simulacion de eventos discretos con SimPy**: el tiempo avanza
por eventos, no por frames. El motor corre headless y persiste todo lo ocurrido en
un archivo de eventos `.jsonl`, que luego se visualiza y analiza por separado.

Entidades principales:

- **Operarios**: `GroundOperator` (picking manual) y `Forklift` (carga pesada),
  con velocidad, capacidad y prioridades de zona.
- **WorkOrders**: mover un SKU de un rack a una zona de staging, con volumen,
  prioridad y secuencia.
- **Layout**: mapas TMX (Tiled) que definen racks, pasillos y zonas.

---

## 2. Allocation Layer V12.1

La novedad de esta version es una **capa de asignacion de stock real (FCFS,
first-come-first-served)** que se ejecuta **antes** de crear las WorkOrders. En
lugar de asumir stock infinito, el sistema reserva el stock disponible por orden
de llegada y refleja faltantes.

- `fulfillment_policy: "ship_partial"` permite cumplir parcialmente una orden
  cuando no hay stock suficiente.
- Cada WorkOrder distingue **cantidad solicitada vs cantidad asignada/recogida**
  (`qty_requested` / `qty_allocated`, concepto **QTY REQ vs QTY PICK**). El
  remanente no servido es un **backorder** (deuda) que se puede reportar.

Por que importa: sin esta capa la simulacion sobreestima el throughput porque
nunca se queda sin stock. La Allocation Layer hace que los resultados reflejen la
realidad del inventario.

Toca principalmente `data_manager.py` (`get_available_stock`), `warehouse.py`
(campos de la WorkOrder), `order_strategies.py` y `config.json`.

---

## 2.1 Capacidades adicionales del motor (opt-in)

Sobre la base V12.1 se anadieron features **opt-in con defaults neutros**: si no
se activan, el motor se comporta como antes (corrida con `WAREHOUSE_SEED=42`
byte-identica al baseline). Se activan desde `config.json`.

- **Tiempos de pick realistas** (INIT-4 C1): el tiempo de recogida puede escalar
  con la cantidad/volumen de la WorkOrder en vez de ser fijo
  (`tiempos.pick_time_model`).
- **Prioridad de pedido / SLA** (INIT-4 C2): los pedidos pueden traer `priority` y
  `due_time`; con `priority_dispatch_enabled` los urgentes se sirven primero
  (Opcion C "fuerte limpia": el tour se arma solo con urgentes, sin diluir, sin
  cruzar de zona).
- **Olas de picking** (INIT-4 C3): agrupar pedidos por `wave` y liberarlos por
  horario (`waves.release_times`); una WO no es elegible hasta su release.
- **Nivel de servicio / backorders** (INIT-5): fill-rate y demanda no cubierta en
  el visor web, la API y una hoja Excel.
- **Reproducibilidad** (`WAREHOUSE_SEED`): semilla determinista via variable de
  entorno para corridas comparables.

Detalle e implementacion: `docs/antiguos/PLAN_INIT4.md` y la seccion "Flags opt-in" de
`CLAUDE.md` / `docs/STATE.md`.

---

## 2.2 Calidad y realismo (MEJ-1 / MEJ-3 / MEJ-4, 2026-07-04)

- **Red de seguridad automatizada (MEJ-1):** suite pytest (~73 tests, <10 s) +
  gate de regresion byte-identico en un comando (~15 s) + CI en GitHub Actions.
  Ver seccion "Tests y gate de regresion" abajo.
- **Esquema unico de configuracion (MEJ-3):** `src/core/config_schema.py` es la
  fuente de verdad de TODAS las claves de `config.json` (cada una anotada con su
  lector real). Typos y claves legacy se detectan y avisan; tipos invalidos
  bloquean el guardado desde la web. Se purgaron ~19 claves muertas y dos
  controles de UI sin efecto.
- **Anti-colisiones completado (MEJ-4):** la permanencia de los operarios
  (picking, descarga, lifting) se reserva en la tabla espacio-temporal AL
  PLANIFICAR (destino-con-permanencia); el planner usa busqueda estilo SIPP
  (salto al primer hueco libre + dominancia por intervalo seguro); fallback
  visible y margen `clearance`. Resultado: sin amontonamientos fisicos (max 2
  agentes/celda en relevos instantaneos, antes 4 superpuestos descargando) y
  **colas reales visibles en el staging**. NOTA: el makespan canonico subio
  ~55% porque la cola del staging unico ahora se modela de verdad (antes el
  throughput estaba inflado por descargas fisicamente imposibles). Detalle:
  `docs/antiguos/PLAN_MEJORA_4_ANTICOLISIONES.md`.

---

## 3. Arquitectura

Flujo central headless -> replay -> analitica:

```
+----------------------------------+
|  Motor headless (event_generator)|
|  - SimPy puro                    |
|  - Allocation Layer (FCFS)       |
|  - Captura de eventos            |
+----------------+-----------------+
                 |
                 v
+----------------------------------+
|  Archivos de salida              |
|  - replay_*.jsonl  (eventos)     |
|  - *.xlsx          (reportes)    |
|  - *_heatmap_*.png (mapa calor)  |
+----------------+-----------------+
                 |
                 v
+----------------------------------+
|  GUI web (web_prototype, :8000)  |
|  - Configura la simulacion       |
|  - Lanza el runner               |
|  - Visualiza el replay           |
+----------------------------------+
```

La **simulacion en vivo (live) fue eliminada a proposito**; la separacion
headless -> jsonl -> viewer es intencional y no debe reintroducirse.

### Frontend unico: la GUI web

La GUI vigente es la **web** (`web_prototype/`, FastAPI en
`http://localhost:8000`). Es el unico frontend de visualizacion y configuracion.

Las **3 GUI de escritorio** anteriores fueron **deprecadas y archivadas** en
`_legacy/gui_escritorio/` (movidas con `git mv`, reversibles, nada se borro):

- Visualizador de replay en **Pygame** (`run_replay_viewer.py` + `replay_engine`).
- Dashboard de WorkOrders en **PyQt6** (IPC).
- Configurador de escritorio en **Tkinter** (`configurator.py`).

Nota: `pygame-ce` sigue siendo dependencia del **headless** porque
`layout_manager.py` lo usa para leer el TMX; no es por las GUI deprecadas.

---

## 4. Instalacion

Requiere **Python >= 3.9**.

```bash
pip install -r requirements.txt
```

Dependencias principales: `simpy` (motor), `pygame-ce` (lectura de layout en el
headless), `pytmx` (mapas Tiled), `pandas` + `openpyxl` (reportes Excel),
`optuna` (optimizacion) y `fastapi` + `uvicorn` + `pydantic` (servidor web).

---

## 5. Uso / Comandos

Hay atajos en `Makefile` (Linux/macOS o `make` en Windows) y `run.bat` (Windows).

### Simulacion headless (genera replay + reportes)

```bash
make sim
# equivale a:
python entry_points/run_generate_replay.py

# opciones:
python entry_points/run_generate_replay.py --config config_test.json
python entry_points/run_generate_replay.py --output-metrics temp_metrics/output.json
```

En Windows: `run sim` (o `.\run sim` en PowerShell).

### GUI web (configurador + runner + viewer)

```bash
make web
# equivale a:
python server_manager.py start --browser
```

En Windows tambien: `run web`, o los `.bat` directos
`start_server.bat` / `stop_server.bat` / `restart_server.bat` / `status_server.bat`.
URL: `http://localhost:8000`.

### Optimizacion (Optuna)

```bash
python entry_points/run_optimization.py
```

### Tests y gate de regresion (MEJ-1)

```bash
make test    # suite pytest de red de seguridad (~59 tests, <10 s)
make gate    # gate byte-identico: corre la sim canonica con seed 42 y
             # compara SHA256 contra tests/baseline.json (~30 s)
```

En Windows: `run test` / `run gate`. La CI (`.github/workflows/tests.yml`)
ejecuta ambos en cada push. Correr SIEMPRE tras tocar el motor; si un cambio
de comportamiento es intencional: `python scripts/regression_gate.py
--update-baseline --yes` y commitear el baseline junto con el cambio.

---

## 6. Estructura de directorios

```
Gemelos Digital/
├── entry_points/
│   ├── run_generate_replay.py    # Motor headless -> .jsonl + reportes
│   └── run_optimization.py       # Optimizacion de parametros (Optuna)
│
├── src/
│   ├── engines/
│   │   ├── event_generator.py    # Motor headless de eventos (SimPy)
│   │   └── analytics_engine.py   # Analitica de la simulacion
│   ├── subsystems/
│   │   ├── simulation/           # Nucleo: warehouse, dispatcher, operators,
│   │   │                         #   order_strategies, data_manager,
│   │   │                         #   pathfinder, route_calculator, layout_manager,
│   │   │                         #   congestion_manager, reservation_table,
│   │   │                         #   spacetime_planner (capa de congestion, activa)
│   │   ├── database/             # Migracion Excel -> SQLite (warehouse.db)
│   │   └── utils/                # Utilidades compartidas
│   ├── core/                     # config_manager, replay_utils, config_utils
│   ├── analytics/                # Exportacion de reportes (exporter, exporter_v2)
│   └── tools/                    # optimizer (Optuna)
│
├── web_prototype/                # GUI web vigente (FastAPI, :8000)
│   ├── server.py                 # App FastAPI (configurador + runner + viewer)
│   ├── config_manager.py
│   ├── simulation_runner.py
│   └── static/                   # Frontend (web_configurator/, viewer, css/js)
│
├── layouts/                      # Datos canonicos: WH1.tmx, Warehouse_Logic.xlsx, ...
├── output/                       # Resultados: simulation_YYYYMMDD_HHMMSS/
├── config.json                   # Configuracion canonica del backend
│
├── simulation_buffer.py          # Buffer de eventos (lo usa event_generator) - VIVO
├── visualizer.py                 # Genera el heatmap PNG por subprocess - VIVO
├── server_manager.py             # Gestor del servidor web - VIVO
│
└── _legacy/                      # Codigo obsoleto archivado (git mv, reversible)
    ├── gui_escritorio/           # Las 3 GUI de escritorio deprecadas (Pygame,
    │                             #   PyQt6, Tkinter) + visualization/ + communication/
    ├── legacy/                   # Carpeta *_OLD historica (0 imports vivos)
    ├── src_shared/               # src/shared/ muerto (superado por simulation_buffer.py)
    ├── utils_root/               # utils/ de la raiz (isla muerta)
    ├── tools_duplicados/         # Duplicados de configurator/visualizer/inspector
    ├── communication_raiz/       # communication/ huerfano de la raiz (roto)
    └── data/                     # Arbol data/ duplicado, migracion abandonada
```

Regla de oro: si trabajas en el simulador, **ignora `_legacy/`**. Nada de ahi
esta en las cadenas vivas (generar replay, optimizar, servidor web). Ver
`_legacy/README.md` para el detalle de cada movimiento y como revertirlo.

---

## 7. Configuracion y datos

`config.json` (en la **raiz**) es la **unica fuente de verdad** del backend: la
web/UI solo lo edita y el motor solo lo lee. No se duplica configuracion en codigo.

Parametros tipicos: `total_ordenes`, `agent_types` (operarios y montacargas con
capacidad y prioridades de zona), `dispatch_strategy`, `tour_type`,
`fulfillment_policy`, `layout_file`, `sequence_file`.

Flags **opt-in** (ausentes del `config.json` canonico a proposito; el motor los lee
con defaults neutros): `tiempos.pick_time_model`, `priority_dispatch_enabled`,
`waves` (ver seccion 2.1). La variable de entorno `WAREHOUSE_SEED` fija la semilla.

A diferencia de esos flags, el bloque **`congestion`** (evasion de colisiones /
ruteo por reserva espacio-temporal, Iniciativa 2 + MEJ-4) SI esta presente y
**activo** en el config canonico (`enabled: true`, `mode: "timewindow"`,
`shadow: false`, `clearance: 0.05`). Es parte del comportamiento de referencia
del motor. Toda clave nueva de config debe registrarse en
`src/core/config_schema.py` (MEJ-3).

Los **datos canonicos viven en la raiz**:

- `layouts/WH1.tmx` - layout activo (mapa Tiled).
- `layouts/Warehouse_Logic.xlsx` - logica/secuencia de racks y zonas.
- `config.json` - configuracion de la simulacion.

> **Nota (sin divergencia):** existe un arbol `data/` con copias duplicadas, pero
> tanto la simulacion como `run_migration.py` leen de `layouts/` (la raiz). El
> migrador usa `find_excel_file()` (busca `layouts/Warehouse_Logic_v2.xlsx` y luego
> `layouts/Warehouse_Logic.xlsx`); no existe copia en `data/layouts/`. El arbol
> `data/` es una migracion abandonada que solo lee codigo muerto/roto.

---

## 8. Salidas del sistema

Cada simulacion crea una carpeta `output/simulation_YYYYMMDD_HHMMSS/` con:

- `replay_*.jsonl` - eventos para el viewer web.
- `simulation_report_*.xlsx` - reporte ejecutivo con KPIs.
- `warehouse_heatmap_*.png` - mapa de calor de actividad.
- JSON de analytics y metadatos de la corrida.

---

## 9. Documentacion y repositorio

- `CLAUDE.md` - manual operativo del proyecto (arquitectura real, flags, leyes).
- `docs/STATE.md` - foto del presente (rama, baseline, pendientes); se reescribe cada sesion.
- `docs/CHANGELOG.md` - historial de iniciativas cerradas (append-only).
- `docs/BACKLOG.md` - solo lo pendiente/abierto.
- `docs/META_DOCUMENTACION.md` - por que la documentacion esta organizada asi.
- `AUDITORIA.md` - diagnostico estructural completo (mayo 2026, no se actualiza).
- `_legacy/README.md` - que se archivo, por que y como revertirlo.
- `docs/antiguos/` - archivo frio unico: planes ya ejecutados, docs de
  referencia puntual, analisis historicos (incluye el ex `archived/` de raiz).

> `CLAUDE.md`, este `README.md` y `docs/STATE.md` se mantienen al dia y son la
> referencia vigente. Los documentos en `docs/antiguos/` son historicos.

Repositorio: https://github.com/MostFerrixx/Gemelos_Digital

---

## 10. Licencia

Proyecto de uso interno y academico.
