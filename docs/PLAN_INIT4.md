# PLAN INIT-4 — Prioridad de pedidos / SLA / Olas + Tiempos de pick realistas

> Documento vivo. Plan de implementacion (Fase A) + Plan de pruebas (Fase B) +
> checklist de progreso (Fase C). Rama: `feature/allocation-layer-v12.1`.
> Creado: 2026-06-27. Autor: Cerebellum.
>
> **Ley #1 (CEREBELLUM):** este plan se aprueba ANTES de codear. Las decisiones de
> diseno abiertas (seccion 2) requieren OK del Director antes de Fase C.

---

## 0. ESTADO Y CONTEXTO

INIT-4 ataca dos limitaciones reales del simulador, confirmadas por lectura del codigo:

1. **Sin prioridad de pedido.** `WorkOrder` no tiene `priority`/`due_time`. La unica
   "prioridad" es de ZONA (el operario atiende primero su area de mayor prioridad).
   Un pedido urgente no puede adelantarse a uno normal.
2. **Tiempo de pick fijo.** Recoger 1 unidad tarda lo mismo que 200. El tiempo de
   recogida es una constante (`picking_time` o `discharge_time`), no escala con cantidad.

A esto se suma la pieza nueva pedida por el Director:

3. **Sin olas (waves).** No se pueden agrupar pedidos en tandas (p.ej. por horario de
   camion) y liberarlos en orden.

### Hallazgos del codigo (verificados, no asumidos)

| Que | Donde | Realidad actual |
|-----|-------|-----------------|
| Objeto pedido-tarea | `warehouse.py:25` `WorkOrder.__init__` | Campos: id, order_id, tour_id, sku, cantidad, ubicacion, work_area, pick_sequence, staging_id, qty_requested/allocated, is_partial, location_id. **NO priority/due/wave.** |
| "Prioridad" en eventos | `dispatcher.py` (4x), `operators.py` (3x) | `getattr(wo,'priority',99)` — solo para el `.jsonl`; siempre 99. |
| Prioridad real de despacho | `dispatcher.py:406` `_filtrar_por_area_prioridad` | Por `operator.get_priority_for_work_area(area)`. Es prioridad de ZONA, no de pedido. |
| Orden de candidatos | `dispatcher.py:325/368` | 1) filtro area-prioridad del operario; 2) primera WO por costo (Opt Global) o menor `pick_sequence` (Ejec Plan); 3) doble barrido por `pick_sequence`. |
| Cola de WOs | `warehouse.py` `work_orders_pendientes` | Lista; las estrategias la filtran/ordenan. Orden de insercion = orden del archivo / generacion. |
| Tiempo de pick (Ground) | `operators.py:1142` | `picking_duration = picking_time if not None else discharge_time`. FIJO. |
| Tiempo de pick (Forklift) | `operators.py:~800` (`_do_picking_at`) | `2*lift_time + picking_duration`. FIJO (salvo lift). |
| Parametros de tiempo | `config.json["tiempos"]` | `tiempo_picking_por_linea: null`, `tiempo_horquilla: 2`, `time_per_cell: 0.1`. `discharge_time` <- `tiempo_descarga_por_tarea`. |
| Generacion de ordenes | `order_strategies.py` | `OrderItem`/`ParsedOrder` (dataclasses, l.22-35). JSON `orders[].items[]`. Modo default = estocastico. |
| Olas / release diferido | — | No existe. `OutboundProcess` (outbound.py:230) usa `truck_interval`; modela camiones, no liberacion de WOs. |

### Principio rector de NO-REGRESION

**Con INIT-4 "apagado" (defaults neutros), una corrida con `WAREHOUSE_SEED=42` debe
producir el `.jsonl` byte-identico al baseline** (`a4ae8d4e9f7dd444...`, 5.379.372 bytes).
Esto se logra haciendo cada feature OPT-IN: sin prioridades en los datos, sin olas
configuradas y con los parametros de tiempo en `null/0`, el motor se comporta
EXACTAMENTE como hoy. Es el criterio de aceptacion mas fuerte (prueba REG-1).

---

## 1. ALCANCE Y SUBDIVISION EN FASES

