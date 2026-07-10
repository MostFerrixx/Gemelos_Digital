# PLAN INIT-7 — INBOUND (recepcion y almacenamiento)

> Aprobado por el Director el 2026-07-08 (las 4 decisiones, ver abajo).
> Este documento es el plan de referencia de la iniciativa completa; el estado
> de avance por fase vive en `docs/BACKLOG.md` / `docs/CHANGELOG.md`.

## Objetivo

Agregar al simulador el flujo de ENTRADA de mercaderia: camiones que llegan a
muelles de recepcion -> descarga -> tareas de putaway (guardar en ubicaciones
del almacen) -> stock disponible. El valor de producto es comparar ESTRATEGIAS
DE SLOTTING (donde guardar cada SKU que llega) con el experiment runner A/B,
igual que hoy se comparan estrategias de despacho.

## Decisiones del Director (2026-07-08)

1. **Alcance v1 = F0-F4** (inbound funcionando solo); flujo mixto F5 en una
   segunda etapa.
2. **Muelles:** 2-3 en la fila superior del mapa, definidos por hoja Excel
   (espejo de `OutboundStaging`), SIN editar el TMX.
3. **Llegadas:** ambos modos, espejo de `order_generation_mode`: archivo
   determinista (ASN) + estocastico (intervalo y mezcla de SKUs).
4. **F5 (stock del dia disponible para picking del mismo dia vs turnos
   separados):** se decide al arrancar F5; no bloquea v1.

## Hallazgos de la investigacion (2026-07-08) — por que es barato

- `schema.sql` ya contempla inbound: `locations.location_type` acepta
  `'STAGING_IN'`, `locations.capacity` existe, y `staging_areas.staging_type`
  acepta `'INBOUND'`. Nunca se usaron, pero el diseno lo anticipo.
- **PERO** `staging_areas` tiene PK simple (`staging_id`): una fila INBOUND
  id=1 pisaria la zona OUTBOUND id=1. Decision tecnica F0: tabla nueva
  `inbound_docks` (aditiva, `CREATE TABLE IF NOT EXISTS` no rompe DBs
  existentes) en vez de reusar `staging_areas`.
- El mecanismo de OLAS de INIT-4 (`dispatcher._wo_elegible_por_ola`) permite
  pre-generar las WOs de putaway en t=0 con release = hora de llegada del
  camion: NO hace falta inyeccion dinamica de trabajo ni cirugia al dispatcher.
- El tileset del TMX ya define el tipo `inbound` ("Zona entrada/recepcion",
  gid 6, walkable). Las filas superiores y=0..2 del WH1 son caminables.
  Anclas de muelles elegidas: **(3,1), (15,1), (27,1)** (y=1 para no pisar la
  fila de spawn y=0).
- El ciclo del operario (`agent_process`) es pick-oriented: F2 agrega un tipo
  de tour inverso (cargar en muelle -> depositar en racks). Rutas, congestion
  timewindow y anti-colision sirven sin cambios.
- El stock hoy es estatico (nace en t=0). El putaway lo vuelve dinamico EN
  MEMORIA (v1); la BD no se escribe en caliente.

## Fases

| Fase | Entrega | Estado |
|---|---|---|
| F0 | Dominio y datos: hoja `InboundDocks` en el Excel canonico, tabla `inbound_docks` (schema+importer), loaders en data_manager, bloque `inbound` en config_schema, archivo ASN de ejemplo (`layouts/Inbound Test.json`), tests | **HECHO 2026-07-08** |
| F1 | Llegadas: `InboundProcess` (espejo de OutboundProcess), camiones segun ASN o intervalo estocastico, descarga a buffer de muelle, eventos al .jsonl + marcadores en visor | **HECHO 2026-07-08** |
| F2 | Putaway: WO tipo `putaway` (muelle -> ubicacion) pre-generadas en t=0, tour de deposito en operators, stock dinamico | **HECHO 2026-07-09** |
| F3 | Estrategias de slotting conmutables: `fija_por_sku` / `cercana_al_muelle` / `abc_rotacion` + selector en UI web | **HECHO 2026-07-09** |
| F4 | KPIs: `inbound_summary` (dock-to-stock time, distancia putaway, utilizacion de muelles) con el patron build_X_summary -> metadata/API/visor/Excel | **HECHO 2026-07-09** |
| F5 | Flujo mixto inbound+outbound: flota compartida, prioridades pick vs putaway, stock entrante alimenta pedidos (requiere decision 4) | pendiente |

