# CHANGELOG — Gemelo Digital de Almacen

Registro append-only de iniciativas cerradas. NUNCA se edita una entrada vieja,
solo se agrega una nueva arriba. El detalle exhaustivo vive en el mensaje de
commit (`git log`/`git show <sha>`) y, si existio, en el plan original bajo
`docs/antiguos/`; esto es solo un indice escaneable con el "por que" cuando no
es obvio del commit.

Formato por entrada: `YYYY-MM-DD  ITEM — resumen de 1-2 lineas. sha(s). [link a plan si aplica]`

---

## 2026-07-11 (cont. 3)

- **INIT-8 F4 — TIEMPOS REALISTAS, variabilidad Log-Normal + packing por
  clase (INICIATIVA COMPLETA F1-F4).** Bloque `tiempos.variabilidad`
  (opt-in, off; canonico intacto => GATE PASS sin update): Log-Normal con
  MEDIA preservada (E[X]=t; sigma de cv), acotada en 0, cola derecha — la
  correccion metodologica del doc del Director (Law/Simio: JAMAS Normal ni
  Triangular). Reproducible bajo WAREHOUSE_SEED (2 corridas -> sha
  identico). REGLA CRITICA: una muestra por WO — `_tiempo_pick_final`
  cachea en la WO porque _compute_pick_time se llama 2 veces (reserva del
  planner + timeout real); mismo patron en descarga/putaway (reserva y
  timeout con el MISMO valor) => plan espacio-temporal consistente.
  Packing: clave `pack` por clase en clases_manejo (descarga = discharge +
  pack; 0 = neutro de objeto exacto). Efecto medido: makespan 5696 -> 6674 s
  (+17%) con cv 0.25 + packs de ejemplo — la varianza crea colas que el
  promedio esconde. Tests T840..844. 189 passed.

---

## 2026-07-11 (cont. 2)

- **INIT-8 F3 — TIEMPOS REALISTAS, velocidad segun carga (opt-in).** Bloque
  `tiempos.velocidad_por_carga` (default off, canonico sin tocar => GATE
  PASS sin update): factor de tiempo 1/(1 - min(kg*0.0084, 0.5)) calibrado
  con Indian Army 2022 (22 kg => -18.5% de velocidad; test T831 verifica
  1.35 -> 1.10 m/s). `cargo_peso` espejado en los 11 sitios de mutacion de
  cargo_volume. Aplicado UNA vez a la entrada de `_recorrer_tramo`: el plan
  espacio-temporal recibe el speed efectivo => reservas consistentes con la
  ejecucion (cero riesgo de co-ocupacion). Forklift exento por default
  (`aplica_forklift`). Penalizacion por giro DESCARTADA (escala vehicular,
  no aplica a grilla peatonal de 1 m; y desincronizaria las reservas del
  planner). Efecto medido: +2.6% makespan con flag on (seed 42). Tests
  T830..834. 184 passed.

---

## 2026-07-11 (cont.)

- **INIT-8 F2 — TIEMPOS REALISTAS, activacion (volumen real + tiempos por
  clase/peso).** LA actualizacion intencional de baseline de la iniciativa
  (nuevo: `8f9f78d5...`, 7.161.322 bytes; commiteado junto). Formula
  extendida en `_compute_pick_time`: `(base + por_unidad*qty +
  por_volumen*vol + por_kg*peso) * clase.mult + clase.recargo` con rama de
  COMPAT EXACTA para configs viejas (T820). Canonico calibrado con el doc
  del Director: base 10 + 2/unidad (~14 s/caja POMS), por_kg 0.15
  (fatigue-factor Blue Yonder), recargos por clase (MTM). Putaway load
  escalado por clase (pallet linea blanca 37 s vs 10 s). Volumen real
  activo en importer + fallback (SKU.volumen: polera=1, refrigerador=66-75
  => carro de 150 lleva max 2). config_schema: `por_kg` +
  `clases_manejo{mult,recargo}`. Tests T820..824 + T802/T803 re-pineados al
  contrato F2. **Impacto medido (seed 42): makespan +82% (3122->5696 s),
  throughput -44% -- el mundo plano sobreestimaba capacidad ~2x, como
  predice Kostrzewski 2016.** 179 passed + gate PASS x2 con el baseline
  nuevo.

---

## 2026-07-11

- **INIT-8 F1 — TIEMPOS REALISTAS, catalogo fisico por SKU.** Arranca la
  iniciativa (plan + tabla de calibracion con fuentes en
  `docs/PLAN_INIT8_TIEMPOS.md`, basada en el doc del Director "Ingenieria de
  Tiempos y Movimientos en CD": MTM-Logistics, regresion POMS 2007,
  biomecanica de carga, playbooks SAP EWM/Manhattan/Blue Yonder, Law/Simio).
  Hallazgo: la DB tenia columnas volume_m3/weight_kg/category con datos
  PLANOS (todos los SKUs identicos). Entregado: hoja `SkuCatalog` en el
  Excel canonico (50 SKUs, 5 clases de manejo pequeno->extra_grande con
  volumen/peso sinteticos coherentes, generacion determinista seed 8);
  importer + fallback Excel del data_manager cargan peso_kg y clase_manejo
  (DB `category`); `SKU` del motor gana `peso`/`clase` (defaults neutros).
  **Estrategia de baseline decidida:** volumen_m3 real viaja en la hoja pero
  NO se importa en F1 (fluye a SKU.volumen => capacidad/tours); se activa en
  F2 JUNTO con el modelo de tiempos = UNA sola actualizacion intencional.
  Correccion del doc del Director a la propuesta original: F4 usara
  Log-Normal (no Triangular). 4 tests (T801..804; T802 pinea volume_m3
  intacto). Validado: 174 passed + GATE PASS byte-identico CON el catalogo
  cargado (los atributos fluyen sin tocar comportamiento).

---

## 2026-07-10 (cont. 3)

