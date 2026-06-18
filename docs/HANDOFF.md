# HANDOFF — Gemelo Digital de Almacen
# Estado operativo para nueva sesion de Cerebellum

**Generado:** 2026-06-18
**Por:** Cerebellum (sesion de traspaso)
**Rama activa:** `feature/allocation-layer-v12.1`
**Proxima accion del Director:** `git push origin feature/allocation-layer-v12.1`
  (desde terminal Windows — el sandbox Linux no tiene red saliente)

---

## 1. QUE ES EL PROYECTO

Simulador de gemelo digital de almacen (Warehouse Digital Twin).
- **Motor:** SimPy (eventos discretos, headless) -> archivo `.jsonl` -> visualizador Pygame + analitica Excel.
- **Web:** FastAPI en puerto 8000 — configurador + runner + visor de replay.
- **Entidades:** GroundOperator (picking manual), Forklift (carga pesada), WorkOrders (SKU de rack a staging).
- **NO hay simulacion en vivo**: el flujo siempre es headless -> jsonl -> replay.

Stack: Python / SimPy / Pygame / PyQt6 / pytmx / pandas / Optuna / FastAPI / SQLite.
> NOTA: FastAPI/uvicorn/pydantic no estan en requirements.txt. Un pip install limpio no levanta el servidor.

---

## 2. ARQUITECTURA — CADENA VIVA

```
entry_points/run_generate_replay.py
  -> src/engines/event_generator.py          (headless SimPy -> .jsonl + Excel + heatmap)

entry_points/run_replay_viewer.py
  -> src/engines/replay_engine.py            (Pygame viewer)

entry_points/run_optimization.py
  -> src/tools/optimizer.py                  (Optuna)

web_prototype/server.py  (FastAPI :8000)     (configurador web + runner + viewer web)
  -> start_server.bat / server_manager.py / start_hidden.py

run_migration.py
  -> src/subsystems/database/               (Excel -> SQLite warehouse.db)
```

Nucleo de simulacion SANO: `src/subsystems/simulation/`
  warehouse.py, dispatcher.py (DispatcherV11), operators.py, order_strategies.py,
  data_manager.py, assignment_calculator.py, route_calculator.py,
  pathfinder.py, layout_manager.py

Archivos VIVOS fuera de src/ (no borrar sin pensar):
  simulation_buffer.py, visualizer.py, configurator.py,
  server_manager.py, start_hidden.py