## Contratos de datos (F0)

### Hoja Excel `InboundDocks` (en `layouts/Warehouse_Logic.xlsx`)

| Columna | Tipo | Ejemplo |
|---|---|---|
| dock_id | int (>0) | 1 |
| x | int | 3 |
| y | int | 15 |

3 filas canonicas: dock 1=(3,1), dock 2=(15,1), dock 3=(27,1).

### Archivo ASN (JSON, espejo de "Orders Test.json")

```json
{
  "metadata": { "version": "1.0", "description": "..." },
  "trucks": [
    {
      "truck_id": "IN-001",
      "arrival_time": 300,
      "dock_id": 1,
      "lines": [ { "sku_id": "SKU029", "quantity": 24 } ]
    }
  ]
}
```

- `arrival_time` en segundos de simulacion. `dock_id` opcional (sin el, el
  motor asigna muelle libre en F1).

### Bloque `inbound` de config.json (default NEUTRO: no esta en el canonico)

```json
"inbound": {
  "enabled": false,
  "arrival_mode": "deterministic",      // deterministic | stochastic
  "asn_file_path": "layouts/Inbound Test.json",
  "truck_interval": 600.0,               // modo stochastic
  "pallets_per_truck": 10,               // modo stochastic
  "units_per_pallet": 20,                // modo stochastic (qty por pallet, F1)
  "unload_time_per_pallet": 15.0,
  "slotting_strategy": "cercana_al_muelle"  // fija_por_sku | cercana_al_muelle | abc_rotacion
}
```

### Decisiones tecnicas de F1 (2026-07-08)

- Muelles = `simpy.Resource(capacity=1)`: cola de camiones FIFO determinista,
  sin polling. Cada camion es su PROPIO proceso SimPy (descargas simultaneas
  en muelles distintos).
- 1 linea del ASN = 1 pallet (espejo de 1 WO = 1 pallet en outbound).
- Asignacion de muelle: `dock_id` explicito del ASN si existe; ausente o
  invalido -> muelle con cola mas corta (empate: id menor, determinista).
- Eventos al .jsonl: `inbound_truck_arrived` / `_docked` / 
  `inbound_pallet_unloaded` / `inbound_truck_departed`. Marcador verde
  (`truck_in`) en la barra de tiempo del visor por cada descarga.
- Buffer sin tope en F1; los pallets quedan en `almacen.inbound_buffer`
  (estado `in_dock_buffer`) hasta que F2 los consuma.
- La TERMINACION de la simulacion sigue gobernada por las WOs de picking:
  camiones con arrival_time posterior al fin del picking NO llegan (visto en
  el smoke: el 5o camion del ASN, t=3600, quedo fuera). En F2 las WOs de
  putaway entran a la lista maestra y extienden la corrida naturalmente.
  **[RESUELTO en F2: verificado en smoke, el 5o camion ahora llega y sus
  pallets se guardan.]**

### Decisiones tecnicas de F2 (2026-07-09)

- **WOs de putaway pre-generadas en t=0** desde la agenda inbound (1 linea
  ASN = 1 pallet = 1 WO, ids `WO-PUT-{truck}-{i}` alineados con
  `INP-{truck}-{i}`). Para el modo stochastic la agenda se PRE-MUESTREA en
  t=0 (`build_stochastic_schedule`, FINITA via `num_trucks` default 5) y el
  InboundProcess la reproduce: equivalente bajo seed y necesario para
  conocer las WOs de antemano.