- **Menores de la auditoria INIT-7 (paquete de 3).** (1) UX cross-dock:
  aviso visual naranja en el tab Inbound cuando el toggle esta activo con
  pedidos Estocasticos (el motor ya se desactivaba solo, pero solo avisaba
  por consola); reactivo al toggle Y al radio de modo de pedidos del paso 1.
  (2) KPI `throughput_picks_per_s` (motor exporta `total_picks_completed` =
  picks exitosos sin putaway ni failed; runner lo deriva y lo suma a
  ALL_KPI_KEYS): comparable limpio entre configs con/sin inbound -- el
  `throughput_wo_per_s` historico mezcla picks+putaway con el tiempo
  extendido de la recepcion (verificado: 45 picks vs 55 totales en la demo,
  0.0123 vs 0.0150 wo/s). (3) Tabla del visor: LOCATION muestra
  "(en camion)" para WOs de putaway antes de aterrizar (heuristica por
  prefijo WO-PUT en el frontend; agregar task_type al to_dict cambiaria la
  metadata/baseline por un cosmetico). 170 passed + GATE PASS.

---

## 2026-07-10 (cont. 2)

- **MEJ-ROBUSTEZ-AGENTES — degradacion por WO + watchdog de no-progreso.**
  La investigacion CORRIGIO el diagnostico de la auditoria: una excepcion a
  mitad de tour NO colgaba en silencio -- propagaba a env.run() y REVENTABA
  la corrida ENTERA (verificado empiricamente; sin .jsonl ni Excel); y el
  cuelgue estatico obvio (area sin agente) ya lo cubria el guard QA-3
  pre-vuelo. Solucion A+D (mejor que la propuesta original): **(A)** cuerpo
  del tour de picks extraido VERBATIM a `_execute_pick_tour` (274 lineas,
  validado por gate byte-identico) y ambos tours envueltos en try/except ->
  `_abort_tour` marca las WOs no completadas via
  `dispatcher.notificar_wo_fallida` (status='failed', cuentan como cerradas
  para la terminacion, NO inflan el KPI de exitosas; evento
  `agent_tour_crashed`), el agente sobrevive. Fallar rapido, sin reintentos
  (re-encolar puede re-crashear en loop). **(D)** watchdog de no-progreso en
  el loop del engine (`compute_stall_limit`: 7200s de sim + extension por la
  ultima llegada inbound): si nada se cierra en ese lapso, aborta con
  diagnostico accionable (WOs huerfanas + areas de la flota) y genera el
  volcado PARCIAL. Cubre los cuelgues dinamicos que QA-3 no ve (ubicacion
  inalcanzable, bugs logicos). 4 tests (RB01..04). Validado: 170 passed +
  GATE PASS (extraccion verbatim confirmada) + smoke A (excepcion inyectada:
  corrida completa con 20 failed y 582 exitosas, antes se perdia todo) +
  smoke B (deadlock inyectado: watchdog aborta a los 4200s de sim con
  diagnostico y jsonl parcial, antes colgaba para siempre).

---

## 2026-07-10 (cont.)

- **AUDITORIA INIT-7 + 3 fixes.** Auditoria en frio de F0-F5 a pedido del
  Director (suite+gate en frio, replay demo evento por evento, revision
  critica de caminos nuevos). Sano: ciclo cross-dock integro, contabilidad
  del dispatcher, coherencia de stock, opt-in real, visor tolera nulls.
  Fixes aplicados: **(1)** `work_orders_total_inicial` se REFRESCA en cada
  alta (antes se fijaba en la 1ra llamada: con inbound el visor mostraba
  progreso 125% = 55/44; verificado ahora 55/55; canonico = 1 llamada =>
  baseline intacto; test IN-26). **(2)** A/B: `_collect_paired_values`
  parea por semilla ANTES de filtrar None (antes None en semillas distintas
  desalineaba los pares del t-test; 3 call sites; test nuevo). **(3)** Demo
  cross-dock movida de temp_web/ (purga 24h la habria borrado) a
  `examples/` (trackeado, con README). Pendientes levantados a BACKLOG:
  MEJ-ROBUSTEZ-AGENTES (tour sin try/except => cuelgue infinito si algo
  revienta a mitad de tour; PRE-EXISTENTE, no regresion de INIT-7) +
  menores (aviso UX cross-dock en modo estocastico, throughput picks-only,
  LOCATION vacia en tabla). 166 passed + GATE PASS.

---

## 2026-07-10

- **INIT-7 F5 — INBOUND, flujo mixto (INICIATIVA COMPLETA F0-F5).** Decision
  4 del Director: AMBAS opciones conmutables por config. **F5a**
  `inbound.putaway_priority` (`picks_first` default historico /
  `putaway_first`: el dispatcher asigna el putaway pendiente mas viejo ANTES
  de evaluar picks) + KPI de contencion cruzada `avg_putaway_wait` (pallet
  listo esperando agente, medido en `_asignar_putaway`); smoke seed 42:
  espera 1305s vs 88s, dock-to-stock 1323s vs 108s. **F5b**
  `inbound.cross_dock_enabled` (solo deterministic): `_preparar_cross_dock`
  captura los backorders de la allocation t=0 (LEIDOS DIRECTO de la
  estrategia -- bug real: `_last_validation_result` se asigna despues) y
  `_rescatar_backorders_cross_dock` crea picks dinamicos `WO-XD-####` al
  depositarse stock del SKU (FIFO, tope=pallet, hereda prioridad/due_time/
  destino del pedido original, pick_sequence real del destino); KPI
  `fill_rate_effective_pct` en service_level (claves SOLO si hubo rescates
  => metadata historica intacta, GATE PASS sin update). A/B: +
  `avg_putaway_wait` y `fill_rate_effective_pct` en OPTIONAL_KPI_KEYS. UI:
  selector prioridad + toggle cross-dock (tab Inbound); visor: grupos
  "Flota compartida" y "Cross-docking"; Excel: secciones F5. 7 tests
  (IN-50..56). Smoke F5b: pedido insaciable de SKU029 -> rescate de 24u a
  t=349s, pick despachado a t=361s, fill-rate 66.5% -> 68.7% efectivo
  (demo en temp_web/cfg_f5b_crossdock.json). Limitacion cosmetica
  documentada: total_work_orders de metadata no cuenta los XD dinamicos.
  164 passed + GATE PASS.