| Fase | Area | Entregable | Riesgo de regresion |
|------|------|-----------|---------------------|
| **C1** | Tiempos de pick realistas | Tiempo = base + por_unidad*cant (o por volumen) | BAJO (aislado en operators) |
| **C2** | Prioridad de pedido / SLA | Campo en WorkOrder + orden en dispatcher | MEDIO (toca seleccion de candidatos) |
| **C3** | Olas (waves) | release_time por ola; WO no elegible hasta su hora | MEDIO (toca elegibilidad de WOs) |

Orden elegido a proposito: **C1 primero** (el mas aislado y el de gate byte-identico
mas facil de razonar), luego C2 (prioridad), luego C3 (olas, que se apoya en C2).

---

## 2. DECISIONES DE DISENO (RESUELTAS — OK del Director 2026-06-27)

> El Director aprobo las 4 recomendaciones (D1-A, D2-A, D3-A) y autorizo avanzar
> C1->C2->C3 seguido, validando REG-1 (gate byte-identico) al cierre de cada fase.
> Resumen: prioridad/SLA desde el archivo de ordenes; prioridad DENTRO de la zona
> (no cruza de area); olas por release diferido (no tocan outbound).

### D1 — De donde sale la prioridad / SLA de un pedido
- **Opcion A (recomendada):** campo opcional `priority` (int; 1 = mas urgente) y/o
  `due_time` (segundos de sim) en el JSON/CSV de ordenes, por pedido. Es la fuente
  natural: un pedido trae su urgencia. En modo estocastico, opcionalmente generar
  prioridad aleatoria segun una distribucion configurable para que el feature se vea
  sin archivo determinista.
- **Opcion B:** reglas globales en `config.json` (p.ej. "SKUs del area X son urgentes").
  Menos expresivo; mezcla politica con datos.
- **Recomendacion:** A. Prioridad y due_time en el archivo de ordenes; default neutro
  (todas iguales) si el campo no esta -> no-regresion.

### D2 — Como se combina la prioridad de pedido con zona y cercania
Hoy el orden es: `area-prioridad-operario` -> `costo / pick_sequence`.
- **Opcion A (recomendada):** la prioridad de pedido entra como **primer criterio de
  desempate DENTRO de los candidatos ya filtrados por area** (no rompe el modelo de
  zonas). Es decir: filtro de area -> ordenar por (prioridad_pedido ASC, luego costo/seq).
  Asi un urgente del area del operario se adelanta, pero no se viola la asignacion por zona.
- **Opcion B:** la prioridad de pedido manda por encima del area (un urgente de otra
  zona "jala" al operario). Mas potente pero rompe el modelo actual de zonas y arriesga
  thrashing. No recomendado para el primer corte.
- **Recomendacion:** A, y ademas **opt-in** via flag `priority_dispatch_enabled` (default
  False) para garantizar el gate byte-identico cuando esta apagado.
- **Empates:** a igual prioridad de pedido, se mantiene el criterio actual (costo o
  pick_sequence). A igual prioridad y costo, desempata por `order_id` (estable/determinista).

### D3 — Modelo de olas (waves)
- **Opcion A (recomendada):** cada ola tiene un `release_time` (segundos). Una WO de la
  ola N no es ELEGIBLE para el dispatcher hasta que `env.now >= release_time(N)`. Es un
  filtro de elegibilidad, no toca outbound. Las olas se definen en config o en el archivo
  de ordenes (campo `wave` por pedido + tabla de release_times).
- **Opcion B:** integrar con `OutboundProcess`/`truck_interval` (una ola por camion).
  Acopla olas con la salida fisica; mas realista pero mas invasivo.
- **Recomendacion:** A para el primer corte (aislado, testeable, no toca outbound).
  Dejar B documentado como evolucion futura.

### D4 — Formula del tiempo de pick
- **Recomendada:** `t_pick = pick_base + pick_por_unidad * cantidad` (lineal en cantidad),
  con variante opcional por volumen `+ pick_por_volumen * volumen`. Forklift conserva
  `2*lift_time` aparte.
- **Defaults de no-regresion:** `pick_base = null`, `pick_por_unidad = 0`,
  `pick_por_volumen = 0`. Con esos valores, `t_pick` cae al comportamiento actual
  (`picking_time` o `discharge_time`). Solo cuando el Director ponga numeros, escala.