- **Elegibilidad por evento, no por reloj:** la WO nace `pallet_ready=False`
  y el InboundProcess la libera al descargar (`marcar_pallet_listo`, que
  ademas fija el muelle REAL: no se puede precomputar porque depende de la
  contencion de muelles). Mas preciso que las olas por release_time.
- **Cola propia en el dispatcher** (`putaway_pendientes`): las estrategias
  de pick no la ven; SI entra a `lista_maestra` => la terminacion espera a
  que todo se guarde. Prioridad: PICKS PRIMERO (despacho a cliente manda);
  putaway solo cuando el flujo de picks no encontro tour. F5 revisa esto.
- **1 pallet por viaje** (realismo de paleta: un montacargas lleva UNA).
  El work_area de la WO = el del DESTINO => mismo filtro de equipamiento
  que un pick (Forklift guarda en Area_High, Ground en Area_Ground).
- **Slotting F2 = `fija_por_sku`** (el pallet va donde su SKU vive, menor
  pick_sequence). F3 lo hace conmutable con las otras dos estrategias.
- **Stock dinamico via `data_manager.add_stock`** (simetrico del
  `consume_stock` que los picks YA usan escribiendo inventory en caliente;
  el plan original decia "en memoria" pero la simetria con el mecanismo
  existente gana). `restore_inventory_baseline` al inicio de cada corrida
  garantiza que el stock agregado no se acumula entre corridas.
- **Determinismo verificado con inbound ON:** dos corridas seguidas con
  seed 42 dan .jsonl con sha256 identico (63f8da4e...).
- Eventos nuevos: `inbound_putaway_started` (pallet cargado en muelle) e
  `inbound_pallet_stored` (deposito, con `dock_to_stock` en segundos de sim
  = t_stored - t_unloaded; insumo directo de F4).
- Claves nuevas de config (registradas en schema): `num_trucks`,
  `putaway_load_time` (default 10 s).
- Edge documentado: pallet cuyo SKU no esta en el plan maestro => WARN, se
  descarga pero queda en buffer sin WO (no bloquea la terminacion).

### Decisiones tecnicas de F3 (2026-07-09)

- **3 estrategias en `inbound.py`** (`resolve_slotting`, conmutadas por
  `config.inbound.slotting_strategy`; validas en `SLOTTING_STRATEGIES`):
  - `fija_por_sku` (default): menor `pick_sequence` -> siempre el mismo slot.
  - `cercana_al_muelle`: candidata con menor Manhattan al muelle REAL ->
    minimiza el viaje de guardado de hoy.
  - `abc_rotacion`: demanda de picking de ESTA corrida -> terciles A/B/C
    (`compute_abc_classes`); 'A' cerca del staging de salida (pickear rapido
    manana), 'C' lejos (liberar slots premium), 'B' fija.
- **Coherencia del inventario:** un SKU solo se guarda en ubicaciones donde
  ese SKU YA vive (`sku_candidate_locations`). La tabla `inventory` tiene PK
  `location_id` (1 SKU por ubicacion): guardar un SKU en una ubicacion ajena
  romperia el modelo. Por eso el slotting elige ENTRE los ~7 slots propios
  del SKU, no cualquier ubicacion libre.
- **Resolucion AL ATERRIZAR** (no en t=0): `cercana_al_muelle` depende del
  muelle real (contencion de colas), imposible de precomputar. `fija_por_sku`
  se fija en t=0 como destino PROVISORIO (valida SKU + da work_area para el
  snapshot); las otras dos re-resuelven en `marcar_pallet_listo`.
- **Fallback determinista:** sin datos para la estrategia pedida (p.ej. sin
  dock_cell) degrada a `fija_por_sku`; estrategia desconocida en config ->
  WARN + `fija_por_sku`.