---

## 2026-07-09 (cont. 2)

- **INIT-7 F4 — INBOUND, KPIs (cierra el alcance v1 F0-F4).** Lo que hace
  COMPARABLES las 3 estrategias de slotting. `build_inbound_summary()` en
  `core/replay_utils.py` (patron `build_bottleneck_summary`): consolida
  `almacen.inbound_metrics` -> dock-to-stock (tiempo sim muelle->stock),
  distancia de guardado por pallet (palanca directa del slotting), contencion
  de muelles, totales. Distancia de putaway medida por operario (delta de
  total_distance_traveled acotado al tour) -> inbound_metrics + evento
  `inbound_pallet_stored`. Plomeria: metadata .jsonl -> app_state -> API
  (`inbound_summary`) -> panel "Recepcion (Inbound)" del visor -> hoja Excel
  "Inbound". `export_optimization_metrics` emite avg_dock_to_stock /
  avg_putaway_distance -> `OPTIONAL_KPI_KEYS` del A/B (t-test pareado,
  None-safe). REGLA BN-05: summary 100% deterministico (test IN-43 prohibe
  wall-clock). 4 tests (IN-40..43). Baseline REAJUSTADO (`930a1e6f`,
  4.920.393 bytes): F4 agrego SOLO `inbound_summary:{available:false}` a la
  metadata (linea 1) -- eventos byte-identicos verificados (sha `6e57752e`
  con y sin F4, mismo caso que MEJ-BOTTLENECK). Validado: 157 passed, GATE
  PASS x2 con el baseline nuevo, KPI discrimina (dist avg cercana 29.4 <
  abc 30.8 < fija 31.4 celdas), hoja Excel + panel visor OK.

---

## 2026-07-09 (cont.)

- **INIT-7 F3 — INBOUND, estrategias de slotting conmutables.** El valor de
  producto de la iniciativa: donde guardar cada pallet que llega, comparable
  con el A/B. En `inbound.py`: `resolve_slotting` con 3 estrategias leidas de
  `config.inbound.slotting_strategy` — `fija_por_sku` (menor pick_sequence),
  `cercana_al_muelle` (menor Manhattan al muelle REAL), `abc_rotacion`
  (`compute_abc_classes` sobre la demanda de picking de la corrida: 'A' cerca
  del staging de salida, 'C' lejos, 'B' fija). `sku_candidate_locations`
  garantiza coherencia del inventario (solo slots donde el SKU ya vive, PK
  `location_id`). Resolucion AL ATERRIZAR en `warehouse.marcar_pallet_listo`
  (cercana depende del muelle real, imposible en t=0); fallback determinista
  a fija. UI: tab "Inbound" nuevo (paso 6, renumera Optimizacion->7,
  A/B->8) con toggle + modo ASN/estocastico (campos condicionales) +
  selector de slotting, guia de 3 niveles; opt-in real (config canonico se
  conserva sin bloque inbound => gate intacto). 6 tests (IN-30..35).
  Validado: 153 passed, GATE PASS sin update, las 3 estrategias dan
  destinos DISTINTOS en smoke real, bloque UI valida limpio en el schema,
  config.json canonico sin inbound.

---

## 2026-07-09

- **INIT-7 F2 — INBOUND, putaway completo.** El corazon del motor inbound:
  WOs `task_type='putaway'` pre-generadas en t=0 desde la agenda (ASN o
  stochastic PRE-MUESTREADO via `build_stochastic_schedule`, finito por
  `num_trucks`), elegibles POR EVENTO cuando su pallet aterriza
  (`marcar_pallet_listo` fija el muelle real, imposible de precomputar por
  contencion). Cola propia `putaway_pendientes` en el dispatcher (los pools
  de pick no la ven; SI cuenta en lista_maestra => la corrida no termina
  hasta guardar todo — el 5o camion del smoke F1 ahora llega). Prioridad:
  picks primero, putaway de relleno (F5 lo revisa). 1 pallet por viaje;
  work_area del destino => mismo filtro de equipamiento que un pick. Tour
  de deposito en operators (`_execute_putaway_tour`: muelle -> cargar ->
  ubicacion -> depositar, con `_recorrer_tramo` = congestion timewindow
  incluida). Slotting F2 = `fija_por_sku` (F3 lo conmuta). Stock real via
  `data_manager.add_stock` (simetrico del consume_stock que los picks ya
  usan; baseline de inventario lo resetea entre corridas). Eventos
  `inbound_putaway_started` / `inbound_pallet_stored` (con `dock_to_stock`
  en tiempo de sim -> insumo de F4). 6 tests (IN-20..25). Validado: 147
  passed, GATE PASS sin update, smoke real: 5 camiones / 10 pallets, 10/10
  guardados en sus ubicaciones reales con stock +=, y DETERMINISMO con
  inbound ON verificado (2 corridas seed 42 -> sha256 identico 63f8da4e).

---

## 2026-07-08 (cont.)

- **INIT-7 F1 — INBOUND, llegadas de camiones.** Nuevo
  `src/subsystems/simulation/inbound.py`: `InboundProcess` (espejo de
  OutboundProcess) con modos deterministic (ASN via `load_asn_trucks`, valida
  y reordena) y stochastic (intervalo + SKUs muestreados del catalogo
  ordenado, reproducible bajo seed); muelles como `simpy.Resource(cap=1)`
  (cola FIFO determinista, cada camion es su propio proceso); pallets al
  `inbound_buffer` (estado `in_dock_buffer`, F2 los consume). Integracion:
  bloque inbound en `warehouse.py` (docks+metrics+process, se autodesactiva
  sin muelles), arranque 7d + telemetria en `event_generator.py`, eventos
  `inbound_truck_arrived/_docked/_pallet_unloaded/_departed` al .jsonl,
  marcador verde `truck_in` en la barra de tiempo del visor, clave
  `units_per_pallet` al schema. 7 tests (IN-10..16). Validado: 141 passed,
  GATE PASS sin update (inbound off en canonico), smoke real con ASN: 4
  camiones/8 pallets a tiempos exactos conviviendo con el picking.