- **Cota inferior:** `t_pick = max(t_pick, minimo_configurable)` para evitar 0 o negativos.

---

## 3. AREA 1 — TIEMPOS DE PICK REALISTAS (Fase C1)

### Diseno
Nuevo bloque en `config.json["tiempos"]`:
```jsonc
"pick_time_model": {
  "base": null,            // si null -> usa picking_time/discharge_time (compat)
  "por_unidad": 0.0,       // segundos extra por unidad pickeada
  "por_volumen": 0.0,      // segundos extra por unidad de volumen
  "minimo": 0.0            // cota inferior del tiempo total de pick
}
```
Formula efectiva (en el operario):
```
if base is None and por_unidad == 0 and por_volumen == 0:
    t = picking_time if picking_time is not None else discharge_time   # << EXACTO como hoy
else:
    b = base if base is not None else (picking_time or discharge_time)
    t = b + por_unidad * wo.cantidad_inicial + por_volumen * wo.calcular_volumen_restante()
    t = max(t, minimo)
```

### Archivos a tocar
- `src/subsystems/simulation/operators.py`:
  - `BaseOperator.__init__`: leer el bloque `pick_time_model` de `config["tiempos"]` y
    guardar los 4 params (con defaults neutros).
  - Helper `BaseOperator._compute_pick_time(wo)` con la formula de arriba.
  - `GroundOperator._do_picking_at` (l.1142): reemplazar `picking_duration = ...` por
    `picking_duration = self._compute_pick_time(wo)`.
  - `Forklift._do_picking_at`: idem para su `picking_duration` (el `2*lift_time` queda igual).
- `web_prototype/config_manager.py`: validacion de los 4 campos (floats >= 0; base puede ser null).
- (Opcional, Fase posterior) configurador web: card "Tiempos" con los 4 inputs.

### Pasos numerados
1. Anadir `pick_time_model` con defaults neutros a `config.json` y a `_get_default_config()`.
2. Leer params en `BaseOperator.__init__`.
3. Implementar `_compute_pick_time(wo)` (con la rama de compat exacta).
4. Cablear en ambos `_do_picking_at`.
5. Validar en `config_manager.py`.
6. Gate byte-identico (REG-1) con params neutros.
7. Prueba CAL-PICK-* (seccion Fase B) con params activos.

### Riesgos y no-regresion
- **Riesgo:** cambiar el default rompe el gate. **Mitigacion:** la rama de compat
  (`base None y por_unidad 0 y por_volumen 0`) devuelve el valor IDENTICO actual.
- **Riesgo:** Forklift duplica logica. **Mitigacion:** `_compute_pick_time` vive en
  `BaseOperator`; ambas subclases lo llaman.

---

## 4. AREA 2 — PRIORIDAD DE PEDIDO / SLA (Fase C2)

### Diseno
- `OrderItem`/`ParsedOrder` (dataclasses) ganan `priority: Optional[int] = None` y
  `due_time: Optional[float] = None`. El parser JSON/CSV los lee si existen.
- `WorkOrder.__init__` recibe `priority` y `due_time` (default None). Se propaga al crear
  WOs en `order_strategies.generate_work_orders` (ambos modos).
- Los 7 `getattr(wo,'priority',99)` siguen funcionando: si la WO trae priority real, lo
  emiten; si no, 99 (sin cambio de comportamiento en eventos).
- **Despacho (opt-in):** nuevo flag `priority_dispatch_enabled` (config, default False).
  Cuando True, en `_estrategia_*` se ordena la lista de candidatos por
  `(priority ASC, criterio_actual)` ANTES de aplicar costo/pick_sequence. Cuando False,
  el comportamiento es identico al actual.
- **SLA/due_time:** primer corte = solo informativo + criterio de desempate secundario
  (a igual priority, menor due_time primero). El "incumplimiento de SLA" (pedidos que
  pasan su due_time) se MIDE y reporta, no se fuerza. Util como KPI.

### Combinacion con zona/cercania (decision D2-A)
```
candidatos = filtrar_por_area_prioridad(operator, compatibles)   # << intacto
if priority_dispatch_enabled:
    candidatos = sorted(candidatos, key=lambda wo: (
        wo.priority if wo.priority is not None else 99,
        wo.due_time if wo.due_time is not None else inf,
        # luego el criterio existente (costo o pick_sequence) lo aplica la estrategia
    ))
# resto de la estrategia (primera WO por costo/seq, doble barrido) sin cambios
```

