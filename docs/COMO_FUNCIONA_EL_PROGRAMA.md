# COMO FUNCIONA EL PROGRAMA — Verdades descubiertas (prueba y error)

> Referencia practica de "como funciona REALMENTE el simulador", construida
> rastreando el codigo y validando con corridas. Sirve para retomar sin volver a
> redescubrir lo mismo. Complementa AUDITORIA.md (vivo vs muerto) y los planes.
> Ultima actualizacion: conexion del layout WH1 v2 + staging de zona (Iniciativa #3).

---

## 1. DE DONDE SALE CADA COSA (cadena de datos real)

| Dato | Fuente REAL que usa el motor | NO de donde se cree |
|------|------------------------------|---------------------|
| Geometria del mapa (tamano, racks, suelo) | `layouts/*.tmx` (propiedades de tile) | - |
| Walkability (que celdas se pueden pisar) | Propiedad `walkable` de cada tile, leida del TMX por pytmx | NO de `custom_tileset_mapping.json` |
| Puntos de picking (donde se recoge) | **`warehouse.db`** (tabla picking) si existe; si no, hoja `PickingLocations` del Excel | NO de los tiles del TMX (el TMX solo marca `type=picking_location` para conteo/validacion) |
| Posiciones de STAGING (donde se deposita) | **`warehouse.db`** (tabla `staging_areas`, type OUTBOUND) si existe; si no, hoja `OutboundStaging` del Excel | NO de los tiles del TMX (las cajas dibujadas son SOLO decorativas para el motor) |
| Catalogo de SKUs y stock | `warehouse.db` (inventario) si existe; si no, fallback | - |
| Ordenes (que pedir) | Archivo JSON (`order_file_path`), modo determinista; o aleatorio | - |
| Configuracion (flota, politica, flags) | `config.json` (o el `config_stress_*.json` que se pase) | - |

**Conclusion clave:** los TILES del mapa solo deciden por donde se camina y donde
hay racks. El staging y el picking REALES salen de la BD/Excel, NO de los dibujos
del mapa. Por eso puedes dibujar las cajas de staging donde quieras: para el
motor solo importa que esas celdas sean caminables y que sus coordenadas esten
en la tabla de staging (BD/Excel).

---

## 2. LA TRAMPA #1: BASE DE DATOS vs EXCEL  (la mas importante)

`data_manager.py` decide la fuente asi (`__init__`, ~L83):
```
if os.path.exists(<project_root>/warehouse.db):  -> carga de la BD (SQLite)
else:                                            -> carga del Excel (fallback)
```
**Si existe `warehouse.db`, el Excel se IGNORA por completo.** Editar
`Warehouse_Logic.xlsx` no cambia nada mientras exista la BD. Esto confundio
mucho: cambiabamos el Excel y la sim seguia con datos viejos.

Para cambiar datos (p.ej. staging), hay que actualizar la BD (o borrarla/renombrarla
para forzar el Excel). Ojo: si se renombra la BD, el catalogo/stock tambien pasa a
fallback (puede generar SKUs sinteticos), asi que lo mas seguro es ACTUALIZAR la BD.

### Esquema de staging en la BD (descubierto)
Tabla `staging_areas(staging_id INTEGER PRIMARY KEY, staging_type, legacy_x, legacy_y)`.
El `staging_id` era PRIMARY KEY => **solo admitia 1 celda por staging**. Para
modelar zonas de varias celdas (Iniciativa #3) hubo que recrear la tabla SIN esa
clave, para permitir varias filas por `staging_id`. (Hecho; BD respaldada en
`_backup_iniciativa3/warehouse.db.bak`.)

> BUG conocido (CLAUDE.md): `run_migration.py` lee `data/layouts/Warehouse_Logic.xlsx`
> pero la sim lee `layouts/Warehouse_Logic.xlsx`. Dos copias que pueden divergir.

---

## 3. LA TRAMPA #2: COMO SE INTERPRETA EL TMX

- El significado de cada ficha (walkable, type) se lee de las PROPIEDADES del
  tileset que esta DENTRO del .tmx, via `pytmx.get_tile_properties` (en
  `layout_manager._build_collision_matrix` y `_extract_picking_points`).
- El archivo `layouts/custom_tileset_mapping.json` (numeros -> significado) EXISTE
  pero **NINGUN codigo lo usa** (verificado con grep). No sirve para arreglar nada.
- `_extract_picking_points` busca tiles con `type == 'picking_location'`. Si el
  tileset marca el picking con otro nombre (p.ej. `MultiLevelPickingPoint` en una
  copia vieja del .tsx), NO se detectan picks. (Igual el motor usa la BD/Excel para
  los picks reales; esto solo afecta el conteo del TMX.)

---

## 4. LA TRAMPA #3: TILED Y LOS TILESETS EXTERNOS

Al editar el mapa en Tiled y guardar, Tiled tiende a **referenciar el tileset
como archivo EXTERNO** apuntando a tu instalacion (p.ej. `D:/Tiled/...` o
`../../../../Tiled/...`). Entonces el motor NO encuentra el tileset y el mapa NO
carga (`Cannot find tileset file ...`). Sintomas vistos: doble tileset (un mismo
dibujo con dos "codigos" distintos -> conteos erroneos), o fallo total de carga.

**Como evitarlo en Tiled:** antes de guardar, **Map -> Embed Tileset** (incrustar),
para que el .tmx sea AUTO-CONTENIDO (un solo tileset, sin enlaces externos). La
unica referencia externa aceptable es la imagen `.png` (ruta RELATIVA, en la misma
carpeta `layouts/`).

Tambien util: dibujar con UN solo tileset (no mezclar dos), y usar fichas
caminables para staging (floor/depot/inbound/parking dan igual: lo que importa es
`walkable=true`; la posicion real del staging la pone la BD/Excel).

---

## 5. LA TRAMPA #4: EL ENTORNO (FUSE + bytecode cacheado)

Este entorno monta los archivos por FUSE y tiene dos comportamientos que enganan:

1. **Escritura que parece truncada.** Tras editar un archivo (herramienta Edit/Write,
   o un guardado de Tiled), la VISTA del archivo puede verse cortada al final
   (`py_compile` falla con "unexpected EOF" / "string never closed"). PROTOCOLO:
   - Tras CADA edicion de codigo: `python3 -m py_compile <archivo>`.
   - Si falla por truncado: round-trip `mv f f.rt && mv f.rt f` (rename puro, no
     copia bytes) fuerza a FUSE a re-resolver y vuelve a verse completo. Recompilar.
2. **Bytecode `.pyc` cacheado (stale).** Python puede ejecutar `__pycache__` VIEJO y
   dar falsos positivos (la "validacion" pasa porque corrio codigo anterior).
   PROTOCOLO: antes de validar, mover los `__pycache__` (`mv ... _old`) y correr con
   `PYTHONDONTWRITEBYTECODE=1`.
3. **Git en FUSE:** los `git commit` funcionan pero tiran warnings `unable to unlink
   tmp_obj` (inofensivos). Si hay `.git/*.lock` zombi (de una sesion que crasheo),
   limpiarlos con `mv` (rm da EPERM): `mv .git/HEAD.lock .git/HEAD.lock.bak`.

---

## 6. COMO CORRER Y VALIDAR (headless)

- **Generar el .jsonl de una corrida** (sin analytics, rapido): script tipo
  `gen_jsonl.py` -> crea `EventGenerator(headless_mode=True, config_path=...)`,
  `crear_simulacion()`, loop `env.run(until=env.now+1.0)` hasta
  `simulacion_ha_terminado()`, y `volcar_replay_a_archivo(...)`.
- **Harness de estres:** `_stress_harness.py <config> [cap_seg]` (corre el loop y
  vuelca co-ocupacion del CongestionManager).
- **No-regresion (flag off):** comparar el CUERPO del .jsonl (md5 sin la linea-1,
  que es el header con timestamp/config). Baseline conocido del escenario de estres
  (mapa viejo): `18502db7de9f33bdccf94db742c45dd8` (9918 eventos, sim_end_t=262/268).
- **Dependencias** (instalar en el sandbox si arranca limpio):
  `pip install simpy pandas openpyxl pytmx pygame pygame_gui --break-system-packages`.
- `sys.path` debe incluir la RAIZ (por `simulation_buffer`) y `src/`.

---

## 7. SUBSISTEMA OUTBOUND (Iniciativa #3) — estado y como esta cableado

Todo gateado por `config.json["outbound"]["enabled"]` (off => comportamiento
identico al baseline). Archivos:
- `src/subsystems/simulation/outbound.py`: `Pallet`, `DockSlot`, `StagingZone`,
  `build_zone_cells` (expande un ancla a k celdas), `OutboundProcess` (esqueleto del
  camion, Fase 2).
- `warehouse.py`: lee `config["outbound"]`, construye `self.staging_zones`
  (`{staging_id: StagingZone}`) y `self.outbound_metrics`. Si el Excel/BD da varias
  celdas por staging, usa TODAS como zona; si da 1, auto-expande a `zone_capacity_default`.
- `data_manager.py`: lee VARIAS celdas por `staging_id` (BD y Excel) en
  `outbound_staging_zone_cells`; `get_outbound_staging_zones()` las devuelve.
  `outbound_staging_locations` sigue siendo 1 ancla por id (compat).
- `operators.py` (descarga, Ground+Forklift): por cada WO -> `_outbound_wait_slot`
  (backpressure: espera si la zona esta llena) + `_outbound_place_pallet` (crea
  Pallet, ocupa slot, metricas) + `_outbound_scaffold_release` (SCAFFOLD Fase 1:
  libera el slot tras `dwell_scaffold` seg = proxy del camion, se reemplaza en Fase 2).
- `event_generator.py`: arranque gateado del OutboundProcess (no-op en Fase 0/1).

Config `outbound`: `enabled, dispatch_policy, truck_interval, truck_capacity,
loading_time, zone_capacity_default, slot_wait_alert, slot_poll_dt, dwell_scaffold`.

**Lo que FALTA (Fase 1.2b):** reservar la celda del pallet en la `ReservationTable`
para que el planner (Opcion C) esquive los pallets y el I1 baje a ~0. Riesgo:
reservar obstaculos puede dejar al planner sin ruta (regresion vista en Fase 2b).

---

## 8. LAYOUT NUEVO WH1 v2 (conectado y validado)

- `layouts/WH1 v2.tmx`: 30x42 (se agrando hacia abajo). Arriba igual (racks +
  picking en y=3..26). Abajo, zona de carga: **7 stagings de 20 celdas** (pares de
  columnas x={3,4},{7,8},...,{27,28}, filas y=29..38) con pasillos entre pares
  (cada caja tiene un pasillo caminable al lado => ningun pallet queda atrapado).
- `layouts/Warehouse_Logic_v2.xlsx`: hoja `OutboundStaging` con esas 140 celdas
  (20 por staging) + `PickingLocations` intacta.
- BD: tabla `staging_areas` recreada (sin PK) con las 140 celdas OUTBOUND.
- `config_stress_tw_v2.json`: `layout_file=layouts/WH1 v2.tmx`,
  `sequence_file=layouts/Warehouse_Logic_v2.xlsx`, `outbound.enabled=true`.
- **Resultado de la corrida de prueba (determinista, 20 agentes, 100% a staging 1):**
  termina (sim_end_t=280), 126 pallets, **0 esperas por slot** (pico 17/20 => la
  zona de 20 no se llena), **I1 = 56** (bajo de 81 solo por repartir en la zona).

---

## 9. APENDICE — RUTAS Y PUNTOS DE CODIGO UTILES
- Eleccion fuente de datos: `data_manager.__init__` (~L83), `db_path` = raiz/warehouse.db.
- Staging desde BD: `data_manager._load_staging_areas_from_db` (~L327).
- Staging desde Excel: `data_manager._process_outbound_staging` (~L490+).
- Walkability/picking del TMX: `layout_manager._build_collision_matrix` (~L80),
  `_extract_picking_points` (~L134, busca `type=='picking_location'`).
- Init congestion/outbound: `warehouse.AlmacenMejorado.__init__` (~L195 congestion,
  ~L239 outbound).
- Descarga: `operators.py` bucle "V12 GRANULAR DISCHARGE" (Ground ~L860, Forklift ~L1270).
- Loop del motor: `event_generator.ejecutar` (~L211).

---

## 10. LA CAPA WEB (UI navegador) — verdades descubiertas

- **El servidor corre OCULTO.** Se lanza con `start_server.bat` / `server_manager.py`
  / `start_hidden.py` y NO deja ventana visible. Se gestiona por PID file (`server.pid`,
  puerto 8000). **Reiniciar:** `stop_server.bat` + `start_server.bat`, o
  `python server_manager.py restart`. (Comandos: start/stop/restart/status/logs.)
- **El servidor hay que REINICIARLO para que tome cambios de `web_prototype/server.py`**
  (el codigo vive en memoria del proceso). Editar el archivo no basta.
- **`/api/layout`** (el endpoint que el visor usa para dibujar el mapa): ANTES tenia una
  ruta FIJA mala (`data/layouts/layout_v2.tmx`, inexistente) y caia al mapa viejo
  (WH1.tmx, 30x30), que NO coincidia con la simulacion -> el replay "no se veia bien".
  ARREGLADO (commit 7d00c7a): ahora resuelve el mapa desde `config.json` (`layout_file`),
  el mismo que usa la simulacion. Carga el TMX con pytmx (necesita poder leer la imagen;
  si el .tmx referencia un tileset externo, falla/cuelga -> ver #4: incrustar tileset).
- **TRAMPA IMPORTANTE — el configurador BORRA bloques al guardar.**
  `web_prototype/config_manager.py::save_config` hace `json.dump(config_de_la_UI)`, es
  decir **SOBRESCRIBE** `config.json` solo con los campos que la UI conoce. Los bloques
  que la UI NO maneja (`congestion`/time-window y `outbound`/carriles) **se PIERDEN** en
  cada guardado (y el guardado ocurre automaticamente al darle *Run Simulation*).
  CONSECUENCIA en las corridas WEB: sin `congestion` los operarios se ATRAVIESAN; sin
  `outbound` descargan en la PRIMERA loza (no usan carriles ni caminan al fondo).
  FIX recomendado: que save_config FUSIONE con el config existente (preservar bloques no
  manejados) en vez de sobrescribir. (PENDIENTE.)
- **El visor (pagina `/`) auto-llama `/api/layout` al cargar.** Si ese endpoint se cuelga
  (p.ej. tileset externo o mapa pesado), el visor queda en "Loading..." y, si se le
  insiste, puede dejar el servidor sin responder (worker bloqueado) -> reiniciar.
- **Flujo correcto de la UI:** `/web_configurator/` -> pestania "Layout y Datos" (poner
  `layouts/WH1 v2.tmx` + `Warehouse_Logic_v2.xlsx`) -> "Outbound Staging" (distribucion)
  -> "Run Simulation" (corre el motor headless, genera replay) -> "Watch Replay" (abre
  el visor en `/`). El motor del run es el mismo headless (mis cambios aplican).
- **Endpoints clave:** `/api/configurator/config` (GET/POST config.json),
  `/api/layout` (mapa para el visor), `/api/snapshot?t=` (estado del replay),
  `/api/upload-orders`, `/api/upload_replay`. El configurador usa `/api/configurator/*`
  (NO depende de `/api/layout`).

<!-- FIN_DOCUMENTO -->