---

## 2026-07-08

- **INIT-7 F0 — INBOUND, dominio y datos.** Arranca la iniciativa de
  recepcion/putaway (plan completo y 4 decisiones del Director en
  `docs/PLAN_INIT7_INBOUND.md`). Entregado: hoja `InboundDocks` en el Excel
  canonico (3 muelles fila superior: (3,1),(15,1),(27,1)); tabla
  `inbound_docks` propia (NO `staging_areas`: su PK simple haria que un dock
  INBOUND id=1 pisara la zona OUTBOUND id=1) con create-if-missing para DBs
  viejas; importer + loaders en data_manager (DB y fallback Excel, sin
  defaults: inbound es opt-in) + validacion de bounds; bloque `inbound` en
  `config_schema` (enabled/arrival_mode/asn_file_path/truck_interval/
  pallets_per_truck/unload_time_per_pallet/slotting_strategy); ASN de
  ejemplo `layouts/Inbound Test.json` (5 camiones, SKUs reales, dock_id
  opcional). 9 tests nuevos (IN-01..09). Motor NO lee nada de esto todavia:
  GATE PASS byte-identico sin update. Hallazgo clave de la investigacion:
  las olas de INIT-4 permiten pre-generar WOs de putaway con release=arrival
  (sin inyeccion dinamica); el tileset ya tenia tipo `inbound` (gid 6).

---

## 2026-07-07 (cont. 2)

- **MEJORAS ESTRUCTURALES 1-4** (las 4 oportunidades de la review,
  aprobadas en bloque por el Director; orden de relevancia):
  **(1) server.py partido en modulos** (`21eeb70`): el monolito de 1410
  lineas con 6 responsabilidades quedo en `server.py` (89 lineas, solo arma
  la app) + `app_state.py` (estado compartido) + `routers/` (configurator,
  replay, runners, system). Cuerpos extraidos VERBATIM; verificado route set
  identico (33 rutas, diff antes/despues) + smoke completo en servidor real.
  Incluyo de paso: **(4) arranque limpio** (replay_data ya no apunta a un
  replay hardcodeado inexistente de nov-2025; arranca vacio a proposito),
  el mismo `pass` muerto de traversal en validate-replay (tercera instancia
  de esa clase), y basename() en upload-orders.
  **(2) Poda de codigo muerto** (`7559403`): eliminados
  `src/analytics/exporter.py` (V1) -- el gate ATRAPO un import relativo en
  `analytics/__init__.py` que el grep inicial no vio, corregido --,
  `export_complete_analytics_with_buffer` + `_exportar_eventos_crudos_organizado`
  (0 callers), 22 selectores CSS con cuerpo identico duplicado en el
  configurador (los 4 con cuerpos DIFERENTES se dejaron: la cascada hace
  efectivo al ultimo), y los backups `style_original.css` (trackeado) /
  `style.css.backup`. Neto: ~-1200 lineas. Estilos verificados en navegador
  (badge/modal/toast).
  **(3) Optimizador independiente del cwd**: `optimizer.py` y
  `run_optimization.py` anclados a PROJECT_ROOT (entry point, temp dirs,
  optimized_configs, cwd del subprocess, cleanup del trial). Validado
  corriendo el CLI desde C:/Users/ferri: config optimizado aterrizo en el
  proyecto, cero basura en el cwd ajeno, limpieza de trials intacta.
  Suite: 125 passed. Gate PASS byte-identico tras cada fase.


## 2026-07-07 (cont.)

- **REVIEW 2 — segunda pasada de revision + prueba de integracion total**
  (pedida por el Director). **Prueba de integracion**: una sola corrida
  combinando TODO lo de la sesion (24 pedidos con destino + due_time, 4 con
  SLA imposible, destino_staging_map a zonas 1/4/6, outbound activo) --
  camiones respetaron exactamente las 3 zonas mapeadas, sla_summary reporto
  exactamente los 4 vencidos, fill 100%, bottleneck con ocupacion pico solo
  en 1/4/6, las 3 hojas nuevas en el Excel, orders_late=4 en las metricas
  del optimizador. Recarga de replay viejo (sin metadata nueva) resetea los
  3 summaries a None (sin datos pegados). **2 hallazgos reparados**:
  (1) el chequeo de path traversal de `/api/load_replay` era un `pass`
  (codigo muerto que aparentaba validar) -- ahora valida el path RESUELTO
  contra PROJECT_ROOT; verificado en vivo (`../evil.jsonl` -> 400, path
  legitimo pasa). (2) `/api/upload_replay` usaba `file.filename` crudo en el
  path -- un nombre con separadores (`a/../../x.jsonl`) escapaba de
  `uploads/`; fix con `os.path.basename`. **Verificado sin reparar**:
  `reload_data` resetea correctamente los summaries; `TMX_PATH` (arbol
  `data/` muerto) es solo un candidato de compatibilidad en una cadena de
  fallbacks sana. Suite: 125 passed. Gate PASS.

## 2026-07-07

