# BACKLOG — Gemelo Digital de Almacen
# Solo lo PENDIENTE. Lo cerrado vive en docs/CHANGELOG.md (no se repite aca).

Actualizado: 2026-07-11 · Responsable: Cerebellum

*(INIT-7 INBOUND completa F0-F5 el 2026-07-10; INIT-8 TIEMPOS completa F1-F4
el 2026-07-11 -> ambas en CHANGELOG. Auditoria de INIT-8 el 2026-07-11:
hallazgos AUD8-1..4 abajo, documentados sin aplicar por pedido del Director.)*

## Indice (de un vistazo)

| Item | Estado | Prioridad | Esfuerzo | Bloqueo |
|------|--------|-----------|----------|---------|
| AUD8-1 — goal_dwell del tramo->staging ignora el packing (co-ocupaciones) | ABIERTO (auditoria INIT-8) | **Media** | ~30 min | Ninguno |
| AUD8-2 — `distribucion_tipos` es letra muerta (filtro nunca matchea) | ABIERTO (auditoria INIT-8) | Media | ~1-2 h (reconectar a clases INIT-8) | Decision de diseno del Director |
| AUD8-3 — cache `_t_pick_muestreado` sin invalidar en re-pick | ABIERTO (auditoria INIT-8) | Baja | ~20 min | Ninguno |
| AUD8-4 — comentario obsoleto "_compute_pick_time es puro" | ABIERTO (auditoria INIT-8) | Trivial | ~5 min | Ninguno |
| BK-02 — FIFO Estricto en UI | EN REPENSAR | Baja | ~15 min | Diseno pendiente del Director |
| INIT-3 v3 — capacidades por agente en el optimizador | DIFERIDO | Baja | Medio | Ninguno, listo para tomar |
| INIT-6 Opcion C — clustering geografico de destinos | DIFERIDO | Baja | Alto (no estimado) | Requiere datos reales de geolocalizacion de clientes |
| Distribucion real de `outbound_staging_distribution` en config canonico | PENDIENTE DECISION | -- | Trivial (config) | Decision de negocio del Director, no un bug |

---

## Auditoria INIT-8 (2026-07-11) — hallazgos documentados, NO aplicados

Auditoria completa de INIT-8 F1-F4 a pedido del Director (solo documentar).
Base SANA: 189 passed + GATE PASS byte-identico en frio. Verificado ademas:
el modo estocastico (canonico) SI ejercita peso/clase (usa
`almacen.catalogo_skus` reales); el split de capacidad tolera el volumen
real (extra_grande ~75 unidades caen en Forklift cap 1000, guard WH04
cubre el resto); descargas/putaway NO tienen doble-muestreo (guardan la
muestra en variable local); reproducibilidad con variabilidad on OK
(2 corridas seed 42 -> sha identico).

### AUD8-1 — goal_dwell del tramo->staging ignora el packing (MEDIA)

`operators.py:1261`: al navegar al staging para descargar, la permanencia
reservada en el plan espacio-temporal es
`goal_dwell = discharge_time * len(staging_wos)` — SIN el packing por clase
(F4) ni la variabilidad. Pero la descarga REAL usa
`_tiempo_descarga_final = (discharge + pack) muestreado`. Con packing activo
la permanencia real EXCEDE sistematicamente la reservada: el agente ocupa la
celda de staging mas tiempo del que el planner reservo, y otros agentes
rutean a traves creyendola libre.
**Evidencia dura (seed 42, canonico + pack=30 en todas las clases):
co-ocupaciones 8 -> 41 (5x).** `table_overlap_violations=0` en ambos (el
planner es internamente consistente; el problema es ejecucion > reserva).
Solo se manifiesta con packing/variabilidad activos (opt-in; el canonico no
los trae, por eso el gate pasa). Afecta el flujo de descarga CLASICA
(outbound off); el flujo por carriles (outbound on) ya usa `_t_desc` para la
reserva de la celda (linea 994, correcto).
**Fix propuesto (~30 min):** que el goal_dwell del tramo->staging sume el
pack por clase (y una estimacion de la media con variabilidad):
`sum(discharge + _clase_pack(wo) for wo in staging_wos)`. Con var on, usar la
media (pack incluido) es suficiente para la reserva; el desvio por muestra
individual queda como el "estatus de estimacion" ya documentado en el plan F4.
Ojo: NO romper el gate (con pack=0 y var off debe dar `discharge*n` exacto).

### AUD8-2 — `distribucion_tipos` es letra muerta (MEDIA)