### Archivos a tocar
- `order_strategies.py`: dataclasses + parser (`_parse_json`, `_parse_csv`) +
  `generate_work_orders` (pasar priority/due al `WorkOrder(...)`).
- `warehouse.py`: `WorkOrder.__init__` (+ `to_dict`) con `priority`/`due_time`.
- `dispatcher.py`: lectura del flag + reordenamiento en las 4 `_estrategia_*`
  (o en un punto comun antes de devolver candidatos).
- `config.json` + `config_manager.py`: `priority_dispatch_enabled` (bool, default False).
- (Opcional) reporte: contar pedidos que incumplen due_time -> hoja/KPI (reusa el patron
  INIT-5 de `replay_utils`).

### Pasos numerados
1. Extender dataclasses + parser (priority/due_time opcionales).
2. Extender `WorkOrder` (+ `to_dict`).
3. Propagar en `generate_work_orders` (determinista y estocastico).
4. Flag `priority_dispatch_enabled` en config + validacion.
5. Reordenamiento opt-in en dispatcher.
6. Gate byte-identico (REG-1) con flag False y sin priorities.
7. Pruebas PRIO-* (urgentes vs normales, empates, due_time).

### Riesgos y no-regresion
- **Riesgo:** reordenar candidatos cambia el `.jsonl` aun sin priorities. **Mitigacion:**
  el reordenamiento solo corre con el flag True; con None en todas las WOs el sort es
  estable y no altera el orden -> igualmente seguro, pero el flag garantiza el gate.
- **Riesgo:** romper el modelo de zonas. **Mitigacion:** se ordena DENTRO de los
  candidatos ya filtrados por area (D2-A); nunca se cruza de zona.
- **Riesgo:** prioridad de pedido vs prioridad de zona se confunden en logs.
  **Mitigacion:** nombrar el campo de pedido `order_priority` en eventos para distinguir.

---

## 5. AREA 3 — OLAS (WAVES) (Fase C3)

### Diseno (decision D3-A: release diferido)
- Config:
```jsonc
"waves": {
  "enabled": false,
  "release_times": { "1": 0, "2": 300, "3": 600 }   // wave_id -> segundos de sim
}
```
- El pedido trae `wave: <id>` (en JSON/CSV). Se propaga a la WO (`wave_id`).
- **Elegibilidad:** el dispatcher, al armar la lista de candidatos, descarta toda WO
  cuyo `release_time(wave_id) > env.now`. Una WO "duerme" hasta que su ola se libera.
- Con `waves.enabled=False` o sin `wave` en los datos -> todas elegibles desde t=0
  (comportamiento actual).
- **Interaccion con outbound:** ninguna directa. Las olas controlan CUANDO entran las
  WOs al sistema; el outbound sigue despachando pallets por `truck_interval`. Son
  ortogonales (documentado; la opcion B "una ola por camion" queda como futuro).
- **Terminacion:** `simulacion_ha_terminado()` debe considerar olas no liberadas aun
  (si quedan WOs en olas futuras, la sim no termina aunque no haya candidatos AHORA).
  Punto critico de no-regresion: revisar el predicado de fin.

### Archivos a tocar
- `order_strategies.py`: parser de `wave` + propagacion a WorkOrder.
- `warehouse.py`: `WorkOrder.wave_id`; ayudante `_wo_es_elegible(wo, ahora)` segun
  release_times; ajuste de `simulacion_ha_terminado()` para olas pendientes.
- `dispatcher.py`: filtrar candidatos por elegibilidad de ola.
- `config.json` + `config_manager.py`: bloque `waves`.

### Pasos numerados
1. Bloque `waves` en config + validacion (release_times: dict id->float >= 0).
2. `wave` en dataclasses/parser + `WorkOrder.wave_id`.
3. Filtro de elegibilidad en dispatcher.
4. Ajuste de `simulacion_ha_terminado()` (no terminar con olas futuras pendientes).
5. Gate byte-identico (REG-1) con `waves.enabled=False`.
6. Pruebas WAVE-* (olas en orden, vacias, solapadas, terminacion).