- **REVIEW — revision de codigo de las funcionalidades recientes** (pedida
  por el Director). 4 hallazgos, todos reparados y validados:
  (1) **Procesos huerfanos al detener desde la web** (moderado):
  `stop()` de OptimizationRunner y ExperimentWebRunner usaba `terminate()`,
  que en Windows mata solo al proceso padre -- el motor de simulacion en
  curso (nieto) quedaba huerfano, seguia corriendo hasta terminar y dejaba
  su carpeta output/ sin limpiar. Fix: matar el arbol completo con
  `taskkill /T /F` (fallback a terminate en no-Windows). Validado en vivo:
  stop a mitad de replica -> 24s despues, cero carpetas huerfanas.
  (2) **Carrera en la limpieza del experiment runner** (menor):
  `run_one_replica` identificaba su carpeta con un diff antes/despues de
  output/ -- con un estudio del optimizador corriendo a la vez podia borrar
  la carpeta de OTRO proceso. Fix: usar `metrics['session_output_dir']`
  (el motor reporta su propia carpeta; mismo patron que el fix de auditoria
  del optimizador). `_find_new_output_dir` quedo muerta y se elimino.
  (3) **Guard debil del panel de cuellos de botella** (menor): comparaba la
  LONGITUD del JSON del summary -- dos replays con summaries del mismo largo
  no re-renderizaban. Fix: comparar el string completo.
  (4) **`_resolver_staging_id` sin coercion defensiva** (robustez): un
  `destino_staging_map` editado a mano con valor no numerico ("tres")
  crasheaba la generacion de pedidos. Fix: try/except con WARN + fallback
  aleatorio; "5" como string se acepta. Test nuevo lo pina.
  Tambien: mensaje del status del experimento tras un stop manual ya no
  sugiere crasheo. Suite: 125 passed. Gate PASS sin cambio de baseline.

## 2026-07-06 (cont. 2)

- **MEJ-SLA-OPT — el optimizador penaliza SLA vencido** (propuesta 2 de la
  terna, replanteada tras la observacion correcta del Director: el fill-rate
  NO depende de la config -- se decide en la asignacion de stock antes de
  simular -- pero el SLA si, porque una config mas lenta completa los mismos
  pedidos DESPUES de su due_time). `export_optimization_metrics()` ahora
  incluye `orders_late`/`sla_summary` (INIT-4b, archivo de metricas separado
  del .jsonl -> sin cambio de baseline). `SimulationOptimizer.calculate_score`
  suma `orders_late * PENALTY_LATE_ORDER` (default $50/pedido) al denominador
  del score, junto a las penalizaciones existentes. Cadena completa: CLI
  `--penalty-late`, request/runner web, campo "Penalizacion SLA vencido" en
  el tab Optimizacion (con help-text; acepta 0 para desactivar -- guard
  Number.isNaN en vez de || para no pisar el 0). NO-REGRESION: sin due_time
  en los pedidos, orders_late=0 y el score es IDENTICO al historico (tambien
  con metricas de versiones previas sin la clave, via .get). Validado
  end-to-end: corrida real con 2 de 3 pedidos vencidos -> orders_late=2 en
  las metricas y score 1.30 vs 2.31 si no hubieran vencido. 3 tests nuevos
  (no-regresion con clave ausente y orders_late=0, penalizacion proporcional,
  penalty=0 desactiva). Suite: 124 passed. Gate PASS sin cambio de baseline.
  **Con esto la terna acordada (3 -> 1 -> 2) queda COMPLETA.**

## 2026-07-06 (cont.)

- **AUDIT — auditoria integral del trabajo de la sesion** (pedida por el
  Director tras MEJ-BOTTLENECK). Verificado OK sin reparar: suite local
  121 passed; gate PASS byte-identico (x2 consecutivas, determinismo);
  **CI de GitHub en verde para todos los commits recientes de main**
  (validacion independiente en Linux); `config.json` canonico intacto desde
  MEJ-4 (coherente con el baseline); CI instala `requirements.txt` (la
  dependencia nueva scipy queda cubierta); sin residuos de archivos
  temporales ni presets no deseados. **Reparado**: (1) el optimizador Optuna
  dejaba la carpeta `output/simulation_*` completa (~5MB) de CADA trial sin
  limpiar -- un estudio de 50 trials dejaba 50 carpetas; ahora cada trial
  borra su propio output tras leer las metricas (race-free con n_jobs>1
  porque el path viene en `metrics['session_output_dir']`, no de un diff del
  directorio; `--no-cleanup` lo conserva); validado con smoke real de 2
  trials (0 carpetas nuevas). (2) Referencias rotas a `docs/HANDOFF.md`
  (renombrado a STATE.md en la reestructuracion) en el comentario del
  workflow de CI y en 2 docstrings de tests. (3) Bloque CSS del panel de
  optimizacion duplicado en el configurador (mi replace_all habia insertado
  en una region ya duplicada historicamente); deduplicado y verificado en
  navegador que los estilos siguen aplicando. **Anotado para poda futura**
  (BACKLOG): exporter.py V1 muerto, variante `_with_buffer` muerta y
  desactualizada, duplicacion historica badges/modals en el CSS del
  configurador. Smokes funcionales post-audit: optimizador CLI (2 trials,
  n_jobs=2) y experiment runner CLI (`run` + `--progress-json`) sanos.

## 2026-07-06

- **MEJ-BOTTLENECK — panel de cuellos de botella + purga de reportes muertos**
  (propuesta 1 de la terna; auditoria previa de reportes pedida por el
  Director). **Purga**: dejaron de generarse los 3 archivos por corrida que
  nadie leia -- `simulacion_completada_*.json` (placeholder "SKELETON"),
  `raw_events_*.json` (~4.5MB, duplicado del .jsonl con esquema viejo) y
  `simulation_report_*.json` (version JSON del Excel sin consumidores); el
  PNG del heatmap colgaba del JSON eliminado (acople accidental) y ahora
  cuelga del Excel. Carpeta de salida: 8 -> 5 archivos, ~4.9MB menos por
  corrida. **Consolidacion**: nuevo `build_bottleneck_summary()` en
  `core/replay_utils.py` (mismo patron que INIT-5/INIT-4b) reune hotspots de
  congestion (top 8, con celda y max concurrentes), metricas del planner
  (planes ok/fallidos, esperas por plan, solapes) y esperas del muelle
  (slot/carril, ocupacion pico por zona). Cableado en: metadata del .jsonl,
  4 respuestas de la API, hoja Excel "Cuellos de Botella" y panel nuevo en
  el dashboard derecho del visor (hotspots en ambar; hint de que es resumen
  de corrida completa, no varia con el scrubber). **Bug real detectado y
  corregido durante la validacion**: la primera version incluia
  `avg_plan_ms` (wall-clock del planner) en la metadata -> dos corridas
  identicas daban SHA distinto y el gate byte-identico quedaba roto. Se
  excluyo todo valor wall-clock del summary (queda en
  timewindow_shadow_report_*.json, no hasheado) y el test BN-05 pina la
  regla ("_ms" prohibido en el summary). Determinismo verificado con dos
  corridas consecutivas PASS. Baseline actualizado (`71fc9904...`,
  4.920.352 bytes; eventos byte-identicos desde INIT-1: sha sin linea 1 =
  `67749aa4...`). 6 tests nuevos. Suite: 121 passed. Validado end-to-end en
  navegador real (corrida con outbound + 3 zonas activas).