`order_strategies.py:209`: el filtro de SKU por tipo de pedido es
`[sku for sku in catalogo if tipo_seleccionado[:3].upper() in sku.id]`.
Para 'pequeno'/'mediano'/'grande' busca 'PEQ'/'MED'/'GRA' dentro de `sku.id`,
pero los SKU se llaman 'SKU001'... => **NUNCA matchea**, siempre cae al
fallback `list(catalogo)` = todos los SKU uniforme. Consecuencia: la
`distribucion_tipos` del canonico (60/30/10) NO tiene efecto, y su campo
`volumen` (5/25/80) es enganoso (el volumen real viene del catalogo desde
INIT-8 F2). PRE-EXISTENTE (no lo introdujo INIT-8), pero INIT-8 lo vuelve
relevante: ahora hay 5 clases de manejo reales que la distribucion de
pedidos DEBERIA respetar para que la mezcla pequeno/pesado/extra_grande sea
controlable. **Oportunidad (~1-2 h, requiere decision del Director):**
reconectar la distribucion de pedidos a `SKU.clase` (INIT-8) en vez del
filtro roto por id; deprecar el campo `volumen` de distribucion_tipos. Es un
cambio de comportamiento del canonico => nueva actualizacion de baseline
intencional. Alternativa minima: documentar en el plan que la mezcla es
uniforme y borrar el filtro muerto.

### AUD8-3 — cache `_t_pick_muestreado` sin invalidar (BAJA)

`operators.py:190-199`: `_tiempo_pick_final` cachea la muestra en la WO
(`wo._t_pick_muestreado`) para que la reserva del planner y el timeout real
usen el MISMO valor (correcto y necesario). Pero la cache NO se invalida: si
el mismo objeto WO se re-pickeara (`picking_executions` puede incrementar en
`_do_picking_at`), devolveria la muestra vieja en vez de una nueva
independiente. Impacto BAJO (el re-pick del mismo objeto es raro; en el flujo
normal `cantidad_restante=0` cierra la WO). Ademas la cache escribe el
atributo en la WO incluso con variabilidad OFF (contaminacion cosmetica, no
observable: to_dict() no lo serializa). **Fix (~20 min):** invalidar la cache
al cerrar el pick (o solo cachear con `var_enabled`), y un test que re-pickee
el mismo objeto. Confirmar que no altera el consumo del RNG en el flujo
normal (gate).

### AUD8-4 — comentario obsoleto (TRIVIAL)

`operators.py:1744` (Forklift `_do_picking_at`): el comentario dice
"_compute_pick_time es puro (sin RNG): calcularlo aqui no altera el
comportamiento". Con F4 el flujo real usa `_tiempo_pick_final` (que SI tiene
RNG cuando variabilidad esta on). El comentario ya aclara el F4 a
continuacion, pero la primera frase quedo enganosa. **Fix (~5 min):**
reescribir para que refleje que la muestra se cachea (por eso la reserva y el
timeout coinciden), sin afirmar pureza.

---

## INIT-6 Opcion C — clustering geografico automatico

**Contexto:** INIT-6 (Opciones A+B, staging por zona real + destino->staging_id)
esta HECHO -- ver `docs/CHANGELOG.md` 2026-07-05. Esto es solo la extension
opcional que quedo afuera.

Clustering geografico automatico de destinos -> staging_id. Requiere:
coordenadas reales de destino por pedido (hoy no existen), algoritmo de
clustering (ej. k-means) corrido al inicio de cada corrida/wave, y decidir si
las 7 zonas fisicas son suficientes o hace falta redefinir el layout. No
estimado -- depende de si el negocio va a tener datos reales de geolocalizacion.

---

## Distribucion real de `outbound_staging_distribution`

Ahora que el camion respeta la zona (INIT-6 Opcion A), tiene sentido repartir
el trafico entre las 7 zonas reales en vez de mandar 100% a la zona 1 (asi
esta el `config.json` canonico hoy). Es una decision de tuning de negocio del
Director, no un bug — cambiarla intencionalmente rompe el baseline byte-identico
y requeriria `--update-baseline --yes`.

---

## BK-02 — FIFO Estricto en UI

**Estado:** EN REPENSAR (nota del Director, 2026-06-15): no exponer todavia.
Hay que redefinir que deberia hacer FIFO operacionalmente antes de mostrarlo
en el configurador. El motor ya lo implementa correctamente
(`dispatcher._estrategia_fifo`, string `"FIFO Estricto"`); es una decision de
diseño de uso, no un problema tecnico.

---

## INIT-3 v3 — capacidades por agente en el optimizador

Unica pieza diferida que queda de INIT-3 (la UI web se completo en v2, ver
CHANGELOG 2026-07-05): **capacidades por tipo de agente en el espacio de
busqueda**. Requiere que el optimizador arme un `agent_types` explicito por
trial en vez de usar el fallback legacy (`num_operarios_terrestres`/
`num_montacargas`), ya que la capacidad esta hardcodeada en el fallback de
`operators.py` (150 ground / 1000 forklift, no leida de config). Cambio de
representacion mas grande, no un fix.

---

*Para retomar cualquier item cerrado, buscar su commit en `docs/CHANGELOG.md`
o `git log --oneline --grep=<ITEM>`.*