### Riesgos y no-regresion
- **Riesgo ALTO:** romper la deteccion de fin de simulacion -> sim cuelga o termina
  antes. **Mitigacion:** test WAVE-TERM dedicado; con `enabled=False` el predicado es
  identico al actual (cero olas pendientes).
- **Riesgo:** deadlock si una ola nunca se libera (release_time inalcanzable).
  **Mitigacion:** validar que todo release_time sea finito; WARN si una ola queda sin
  liberar al final.

---

## 6. FASE B — PLAN DE PRUEBAS

> Principio: cada caso con su resultado esperado. Donde aplique, usar `WAREHOUSE_SEED=42`.
> "Gate byte-identico" = SHA256 del `.jsonl` == baseline `a4ae8d4e9f7dd444...`.

### Suite REG — No-regresion (la mas importante)
| ID | Caso | Esperado |
|----|------|----------|
| REG-1 | Corrida con INIT-4 totalmente apagado (sin priorities, `priority_dispatch_enabled=False`, `waves.enabled=False`, `pick_time_model` neutro), `WAREHOUSE_SEED=42` | `.jsonl` byte-identico al baseline |
| REG-2 | Corrida estocastica default (sin tocar config) | KPIs y conteos identicos a pre-INIT-4 |
| REG-3 | Las 4 estrategias de despacho con flags apagados | Mismo comportamiento que hoy |

### Suite CAL-PICK — Tiempos de pick
| ID | Caso | Esperado |
|----|------|----------|
| PICK-1 | `pick_time_model` neutro | t_pick == picking_time/discharge_time (igual que hoy) |
| PICK-2 | `por_unidad=0.5`, WO de 1 vs 200 uds | t(200) = t(1) + 0.5*199; la grande tarda mas |
| PICK-3 | `por_volumen` activo | t escala con volumen de la WO |
| PICK-4 | `minimo` mayor que el calculado | t == minimo (cota inferior respetada) |
| PICK-5 | cantidad = 0 (WO degenerada) | t == base/minimo, sin error ni timeout negativo |
| PICK-6 | Forklift con params activos | t = 2*lift_time + t_pick_escalado |

### Suite PRIO — Prioridad / SLA
| ID | Caso | Esperado |
|----|------|----------|
| PRIO-1 | 1 urgente (prio=1) + 50 normales (prio=5), flag ON | el urgente se pikea antes (dentro de su area) |
| PRIO-2 | Mismo set, flag OFF | comportamiento actual (orden por costo/seq); gate-compat |
| PRIO-3 | Empate de prioridad | desempata por criterio actual (costo/seq), luego order_id; determinista |
| PRIO-4 | Urgente en area distinta a la del operario (D2-A) | NO cruza de zona; el operario respeta su area-prioridad |
| PRIO-5 | due_time imposible (ya vencido al inicio) | se pikea lo antes posible; se MARCA incumplido en reporte, sin crash |
| PRIO-6 | priority ausente en datos | cae a 99; sin cambio de comportamiento |
| PRIO-7 | priority malformada (texto/negativa) | validacion: warn + fallback a None/99, sin crash |

### Suite WAVE — Olas
| ID | Caso | Esperado |
|----|------|----------|
| WAVE-1 | 3 olas con release 0/300/600 | WOs de ola 2 no se tocan antes de t=300; ola 3 antes de t=600 |
| WAVE-2 | `waves.enabled=False` | todas elegibles desde t=0 (gate-compat) |
| WAVE-3 | Ola vacia (id sin pedidos) | sin efecto, sin crash |
| WAVE-4 | Olas con release solapado (mismo t) | se liberan juntas; orden interno por prioridad/seq |
| WAVE-5 | Ola con release inalcanzable (> fin natural) | WARN; sus WOs quedan sin pikear; sim NO cuelga |
| WAVE-TERM | Terminacion con olas futuras pendientes | sim no termina hasta liberar/agotar olas; sin hang infinito |