## 2026-07-05 (cont. 7)

- **MEJ-EXP-WEB — comparador A/B en el navegador** (propuesta 3 de la terna
  aprobada por el Director; orden acordado: 3 -> 1 -> 2 replanteada). Nuevo
  tab "Experimentos A/B" (paso 7) en el configurador: selects de Config A/B
  ("Actual" = config.json canonico, o cualquier preset guardado, validado
  con la misma barrera del guardado antes de lanzar), replicas y semilla
  base, progreso en vivo y tabla de resultados por KPI (media A/B, delta %,
  p-valor, veredicto; filas significativas resaltadas). Plomeria:
  `--progress-json` en `scripts/experiment_runner.py` (ProgressWriter con
  escritura atomica tmp+os.replace, para polling sin lecturas a medio
  escribir) + `web_prototype/experiment_runner_web.py` (singleton, mismo
  patron fire-and-forget de OptimizationRunner) + 3 endpoints
  (`/api/experiment/start|status|stop`). Guardas: A==B -> 400, replicas
  fuera de 1..50 -> 400, preset invalido -> 400, doble start -> 409.
  Validado end-to-end en navegador real: comparacion "Actual (2 ground)" vs
  preset "3 ground" con 2 replicas pareadas -> makespan -3.2% y throughput
  +3.3%, ambos DIFERENCIA SIGNIFICATIVA (p<0.05) -- resultado con sentido
  fisico. 4 tests nuevos (ProgressWriter ciclo completo/fail,
  build_compare_result serializable). Suite: 115 passed. Gate PASS sin
  cambio de baseline (no toca el motor).
- **Correccion de alcance a la propuesta 2 (senalada por el Director):** el
  fill-rate NO depende de la configuracion -- la asignacion de stock ocurre
  ANTES de simular (allocation layer: pedido vs stock, invariante a flota/
  estrategia). Lo que SI depende de la config es el SLA (due_time vs tiempo
  de completado). La propuesta 2 queda replanteada como "el optimizador
  debe penalizar SLA vencido", no fill-rate.

## 2026-07-05 (cont. 6)

- **INIT-4b — KPI de SLA vencido en reporte/visor.** Ultimo punto diferido de
  INIT-4. Reusa el patron exacto de INIT-5 (build_service_level_summary):
  nuevo `build_sla_summary()` en `core/replay_utils.py` agrupa las
  WorkOrders completadas por `order_id`, usa el MAX `tiempo_fin` del pedido
  (no esta completo hasta que TODAS sus WOs lo estan) y lo compara contra
  `due_time` (INIT-4 C2, opt-in). Si ninguna WO completada trae `due_time` ->
  `available=False` (N/A), igual que nivel de servicio en modo Stochastic.
  Cableado en las 4 capas: metadata `SIMULATION_START` del `.jsonl`
  (`sla_summary`), 3 endpoints de `server.py` (`/api/snapshot`, `/api/state`,
  `/api/metrics`), KPI "SLA" en la barra de metricas del visor
  (`static/app.js`), hoja Excel nueva "Cumplimiento SLA" (`exporter_v2.py`,
  mismo patron que "Nivel de servicio"). Cambio de metadata en el `.jsonl`
  (nueva clave) -- verificado que los eventos son byte-identicos (sha256
  sin la linea 1 identico antes/despues, solo +144 bytes del campo nuevo);
  baseline actualizado con `--update-baseline --yes`. 8 tests nuevos
  (`tests/unit/test_sla_summary.py`: a tiempo, vencido, multi-WO usa MAX
  tiempo_fin, borde exacto, mezcla, sin due_time, sin WOs, almacen None).
  Validado end-to-end: corrida real con `due_time=1s` detecto correctamente
  "50% a tiempo (1 de 2 pedidos vencidos)". Suite: 112 passed.

## 2026-07-05 (cont. 5)

- **Eliminacion de `_legacy/web_dashboard/`.** A pedido del Director: auditar
  si valia la pena rescatar alguna idea antes de descartar. Comparacion
  exhaustiva (README, HTML, JS, CSS, servidor) contra el viewer web vigente
  (`web_prototype/static/`) confirmo que el viewer actual es una evolucion
  directa de este codigo, no algo distinto: mismas 18 columnas de la tabla
  de WorkOrders (el viewer actual tiene 2 mas: `qty_requested`/`qty_picked`),
  mismos codigos de color hex exactos por estado (`#FFC107`/`#007BFF`/
  `#28A745`), mismo sistema de sorting por click, mismo scrubber+playback
  (mas desarrollado, integrado con el mapa 2D). El backend estaba ademas
  roto (ruta de replay hardcodeada e inexistente). Nada que rescatar ->
  eliminado (no archivado de nuevo, ya estaba en `_legacy/` desde
  2026-05-31). Referencias actualizadas en `CLAUDE.md`, `README.md`,
  `_legacy/README.md`, `docs/BACKLOG.md`, `docs/STATE.md`.

## 2026-07-05 (cont. 4)

