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
| F2 | Putaway: WO tipo `putaway` (muelle -> ubicacion) pre-generadas con release=arrival (mecanismo de olas), tour de deposito en operators, stock dinamico en memoria | pendiente |
| F3 | Estrategias de slotting conmutables: `fija_por_sku` / `cercana_al_muelle` / `abc_rotacion` + selector en UI web | pendiente |
| F4 | KPIs: `inbound_summary` (dock-to-stock time, distancia putaway, utilizacion de muelles) con el patron build_X_summary -> metadata/API/visor/Excel | pendiente |
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

`enabled=false` (o bloque ausente) => comportamiento identico al historico;
el gate byte-identico DEBE pasar sin actualizar baseline en F0 y F1.

## Regla de validacion por fase

Cada fase cierra con: `python -m pytest -q` verde + `python
scripts/regression_gate.py` PASS (sin `--update-baseline` mientras
`inbound.enabled=false` no este en el canonico) + docs al dia.
