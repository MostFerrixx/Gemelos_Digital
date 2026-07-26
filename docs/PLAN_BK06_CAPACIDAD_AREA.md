# PLAN BK-06 — Capacidad por area vs. flota heterogenea

**Estado:** F0-F3 IMPLEMENTADAS Y VALIDADAS (2026-07-25). Falta F4 (regenerar
baseline) — requiere OK explicito del Director. Resultados en la seccion 9.
**Rama:** `fix/bk06-capacidad-area`
**Fecha:** 2026-07-25

> **SUPUESTO DE TRABAJO A CONFIRMAR CON EL CLIENTE (2026-07-25).** Todo este
> trabajo asume que el mapa `work_area_equipment` del canonico refleja la
> realidad: `Area_High` y `Area_Special` son atendidas **exclusivamente por
> montacargas**, y `Area_Ground` exclusivamente por operarios terrestres. El
> Director no tiene todavia la lectura del almacen real. Si resultara que esas
> areas son MIXTAS (ambos tipos pueden operar), el mapa esta mal y se corrige
> **en configuracion, sin tocar codigo** (tab Flota) — salvo que se necesite
> expresar varios tipos por area, que hoy el modelo no soporta (ver BK-07 en el
> BACKLOG). Los numeros de la seccion 9 dependen de este supuesto.
**Origen:** hallazgo colateral al intentar BK-05 opcion (b) (migrar el canonico
a `agent_types` explicito). La migracion resulto NO ser cosmetica: destapo un
bug de fondo. Este plan trata el bug; BK-05 queda desacoplado y pendiente.

---

## 1. RESUMEN EJECUTIVO

La clave `capacity` de `agent_types` alimenta DOS cosas independientes que hoy
estan acopladas por accidente:

1. la capacidad fisica del operario (`operators.crear_operarios`), y
2. el divisor que dimensiona las WorkOrders por area
   (`warehouse._validar_y_ajustar_cantidad`).

Con el `config.json` canonico (`agent_types: []`) la via (2) queda CIEGA y
colapsa a un default de 150 para TODAS las areas, incluidas las servidas por
montacargas de capacidad 1000. Resultado: las WOs de `Area_High` y
`Area_Special` se dimensionan a 1/6,6 de la capacidad real del equipo que las
va a mover.

Poblar `agent_types` de forma ingenua (replicando el fallback) NO arregla nada:
rompe la simulacion, porque el dispatcher puede ofrecer una WO dimensionada
para montacargas (1000) a un operario terrestre (150), que no puede levantarla
nunca -> reintento en bucle.

---

## 2. ANALISIS DE CAUSA RAIZ

### 2.1 La via ciega (estado actual del canonico)

`warehouse.py:464-482` deriva las capacidades EXCLUSIVAMENTE de `agent_types`:

```
self.operator_capacities = {}          # {work_area: max_capacity}
for agent_config in agent_types:       # <- canonico: lista VACIA
    ...
self.max_operator_capacity = max([...], default=150)   # <- cae al default
```

Con `agent_types: []` esto produce `operator_capacities = {}` y
`max_operator_capacity = 150`. Luego `_validar_y_ajustar_cantidad`
(`warehouse.py:605-609`) hace:

```
max_capacity = self.operator_capacities.get(work_area, self.max_operator_capacity)
```

Como el dict esta vacio, TODA area cae al fallback 150.

**Evidencia empirica (corrida canonica, WAREHOUSE_SEED=42):**

```
- Capacidades por work area: {}
- Capacidad maxima global: 150
[AGENT] Forklift-01 (Forklift) inicializado - Capacidad: 1000
[AGENT] Forklift-02 (Forklift) inicializado - Capacidad: 1000
[STOCHASTIC] 40 WorkOrders ajustadas por capacidad
```

Los montacargas EXISTEN con capacidad 1000, pero el dimensionado de WOs los
trata como si cargaran 150. Las 40 WOs divididas son, en parte, divisiones
innecesarias.