- **INIT-6 — UI web para configurar staging por destino + capacidad de
  camion.** Auditoria (a pedido del Director) encontro 2 huecos reales: la
  UI no tenia forma de editar `destino_staging_map` (INIT-6 Opcion B, sin
  riesgo de perdida de datos -- `save_config` hace merge y preserva claves
  que la UI no gestiona, pero tampoco era EDITABLE desde el navegador) ni
  `outbound.truck_capacity` (ya se guardaba/preservaba, pero sin campo para
  cambiarlo). Se agrego: editor de filas destino->zona (tab "Outbound
  Staging", mismo patron visual que "Prioridades de Work Area" de
  fleet-manager) + campo `truck-capacity` junto a `truck-interval` (visible
  solo con outbound activo). **Guia sutil en la UI** (a pedido del Director,
  "profesional, sin ambiguedad, sin manual gigante"): se identifico que el
  patron ya existia parcialmente (`help-text` por campo) y se formalizo en 2
  niveles -- `.tab-intro` (1 parrafo corto arriba de cada pestaña, el "por
  que" general, nuevo) + `.description-text` (contexto por card, ya
  existia) + `.help-text` (detalle por campo, ya existia). Aplicado a la
  pestaña Staging explicando la precedencia real (zona explicita en el
  archivo > destino mapeado > reparto aleatorio). Validado en navegador real
  (Preview): agregar/quitar filas, guardar y verificar el round-trip completo
  en `config.json` (incluyo confirmar que `save_config` no descarta la clave
  nueva). `config.json` restaurado a su estado original tras la prueba (no
  se dejo data de prueba commiteada). Suite 104 passed, gate PASS sin cambio
  de baseline (solo archivos estaticos web).

## 2026-07-05 (cont. 3)

- **INIT-6 (Opciones A + B) — staging multi-destino por ruta.** RCA en codigo
  (no supuesto) revelo que ya existian 7 zonas fisicas reales de staging
  (`Warehouse_Logic.xlsx`, hoja `OutboundStaging`) e infraestructura parcial
  (`ParsedOrder.staging_id`), pero el config canonico manda 100% a una sola
  zona, y el hallazgo mas importante: `OutboundProcess` tomaba pallets FIFO
  de una cola GLOBAL sin filtrar por `staging_id`, mezclando pedidos de
  zonas/rutas distintas en un mismo camion -- el eslabon perdido real.
  **Opcion A**: `OutboundProcess.run()` ahora sirve una sola zona por camion
  (la del pallet mas antiguo en espera); sin inanicion, sin cambio al
  baseline (outbound esta deshabilitado en el canonico). **Opcion B**: campo
  `destino` opcional en pedidos (JSON/CSV) + `destino_staging_map` en config
  (mismo patron que `work_area_equipment`) resuelto via nuevo
  `AlmacenMejorado._resolver_staging_id()` (precedencia: staging_id explicito
  > destino mapeado > fallback aleatorio, sin regresion). Opcion C
  (clustering geografico automatico) diferida -- requiere datos de
  geolocalizacion de clientes inexistentes hoy. 9 tests nuevos + 3 de
  validacion web. Suite: 104 passed. Gate PASS sin cambio de baseline (ningun
  cambio toca el escenario canonico, que tiene outbound deshabilitado).

## 2026-07-05 (cont. 2)

- **INIT-3 v2 — UI web del optimizador + fix de bug de concurrencia real
  encontrado en el camino.** Nuevo tab "Optimizacion" en el configurador web
  (`web_prototype/static/web_configurator/`): inputs (trials, jobs, costos),
  boton Iniciar/Detener, panel de progreso con polling cada 3s
  (`/api/optimization/status`), recupera un estudio en curso si la pagina se
  recarga. **Bug real encontrado y corregido**: `study.enqueue_trial()`
  (warm-start) + `study.optimize(n_jobs>1)` provoca una carrera de Optuna --
  dos workers toman el mismo trial encolado y le asignan el mismo
  `trial.number`, perdiendo un trial silenciosamente (reproducido de forma
  aislada y confirmado: con n_trials=2/n_jobs=2 solo se completaba 1 trial).
  Preexistente en `optimizer.py` desde su creacion, nunca antes expuesto
  porque nadie habia corrido `n_jobs>1` -- el panel web lo dispara con su
  default (`n_jobs=2`). Fix: `SimulationOptimizer.optimize()` consume el
  warm-start en serie (n_jobs=1, n_trials=1) ANTES de arrancar el resto en
  paralelo. Ademas: `OptimizationRunner.status()` capturaba solo `KeyError`
  para "estudio no existe todavia"; una consulta de status justo despues de
  `start()` puede chocar con la migracion Alembic del subprocess recien
  lanzado (`IntegrityError` de sqlalchemy) -- ahora se captura como
  transitorio. Validado: CLI (n_trials=2/4, n_jobs=2/3, sin perdida de
  trials) + flujo real via navegador (3/3 trials completados, antes se
  perdia 1). 2 tests nuevos de regresion (orquestacion Optuna con objective
  mockeado, sin correr sim real). Suite: 92 passed. Gate PASS sin cambio de
  baseline (no toca el motor).

## 2026-07-05 (cont.)

- **MEJ-2 v2** — `export_optimization_metrics()` ahora incluye `fill_rate_pct`
  y `service_level` (mismo patron/fuente que INIT-5:
  `build_service_level_summary()`). En modo Stochastic (default de
  `config.json`) es `None`/N/A -- consistente con como ya se comporta en
  visor/API/Excel, no es un caso especial nuevo. `experiment_runner.py`
  filtra los `None` (`_collect_values`) en vez de tratarlos como 0.0. No toca
  el `.jsonl` (metrica en archivo separado) -- gate PASS sin cambio de
  baseline. Probado en ambos modos (Stochastic -> N/A; Deterministic con
  `layouts/Orders Test.json` -> 100.0%). 2 tests nuevos, suite 90 passed.

## 2026-07-05

- **INIT-3** (`3cf359e`) — RCA revelo que el desalineamiento motor-optimizador
  del backlog ya no existia (nombres de estrategia correctos, fallback de
  flota vivo). Se amplio el espacio de busqueda (`max_wos_por_tour`,
  `radio_cercania` condicional) y se expuso en la web (`optimization_runner.py`
  + 3 endpoints, fire-and-forget con polling via BD Optuna). Sin cambio al motor.