- **UI:** tab "Inbound" nuevo (paso 6, renumera Optimizacion->7,
  Experimentos->8). Toggle + modo (ASN/estocastico con campos condicionales)
  + selector de slotting, patron de guia de 3 niveles (.tab-intro/
  .description-text/.help-text). Opt-in real: si el toggle esta off y no
  habia inbound, el config canonico se conserva SIN el bloque (el merge del
  backend no lo agrega) => gate byte-identico intacto.
- Verificado: las 3 estrategias producen destinos DISTINTOS para los mismos
  pallets (smoke con ASN canonico); bloque inbound de la UI valida limpio en
  el schema (sin claves desconocidas); config.json canonico sigue sin inbound.

### Decisiones tecnicas de F4 (2026-07-09)

- **`build_inbound_summary(almacen)`** en `core/replay_utils.py` (mismo patron
  que `build_bottleneck_summary`): consolida `almacen.inbound_metrics` en un
  dict serializable, deriva promedios (dock-to-stock, distancia) y transporta
  la `slotting_strategy`. `available=False` si inbound no corrio.
- **KPIs:** dock-to-stock (tiempo de sim muelle->stock), distancia de guardado
  por pallet (la palanca DIRECTA del slotting), contencion de muelles
  (esperas, buffer pico), totales de recepcion/putaway.
- **Distancia de putaway:** medida por operario como delta de
  `total_distance_traveled` acotado al tour de putaway; acumulada en
  `inbound_metrics` via `registrar_stock_putaway(distance=...)` y viajando
  ademas en cada evento `inbound_pallet_stored`.
- **Plomeria completa:** metadata del .jsonl -> `app_state` (parse en
  SIMULATION_START) -> API (`inbound_summary` en /api/state) -> panel
  "Recepcion (Inbound)" del visor (reusa clases de bottleneck) -> hoja Excel
  "Inbound". Ademas `export_optimization_metrics` emite `avg_dock_to_stock` /
  `avg_putaway_distance` como KPIs de nivel superior, agregados a
  `OPTIONAL_KPI_KEYS` del experiment runner => el **A/B compara estrategias
  de slotting con numeros** (t-test pareado, None-safe como fill_rate_pct).
- **REGLA BN-05 respetada:** todo el summary es tiempo de SIMULACION o
  distancia de grilla (deterministas); test IN-43 prohibe claves wall-clock.
- **Baseline actualizado** (`930a1e6f...`, 4.920.393 bytes): F4 agrego SOLO la
  clave `inbound_summary` a la metadata (linea 1) del .jsonl -- verificado que
  los EVENTOS (linea 2+) quedan byte-identicos (sha `6e57752e...` con y sin
  F4). Mismo caso que MEJ-BOTTLENECK: metadata nueva legitima, no cambio de
  comportamiento.
- **KPI discrimina** (smoke, seed 42): distancia avg cercana_al_muelle 29.4 <
  abc 30.8 < fija 31.4 celdas -- la estrategia "cercana" recorre menos, como
  se diseno. F4 hace medible lo que F3 hizo configurable.

`enabled=false` (o bloque ausente) => comportamiento identico al historico
EN LOS EVENTOS; desde F4 la metadata lleva `inbound_summary:{available:false}`
(baseline `930a1e6f`). El gate DEBE pasar sin `--update-baseline`.

## Regla de validacion por fase

Cada fase cierra con: `python -m pytest -q` verde + `python
scripts/regression_gate.py` PASS + docs al dia. (F4 reajusto el baseline una
vez por la metadata nueva; de aca en mas el gate pasa sin update salvo cambio
real de comportamiento.)

## Alcance v1 COMPLETO (F0-F4)

Con F4 cerrado, el alcance v1 aprobado por el Director esta HECHO: recepcion
-> putaway -> stock, con 3 estrategias de slotting comparables por KPIs en el
A/B. Falta solo **F5 (flujo mixto)**, segunda etapa que requiere la decision 4
del Director (stock del dia disponible para picking del mismo dia vs turnos
separados).