### Suite INT — Interaccion entre features y subsistemas
| ID | Caso | Esperado |
|----|------|----------|
| INT-1 | Prioridad + olas juntas | dentro de cada ola liberada, manda la prioridad |
| INT-2 | Prioridad + outbound activo | el muelle despacha normal; prioridad no rompe pallets/trucks |
| INT-3 | Olas + outbound | ortogonales; trucks por `truck_interval`, WOs por release_time |
| INT-4 | Tiempos de pick + cantidades grandes + capacidad | WOs sobredimensionadas siguen su camino actual (ver backlog) sin doble fallo |
| INT-5 | Las 4 estrategias x (flag prio ON/OFF) | ninguna estrategia crashea; orden coherente |

### Casos borde transversales
- Cantidad 0 / negativa, priority 0 / negativa, due_time 0, wave inexistente referenciada,
  archivo de ordenes sin `orders`, JSON con campos extra ignorados, CSV sin columnas nuevas.
- Todos: validacion defensiva (warn + fallback), nunca crash, nunca `UnicodeEncodeError`
  (Ley #4: ASCII en logs).

---

## 7. CHECKLIST DE PROGRESO (Fase C)

> Se actualiza a medida que se avanza. Cada hito: commit + push + sync main + actualizar
> este checklist, BACKLOG.md, HANDOFF.md y (si cambia el estado) CLAUDE.md.

### C1 — Tiempos de pick — COMPLETADO 2026-06-29
- [N/A] `pick_time_model` en config.json canonico -> DECISION: NO se toca el config
      canonico (el .jsonl serializa el config en SIMULATION_START; anadir el bloque
      cambiaria el SHA solo por metadata). El bloque es OPCIONAL; el motor lo lee con
      defaults neutros. Se prueba con config separado.
- [x] Lectura en `BaseOperator.__init__` (operators.py:112-126)
- [x] `_compute_pick_time(wo)` con rama de compat exacta (operators.py:129-153)
- [x] Cableado en ambos `_do_picking_at` (Ground + Forklift)
- [x] Validacion en config_manager.py (bloque pick_time_model opcional)
- [x] REG-1 (gate byte-identico) PASA -> SHA a4ae8d4e..., 5.379.372 bytes
- [x] PICK-1..6 PASAN (test unitario del metodo real, scratchpad/test_pick_time.py)
- [ ] E2E con config activo (en curso) + Commit + push + sync main

### C2 — Prioridad / SLA
- [ ] Dataclasses + parser (priority/due_time)
- [ ] `WorkOrder` extendida (+ to_dict)
- [ ] Propagacion en generate_work_orders (ambos modos)
- [ ] Flag `priority_dispatch_enabled` + validacion
- [ ] Reordenamiento opt-in en dispatcher
- [ ] REG-1 con flag OFF PASA
- [ ] PRIO-1..7 PASAN
- [ ] (Opcional) KPI de incumplimiento SLA en reporte
- [ ] Commit + push + sync main

### C3 — Olas
- [ ] Bloque `waves` en config + validacion
- [ ] `wave` en parser + `WorkOrder.wave_id`
- [ ] Filtro de elegibilidad en dispatcher
- [ ] Ajuste de `simulacion_ha_terminado()`
- [ ] REG-1 con waves OFF PASA
- [ ] WAVE-1..5 + WAVE-TERM PASAN
- [ ] INT-1..5 PASAN
- [ ] Commit + push + sync main

### Cierre
- [ ] BACKLOG.md: INIT-4 marcado HECHO
- [ ] HANDOFF.md + CLAUDE.md actualizados
- [ ] docs/PRUEBAS_E2E_SISTEMA.md: anexar suites PRIO/WAVE/CAL-PICK si procede

---

## 8. NOTAS DE NO-ALUCINACION

Verificado por lectura directa (no asumido):
- `WorkOrder.__init__` y `to_dict`: `warehouse.py:25-120`.
- `getattr(wo,'priority',99)`: dispatcher l.1001/1051/1109/1190; operators l.885/1178/1320.
- Tiempo de pick Ground: `operators.py:1142`. Forklift `_do_picking_at` ~l.800.
- Estrategias y filtro de area: `dispatcher.py:270-435`.
- Dataclasses de orden: `order_strategies.py:22-35`; parser JSON l.272-302.
- `truck_interval` / outbound: `outbound.py:230-259`.
- Formato de ordenes: `layouts/Orders Test.json`.