- **INIT-1** (`be29590`) — RCA redujo el alcance real: el modo por archivo ya
  usaba ubicacion real (Allocation Layer V12.1); el bug vivia solo en
  `StochasticOrderStrategy` (SKU y ubicacion elegidos sin relacion). Fix:
  indice `points_by_sku` sobre `sku_initial`. Baseline actualizado
  (`5f1f4adc...`, 4.919.513 bytes, -3.9%; makespan intacto).
- **Fix WOs sobredimensionadas** (`bac6606`) — `_validar_y_ajustar_cantidad`
  entraba en bucle infinito si `sku.volumen > max_capacity`. Guard temprano
  devuelve `[]` (backorder implicito) en vez de colgarse. Sin cambio al
  baseline (el escenario canonico no dispara el path).
- **MEJ-2 v1** (`6624630`) — `scripts/experiment_runner.py`: N replicas +
  IC95%, comparacion A/B con t-test pareado (`scipy`). KPIs v1 = los que ya
  exporta `export_optimization_metrics`; v2 (nivel de servicio) diferido.
- **Merge MEJ-3+MEJ-4 a main** (`3cf359e`..`82f1487` ff) — autorizado por el
  Director tras CI verde.
- **Reestructuracion de documentacion** — ver seccion "Meta" mas abajo.

## 2026-07-04

- **MEJ-4** (`d1fec07`) — anti-colisiones completo: dwell reservado al
  planificar (picking/descarga/destino-con-permanencia), planner reescrito
  estilo SIPP (0 fallos, 0.7ms/plan), fallback visible, clearance 0.05,
  parking disperso. Co-ocupaciones 28->9. Baseline `c6f129ef...`.
  **Hallazgo:** makespan +55% (2011->3121s) es la cola REAL del staging unico
  (antes 4 agentes superpuestos, fisica imposible). Redefinido 2026-07-05 como
  **INIT-6** (staging debe consolidar por ruta/destino, no un unico punto) —
  ver BACKLOG.md. Plan: `docs/antiguos/PLAN_MEJORA_4_ANTICOLISIONES.md`.
- **MEJ-3** (`e4db0ab`) — `src/core/config_schema.py` (pydantic, unico,
  validacion-only). Purga de 10 claves muertas + 9 subclaves F3 de congestion
  + 2 controles UI sin efecto (capacidad_carro, map_scale). Baseline `662ed5e3...`.
- **MEJ-1** (`6b0b438`..`093b8c9`, en main) — suite pytest (`tests/`, ~73
  tests) + `scripts/regression_gate.py` (byte-identico modulo EOL) + CI
  GitHub Actions verde. Primera red de seguridad automatizada del proyecto.
  Plan: `docs/antiguos/PLAN_MEJORA_1_RED_SEGURIDAD.md`.

## 2026-06-29

- **INIT-4** (`91dd6c0`, `c27dacb`, `fd0a41d`) — prioridad/SLA/olas + tiempos
  de pick escalables, 3 fases opt-in con gate byte-identico. C1 tiempo por
  cantidad/volumen; C2 prioridad "fuerte limpia" (Opcion C del Director); C3
  olas por release diferido. Diferido: KPI de SLA vencido (INIT-4b, pendiente).
  Plan: `docs/antiguos/PLAN_INIT4.md` (o `docs/PLAN_INIT4.md` si aun no se movio).

## 2026-06-27

- **Logging refactor** (`b990964`) — ~186 `print()` -> logging por nivel en
  hot-path (dispatcher, operators, event_generator).
- **WAREHOUSE_SEED** (`413888c`) — semilla determinista via env var. Gate
  byte-identico base (`a4ae8d4e...`, 5.379.372 bytes).
- **Template Method** (`41ddc22`) — `BaseOperator.agent_process()` + hook
  `_do_picking_at()` por subclase. -296 lineas en operators.py (-16.7%).
- **BK-05** (`f3a3ec5`) — botones stub E6/E7 eliminados (sin backend real).

## 2026-06-21 / 2026-06-20

- **INIT-5** (`8cc7f8d`) — nivel de servicio / backorders expuestos en visor,
  API y Excel. Fuente: `core/replay_utils.build_service_level_summary()`.
- **BK-04 + QA-1/2/3** (`1bb24a3`, `e50b924`, `e2c6293`, `19e8829`) — flota por
  defecto sin `work_area` causaba outbound colgado (camiones vacios
  indefinidamente). Fix preventivo (validacion bloqueante + flota real +
  indicador UI) + hardening QA (mapa explicito `work_area_equipment`).

## 2026-06-14 / 2026-06-15

- **BK-01** — estrategia "Cercania" + `radio_cercania` expuestos en UI.
  Incluye fix H-5 (alias "Ejecucion de Plan") y H-6 (radio blando, evita
  deadlock).
- **BK-03 descartado** — greedy nearest-neighbor evaluado con evidencia
  (N=3): -1.54% distancia/WO, dentro del ruido estadistico. Flag
  `cercania_tour_mode` default "cost".

## Anterior a 2026-06-14

Ver `git log --oneline` para el detalle completo (Allocation Layer V12.1,
migracion V11->V12, arquitectura headless, eliminacion de live simulation).
Documentos historicos de esas fases en `docs/antiguos/`.

---

## Meta: reestructuracion de la documentacion (2026-07-05)

Con este archivo se separa "estado actual" (`docs/STATE.md`, se REESCRIBE
entero cada sesion, nunca acumula) de "historial" (este CHANGELOG, append-only,
terso) de "pendientes" (`docs/BACKLOG.md`, recortado a solo lo abierto) de
"identidad/reglas/arquitectura" (`CLAUDE.md`, estable, ya no carga estado).
Razon completa y estructura objetivo: ver `docs/META_DOCUMENTACION.md`.