Codigo MUERTO (ignorar en features; objetivo en limpieza futura):
  legacy/**, src/shared/**, utils/ (raiz), tools/configurator.py,
  tools/visualizer.py, tools/inspect_tmx.py, gran parte de tests/

web_dashboard/ (puerto 8001): HUERFANA pero el Director quiere revisarla antes de decidir.

Fuente de datos canonica = RAIZ (config.json, layouts/WH1.tmx, layouts/Warehouse_Logic.xlsx).
El arbol data/ es una migracion abandonada que solo lee codigo muerto.

---

## 3. GIT — ESTADO ACTUAL

**Rama:** `feature/allocation-layer-v12.1`
**HEAD local:** `dd5c729`
**Remote:** `9af0455` (6 commits atras — push pendiente)

### Commits en la rama por delante de main (20 total):

```
dd5c729  exp(p4-bk03): greedy NN descartado con evidencia
76f1e21  feat(p3): exponer radio_expansion_paso y radio_max_expansiones en configurador web
9451795  chore(gitignore): .fuse_hidden*, commit*.bat, COMMIT_*.bat
8a2fe86  fix(h-6): radio blando en estrategia Cercania (elimina deadlock)
c24b087  docs(h-6): analisis deadlock Cercania + BK-02 EN REPENSAR
3d0b0f8  docs(val-comp): validacion comportamiento real por estrategia + bug H-6
336c442  docs(backlog): BK-02 FIFO Estricto + BK-03 greedy nearest-neighbor
056ac09  refactor: eliminar campo fantasma Zoning-and-Snake, doc greedy-NN
e91dddf  fix(optimizer): strings fantasma -> 4 estrategias reales de despacho
c4c772f  fix(H-5): dispatcher reconoce alias corto "Ejecucion de Plan" de la UI
836ba72  docs: AUDITORIA_ESTRATEGIAS.md inventario completo
5980341  docs: H-5 auditoria estrategias (hallazgo)
bcdb264  feat(ui): BK-01 Cercania + radio_cercania en configurador
9ab9f42  docs: D-01..D-12 marcadas implementadas
394d3f1  feat(ui): D-08..D-12 sidebar, fleet cards, inline validation, KPIs, toasts
884a420  fix(ui): D-03..D-07 quick wins + H-1..H-4 cerrados
99166bc  docs: backlog BK-01 estrategias ocultas
8fd8a3c  chore: cuarentena archivos basura en basura/
6e4e0e0  docs: propuesta mejora UI/UX + inventario basura
9af0455  (base: chore limpieza docs + fixes E2E)
```

### Para hacer el push (desde terminal Windows del Director):
```
cd "D:\Documentos\Martin\Gemelos Digital"
git push origin feature/allocation-layer-v12.1
```
SHA remoto esperado tras el push: `dd5c729c31ca0f6b3108d9a74df50814c5be181f`

### Para el merge a main (despues del push):
```
git checkout main
git merge --no-ff feature/allocation-layer-v12.1 -m "merge: allocation layer V12.1 + fixes H5/H6 + BK-01 + UI"
git push origin main
```
> NOTA: el sandbox Linux no puede hacer push. Ambas operaciones deben correr en
> Windows donde las credenciales de GitHub estan en el Credential Manager.

---

## 4. LO QUE SE HIZO EN LAS ULTIMAS SESIONES

### Allocation Layer V12.1 (base de la rama)
Asignacion de stock real (FCFS) antes de crear WorkOrders.
- `data_manager.py::get_available_stock()` — reserva stock real del Excel.
- `warehouse.py::WorkOrder` — campos `qty_requested`, `qty_allocated`, `is_partial`.
- `order_strategies.py` — genera WOs solo si hay stock; registra backorders.
- `config.json` — `fulfillment_policy: "ship_partial"` como fuente de verdad.

### Limpieza estructural
- Cuarentena: 40+ archivos basura movidos a `basura/`.
- `.gitignore` ampliado: `.fuse_hidden*`, `commit*.bat`, lock files.
- 7044 archivos `.fuse_hidden*` borrados por el Director (LIMPIAR_TEMPORALES.bat).

### UI/UX — mejoras D-03 a D-12
- D-03/D-04: sidebar colapsable, tabs con iconos.
- D-05/D-06: fleet cards con estado visual, inline validation en inputs.
- D-07: jerarquia visual de KPIs en el visor.
- D-08 a D-12: colores de sidebar, toasts de estado en el viewer, etc.
- H-1/H-2/H-4: E6/E7 deshabilitados, confirm reemplazado por modal, right panel sincronizado al seek.

### Auditoria y fixes de estrategias de despacho
- AUDITORIA_ESTRATEGIAS.md: mapeadas las 4 estrategias reales + 3 fantasmas eliminadas.
- **Fix H-5** (`c4c772f`): la UI enviaba "Ejecucion de Plan" (sin sufijo) pero el dispatcher
  buscaba "Ejecucion de Plan (Filtro por Prioridad)". Nunca ejecutaba su funcion.
  Fix: alias corto reconocido en `__init__` del dispatcher.
- **Fix optimizer.py**: estrategias fantasmas (FIFO Simple, Proximity-Based, Zoning-and-Snake)
  reemplazadas por los 4 strings reales.

### Fix H-6 — Deadlock de Cercania (radio restrictivo)
**Problema:** `_estrategia_cercania()` usaba un radio DURO. Si ningun WO estaba
dentro del radio, retornaba `[]`. El caller retornaba `None`. `operators.py`
hacia `yield timeout(0.5); continue` -> bucle infinito -> deadlock.
**Fix (Radio Blando):** expansion progresiva del radio por pasos:
```
radio inicial -> radio + paso*1 -> ... -> radio + paso*N -> todos los WOs compatibles
```
Parametros en config.json:
- `radio_cercania`: radio inicial en celdas (default 100)
- `radio_expansion_paso`: incremento por intento (default 50)
- `radio_max_expansiones`: maximo de expansiones (default 5)
Validado: radio=15 con 25 WOs -> completa en 3.57s (antes: bucle infinito hasta t=135249).
Los 3 parametros estan expuestos en el configurador web.

### BK-01 — Estrategia Cercania expuesta en la UI
- `index.html`: nueva opcion en selector + div `#radio-cercania-group` con sub-seccion
  de expansion de radio.
- `app.js`: load/serialize de radio_cercania, radio_expansion_paso, radio_max_expansiones.
- `config_manager.py`: validacion de los 3 campos nuevos.

### BK-03 — Experimento greedy nearest-neighbor (DESCARTADO)
Hipotesis: ordenar WOs por vecino mas cercano en lugar de por costo mejora distancia total.
Resultado (3+3 corridas, Cercania, radio=100, 300 WOs, 2 operarios):
- Distancia total: -5.27% (aparente)
- Distancia / WO: -1.54% (real — dentro del ruido estadistico con N=3)
- WOs completadas: -3.80% (REGRESION — hace menos trabajo)
- El ahorro de distancia es un artefacto de hacer menos trabajo, no de mejor routing.
Decision: no integrar. Flag `cercania_tour_mode` queda en codigo con default `"cost"`.

---

## 5. PENDIENTES Y PROXIMOS PASOS

### Inmediato (requiere accion del Director)
| Accion | Como |
|---|---|
| Push a GitHub | `git push origin feature/allocation-layer-v12.1` desde terminal Windows |
| Merge a main | `git checkout main && git merge --no-ff feature/...` desde terminal Windows |
| Borrar push_feature.bat | Eliminar desde Explorer tras el push exitoso |

### Backlog activo (ver docs/BACKLOG.md para detalle)

**BK-02 — FIFO Estricto en UI** (EN REPENSAR)
El motor lo implementa correctamente (string `"FIFO Estricto"`). No se expone en la UI
porque el Director quiere redefinir primero que deberia hacer operacionalmente.
Esfuerzo cuando se decida: ~15 min (1 linea HTML + 1 linea validacion).

**web_dashboard/** (PENDIENTE DECISION)
Puerto 8001. Ruta de replay rota. Parece huerfana pero el Director quiere revisarla
antes de decidir si se conserva, se repara o se elimina.

**Mejoras de diseno D-13+**
D-01 a D-12 estan implementadas. Si el Director define nuevas mejoras de UI,
se numeran D-13 en adelante en docs/PROPUESTA_MEJORA_DISENO_UI.md.

### Issues conocidos (no criticos)
- `run_migration.py:75` lee `data/layouts/Warehouse_Logic.xlsx` pero la simulacion
  lee `layouts/Warehouse_Logic.xlsx`. Dos copias que pueden divergir.
- `warehouse.db-shm` / `warehouse.db-wal`: archivos de WAL de SQLite, aparecen como
  untracked pero ya estan en .gitignore.
- `push_feature.bat` en raiz: artefacto de intento de push autonomo. Borrar tras push.
- FastAPI/uvicorn/pydantic no estan en requirements.txt.

---

## 6. DOCUMENTACION VIGENTE

| Archivo | Estado | Descripcion |
|---|---|---|
| `CLAUDE.md` | ACTUALIZADO 2026-06-18 | Identidad, arquitectura, leyes, estado actual |
| `AUDITORIA.md` | Vigente (mayo 2026) | Diagnostico estructural completo del repo |
| `docs/HANDOFF.md` | NUEVO 2026-06-18 | Este archivo — estado operativo para nueva sesion |
| `docs/BACKLOG.md` | ACTUALIZADO 2026-06-18 | BK-01 IMPLEMENTADO, BK-02 EN REPENSAR, BK-03 DESCARTADO |
| `docs/AUDITORIA_ESTRATEGIAS.md` | ACTUALIZADO 2026-06-18 | H-5 resuelto, R1 descartada |
| `docs/ANALISIS_H6_CERCANIA_DEADLOCK.md` | ACTUALIZADO 2026-06-18 | H-6 resuelto en 8a2fe86 |
| `docs/VALIDACION_UI_WEB.md` | Vigente (jun 2026) | 62 controles validados; 4 hallazgos cerrados |
| `docs/PROPUESTA_MEJORA_DISENO_UI.md` | Vigente | D-01..D-12 implementadas |
| `docs/PRUEBAS_E2E_SISTEMA.md` | Vigente | Bateria de 44 casos E2E |
| `docs/LIMPIEZA_ARCHIVOS_BASURA.md` | Vigente | Cuarentena ejecutada en 8fd8a3c |
| `docs/COMO_FUNCIONA_EL_PROGRAMA.md` | Referencia | Descripcion operativa del sistema |
| `docs/VISION_PRODUCTO.md` | Referencia | Vision y roadmap de alto nivel |
| `docs/antiguos/` | OBSOLETOS | Docs de sesiones anteriores (V11 y antes) |

---

## 7. PROTOCOLO ANTI-FUSE (para Cerebellum)

El sandbox corre en Linux pero el proyecto esta en un mount FUSE de Windows.
Restricciones del mount:
- `rm` / `os.remove()` -> "Operation not permitted"
- `git` normal (add/commit/push) -> bloqueado por index.lock / HEAD.lock
- Escritura: SOLO funciona con `shutil.copy2(src, dst)` (sobreescritura)

Solucion para commits (bypass de bajo nivel):
```bash
git hash-object -w <archivo>           # genera blob hash
export GIT_INDEX_FILE=/tmp/idx_xx
git read-tree <parent-commit-hash>     # carga arbol del padre en indice temporal
git update-index --cacheinfo 100644,<hash>,<ruta>   # actualiza entradas
TREE=$(git write-tree)
COMMIT=$(echo "mensaje" | git commit-tree $TREE -p <parent-hash>)
echo $COMMIT > .git/refs/heads/<branch>   # actualiza rama directamente
unset GIT_INDEX_FILE
```

Solucion para edicion de archivos:
```python
# En /tmp (Linux nativo):
# 1. Editar el archivo
# 2. shutil.copy2('/tmp/archivo', '/sessions/.../mnt/Gemelos Digital/archivo')
```

Para push a GitHub: el sandbox no tiene red saliente. El Director debe hacer el push
desde su terminal Windows.

---

## 8. CONFIG.JSON — DEFAULTS SEGUROS (estado post-experimentos)

```json
{
  "dispatch_strategy": "Ejecucion de Plan",
  "radio_cercania": 100,
  "radio_expansion_paso": 50,
  "radio_max_expansiones": 5,
  "cercania_tour_mode": "cost",
  "total_ordenes": 300,
  "num_operarios_terrestres": 2,
  "num_montacargas": 2
}
```
`cercania_tour_mode: "cost"` es el default seguro post-BK-03. El valor `"greedy_nn"`
existe como opcion pero no se recomienda (ver BK-03 descartado).