### 2.2 Por que la migracion ingenua rompe

Al poblar `agent_types` con la replica exacta del fallback (2 GroundOperator
cap 150 + 2 Forklift cap 1000, mismo orden e IDs), `operator_capacities` pasa a
`{'Area_Ground': 150, 'Area_High': 1000, 'Area_Special': 1000}` porque el bucle
toma el **maximo** por area (`warehouse.py:475-476`).

Pero el `work_area_priorities` del GroundOperator en el fallback
(`operators.py:1929`) es:

```
{"Area_Ground": 1, "Area_High": 2, "Area_Special": 3}
```

es decir, **el operario terrestre se declara compatible con Area_High y
Area_Special**. Entonces:

1. `warehouse` dimensiona una WO de `Area_High` hasta 1000 (maximo del area).
2. `dispatcher._seleccionar_primera_wo` (`dispatcher.py:700-713`) busca la mejor
   WO que quepa; si ninguna cabe, **igual devuelve la mejor** ("sera marcada
   como oversized").
3. `dispatcher._construir_tour_por_secuencia` (`dispatcher.py:760-766`) la
   rechaza y aborta con `return []`.
4. El operario terrestre se queda sin tour, reintenta, y vuelve al paso 2.

Las dos funciones se contradicen: una entrega deliberadamente una WO oversized,
la otra la rechaza sin consumirla. Ese es el bucle.

### 2.3 La fuente de verdad que el motor no consulta

`work_area_equipment` (MEJ-3 QA-3 Opcion B) YA declara que tipo de equipo sirve
cada area, y en el canonico dice:

```
"Area_Ground": "GroundOperator", "Area_High": "Forklift", "Area_Special": "Forklift"
```

Ese mapa se consulta en TRES capas — `event_generator._expected_equipment_for_area`,
`config_manager._expected_equipment_for_area` y `fleet-manager.js` — pero
**ninguna de ellas es el hot-path de simulacion**. Ni el dispatcher, ni
`operators`, ni `warehouse` lo miran. El motor decide compatibilidad de area
unicamente por `work_area_priorities`, que puede contradecir el mapa (y lo hace:
el ground se declara apto para Area_High, que el mapa asigna a Forklift).

**Esa es la causa raiz: existe una fuente de verdad declarada para "que equipo
sirve cada area" y el motor no la usa.**

### 2.4 Medicion del impacto (dos corridas, seed 42)

| KPI | Canonico (hoy) | agent_types ingenuo |
|---|---|---|
| WOs completadas | 666 | 626 (-40) |
| Tiempo total simulacion | 7440 s | 7955 s (+6,9%) |
| Tiempo medio de completado | 11,17 s | 12,71 s (+13,8%) |
| `[DISPATCHER ERROR]` | 0 | 9.341 |

Las 9.341 lineas de error corresponden a solo 5 WOs huerfanas (WO-0195,
WO-0265, WO-0377, WO-0416, WO-0462) reintentadas hasta el final de la corrida.
El watchdog de no-progreso NO corta porque los otros operarios si progresan.

---

## 3. ALTERNATIVAS DE SEMANTICA

### Opcion A — `work_area_equipment` manda (RECOMENDADA)

El mapa pasa a ser la fuente de verdad tambien en el motor:

- La capacidad de dimensionado de un area = capacidad de los agentes **del tipo
  asignado a esa area por el mapa**, no el maximo de todos los que la declaran.
- La compatibilidad de un operario con un area se filtra por el mapa: un
  GroundOperator no recibe WOs de un area asignada a Forklift, aunque su
  `work_area_priorities` la liste.

Coherente con QA-3, elimina la contradiccion de raiz, y hace que
`work_area_priorities` signifique solo lo que su nombre dice (orden de
preferencia entre las areas que el agente PUEDE servir), no quien puede servir
que.

**Riesgo:** cambia el reparto de trabajo. Hoy un ground puede tomar WOs de
Area_High si son chicas; con A ya no. Hay que medir si eso desbalancea la flota.

### Opcion B — capacidad por area = MINIMO de los agentes compatibles

Cambiar `max(current_max, capacity)` por `min(...)` en `warehouse.py:475-476`.
Garantiza que toda WO generada quepa en cualquier operario que pueda tomarla:
no hay huerfanas, no hay bucle.

**Contra:** cristaliza el sub-dimensionado. El area seguiria dimensionando a 150
por culpa del ground, desperdiciando el montacargas. Arregla el crash pero no el
bug economico. Es la version "segura y honesta" del comportamiento actual.

### Opcion C — desacoplar las dos capacidades con una clave nueva

Separar "capacidad fisica del agente" de "capacidad de dimensionado por area"
(p. ej. `work_area_capacity` explicito en config).

**Contra:** mas superficie de config, y deja al Director la responsabilidad de
mantener coherentes dos numeros que deberian derivarse solos. Solo tiene sentido
si se quiere modelar un limite operativo distinto del fisico (p. ej. politica de
"no armar pallets de mas de X aunque el equipo pueda").

**Mi recomendacion: Opcion A**, con la Opcion B como red de seguridad dentro de
la misma implementacion (si tras aplicar A un area quedara servida por tipos de
capacidad heterogenea, dimensionar por el minimo de ese conjunto en vez de por
el maximo). Asi el bucle se vuelve estructuralmente imposible.

---

## 4. IMPACTO ESPERADO EN EL BASELINE

**El baseline byte-identico SE ROMPE de forma intencional.** No hay version de
este fix que preserve `2233b3c6...`: el dimensionado de WOs de Area_High y
Area_Special cambia de 150 a 1000, lo que cambia la cantidad de WOs, su volumen
y por lo tanto todos los eventos.

Direccion esperada del cambio (a confirmar empiricamente, NO afirmado):
menos WOs (menos divisiones innecesarias), menos viajes de montacargas, y
mejora de throughput. La magnitud es justamente lo que hay que medir: es el
argumento economico de la iniciativa.

Procedimiento: `--update-baseline --yes` y commitear el baseline JUNTO con el
fix, con los numeros del antes/despues en el mensaje de commit.

---

## 5. PLAN DE IMPLEMENTACION (por fases, cada una con gate)

- **F0 — Instrumentacion sin cambio de comportamiento.** Contar cuantas WOs y
  cuanto volumen hay por area en el canonico, para cuantificar el upside antes
  de tocar la logica. Gate: PASS byte-identico (F0 no cambia el motor).
- **F1 — El motor consulta `work_area_equipment`.** Helper unico compartido
  (evitar una cuarta copia del `_expected_equipment_for_area`); filtrado de
  compatibilidad en el dispatcher por el mapa. Tests unitarios nuevos.
- **F2 — Capacidad de dimensionado derivada del tipo del area** (con el minimo
  como red de seguridad, ver Opcion A). Ajuste de `warehouse.py:464-482`.
- **F3 — Cerrar la contradiccion del dispatcher.** `_seleccionar_primera_wo` no
  debe devolver una WO que `_construir_tour_por_secuencia` va a rechazar. Con
  F1+F2 el caso no deberia ocurrir; igual hay que hacerlo imposible por
  construccion, no por suerte.
- **F4 — Medicion y baseline.** Corrida A/B, tabla de KPIs, regenerar baseline,
  documentar.

---

## 6. VALIDACION

1. `python -m pytest -q` verde tras cada fase (hoy: 193 passed).
2. `python scripts/regression_gate.py`:
   - F0: PASS byte-identico obligatorio.
   - F1-F3: se espera FAIL (cambio intencional); el gate se usa como detector
     de cambio, no como aprobacion.
   - F4: regenerar baseline y volver a PASS.
3. **Criterio de exito duro:** `[DISPATCHER ERROR] ... excede capacidad` debe
   ser CERO en la corrida canonica y en la variante con `agent_types` explicito.
4. **Criterio de no-regresion:** WOs completadas >= 666 y tiempo total <= 7440 s
   (los numeros del canonico actual). Si el fix empeora cualquiera de los dos,
   se para y se reevalua la semantica.
5. Tests nuevos que pinneen: (a) area servida por un solo tipo dimensiona por la
   capacidad de ESE tipo; (b) un GroundOperator nunca recibe WO de un area
   mapeada a Forklift; (c) ninguna WO generada es irrecogible por todos los
   agentes compatibles con su area.

---

## 7. ACTIVOS REUTILIZABLES (de la rama `feat/bk05-agent-types-explicito`,
## ya borrada por vacia)

La rama no llego a tener commits, pero el trabajo exploratorio produjo dos cosas
que valen para F4 y para BK-05, y por eso quedan documentadas aca:

**(a) Generador del config variante.** Script que lee el `config.json` canonico
y le inyecta el `agent_types` explicito que replica EXACTAMENTE el fallback
(mismo orden, mismos IDs, mismas capacidades y prioridades). Reconstruible en 5
minutos con esta especificacion:

```
n_ground = config["num_operarios_terrestres"]   # canonico: 2
n_fork   = config["num_montacargas"]            # canonico: 2
# primero TODOS los ground, luego TODOS los forklift (el orden fija spawn_index)
GroundOperator: capacity 150,  discharge_time 5,
                work_area_priorities {"Area_Ground":1, "Area_High":2, "Area_Special":3}
Forklift:       capacity 1000, discharge_time 5,
                work_area_priorities {"Area_High":1, "Area_Special":2}
```

Sirve como caso de prueba permanente: **tras BK-06, correr el canonico y esta
variante debe dar resultados equivalentes** (misma flota, expresada de dos
formas). Hoy no los da — esa es justamente la prueba de que el bug existe.

**(b) Metodo de medicion A/B sin tocar el canonico.** Dos corridas con
`WAREHOUSE_SEED=42`, una con el config de la raiz y otra con `--config <path>`,
ambas con `--output-metrics`, y comparacion de los JSON resultantes. Es el
procedimiento a usar en F4. Los outputs van al scratchpad, no al repo.

---

## 8. RELACION CON OTRAS INICIATIVAS

- **BK-05** (guard de flota vacia al guardar el canonico desde la UI): queda
  ABIERTO y desacoplado. La opcion (b) original (migrar el canonico a
  `agent_types` explicito) esta BLOQUEADA por BK-06: migrar antes del fix
  degrada la simulacion. La opcion (a) (el validador acepta flota vacia con
  contadores legacy > 0) sigue disponible y no depende de esto.
- **INIT-3 v3** (capacidades por agente en el optimizador): depende de BK-06.
  Meter capacidades en el espacio de busqueda sobre la semantica actual
  generaria trials con flotas heterogeneas y el bucle de WOs huerfanas.

---

## 9. RESULTADOS (F0-F3 ejecutadas, 2026-07-25)

### 9.1 Que se implemento

| Fase | Cambio | Archivos |
|---|---|---|
| F0 | Instrumentacion (sin tocar el motor) | `scripts/bk06_f0_instrumentacion.py` |
| F1 | El mapa manda en el motor + `[WARN]` de config incoherente | `src/core/work_areas.py` (nuevo), `operators.py`, `event_generator.py` |
| F2 | Capacidad por area derivada de la flota real (minimo) + flota configurable | `src/core/fleet.py` (nuevo), `warehouse.py`, `operators.py`, `config_schema.py` |
| F3 | Contrato unico en el dispatcher (no devolver WOs oversized) | `dispatcher.py` |
| -- | 14 tests nuevos | `tests/unit/test_bk06_capacidad_area.py` |

Dos deudas estructurales saldadas de paso:

* **Fuente unica de flota.** `crear_operarios` tenia dos ramas duplicadas
  (agent_types / contadores legacy) con las capacidades **hardcodeadas**
  (150/1000) que `warehouse` no podia ver. Ahora ambos leen
  `core.fleet.resolver_flota`.
* **Capacidades configurables** (principio rector #2): nuevo bloque opt-in
  `fleet_defaults` en config.json (registrado en `config_schema.py`). Ausente =
  defaults historicos, comportamiento intacto.

### 9.2 Numeros (canonico, WAREHOUSE_SEED=42)

| KPI | Canonico (pre-fix) | F1 | F1+F2+F3 |
|---|---|---|---|
| WorkOrders | 666 | 666 | **626** |
| Volumen movido | 21.150 | 21.150 | **21.150** |
| Ordenes | 300 | 300 | **300** |
| Makespan | 7440 s | 9685 s | **8783 s** |
| `[DISPATCHER ERROR]` | 0 | 0 | **0** |

**Las 626 WOs mueven exactamente el mismo volumen (21.150) que las 666
anteriores: son 40 viajes menos, no trabajo perdido.**

### 9.3 El trade-off del makespan (y por que se acepta)

El makespan sube 18,1% respecto al baseline historico. La causa NO es el fix:
es que el baseline **se lograba en parte con asignaciones fisicamente
imposibles** (operarios terrestres bajando mercaderia de racks altos). Al
prohibirlas, los montacargas quedan como cuello de botella real y los
terrestres subutilizados. Decision del Director (2026-07-25): **el realismo
gana**; un KPI logrado con fisica imposible no es una meta legitima
(principio rector #1, `CLAUDE.md` 1.5).

### 9.4 Validacion del diagnostico: dimensionado de flota

Si el cuello de botella son los montacargas, sumar montacargas debe recuperar
el makespan. Se corrio variando SOLO `num_montacargas`:

| Flota (ground+forklift) | WOs | Makespan | vs 7440 s |
|---|---|---|---|
| 2+2 (canonico) | 626 | 8783 s | +18,1% |
| 2+3 | 626 | 6042 s | **-18,8%** |
| 2+4 | 626 | 4844 s | **-34,9%** |
| 2+5 | 626 | 4966 s | -33,3% |

Diagnostico confirmado. Con **un solo montacargas mas**, el modelo realista ya
**supera** el baseline historico. El optimo esta en 2+4; con 2+5 empeora
(congestion), un comportamiento fisicamente sensato que valida de paso la capa
de congestion. **Hallazgo de negocio accionable: la flota 2+2 esta
sub-dimensionada para esta carga.**

### 9.5 Criterios de exito del plan (seccion 6)

| Criterio | Resultado |
|---|---|
| `[DISPATCHER ERROR]` = 0 en canonico | **CUMPLE** (0) |
| `[DISPATCHER ERROR]` = 0 con agent_types explicito | **CUMPLE** (0, antes 9.341) |
| Canonico == agent_types explicito | **CUMPLE** (626 / 8783 s ambos, identico) |
| WOs completadas >= 666 | **NO CUMPLE literalmente** (626) — pero el volumen y las ordenes son identicos: son menos viajes, no menos trabajo. El criterio estaba mal formulado (contaba viajes, no trabajo). |
| Makespan <= 7440 s | **NO CUMPLE** (8783 s) — aceptado explicitamente por el Director: el 7440 no era legitimo. Ver 9.3 y 9.4. |
| Tests que pinneen (a), (b), (c) | **CUMPLE** (14 tests, `test_bk06_capacidad_area.py`) |

### 9.6 Efecto colateral: BK-05 desbloqueado

La prueba de equivalencia (canonico == agent_types explicito) era justamente lo
que fallaba antes. Ahora pasa, asi que **migrar el canonico a `agent_types`
explicito ya es un no-op de comportamiento**: BK-05 opcion (b) deja de estar
bloqueada.
