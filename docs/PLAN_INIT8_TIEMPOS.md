# PLAN INIT-8 — TIEMPOS REALISTAS POR PRODUCTO

> Aprobado por el Director el 2026-07-11. Fundamento tecnico: documento del
> Director "Ingenieria de Tiempos y Movimientos en Centros de Distribucion"
> (Google Doc, 2026-07-11) — reporte de estandares MTM/MOST, ergonomia de
> carga, playbooks WMS/LMS y modelado estocastico. Cada parametro calibrado
> cita su fuente.

## Objetivo

Que el simulador distinga fisicamente un refrigerador de una polera: tiempos
de picking/putaway/packing y velocidad de movimiento dependientes de los
atributos reales del producto (volumen, peso, clase de manejo). Hallazgo de
la investigacion (2026-07-11): la DB ya tenia columnas `volume_m3`,
`weight_kg`, `category` pero con datos PLANOS (todos 0.01 m3 / NULL /
GENERAL) — hoy todos los SKUs son identicos para el motor.

## Fases

| Fase | Entrega | Estado |
|---|---|---|
| F1 | Catalogo fisico: hoja `SkuCatalog` (volumen/peso/clase por SKU, sintetico coherente), importer + data_manager + SKU del motor cargan peso/clase (SIN lector aun => gate intacto) | **HECHO 2026-07-11** |
| F2 | Activacion: el motor consume volumen REAL (capacidad/tours) + tiempos por clase y peso (`tiempos.clases_manejo` + `por_kg`) + recargos estilo Blue Yonder. **UNICA actualizacion intencional de baseline de la iniciativa** | **HECHO 2026-07-11** |
| F3 | Velocidad segun carga (curva calibrada) + opcional penalizacion por giro | **HECHO 2026-07-11** (giro DESCARTADO, ver decisiones) |
| F4 | Variabilidad Log-Normal de tiempos (seeded) + packing por clase | pendiente |
| F5 (diferida) | Fatiga dinamica acumulativa (Giacomelli 2026) | no planificada |

## Estrategia de baseline (decidida en F1)

La hoja `SkuCatalog` trae TAMBIEN `volumen_m3` real, pero el importador NO lo
importa en F1 (solo peso y clase, que no tienen lector). Motivo: el volumen
fluye HOY al motor via `SKU.volumen` (capacidad, splits de tours) — importarlo
cambiaria el comportamiento sin modelo de tiempos que lo justifique. En F2 se
importa el volumen + se activan los tiempos por clase JUNTOS => una sola
actualizacion de baseline documentada (mismo patron que INIT-7 F4).

## Tabla de calibracion (fuente: doc del Director, 2026-07-11)

| Parametro | Valor | Fuente |
|---|---|---|
| Manipulacion por caja estandar | 14.2 s/caja | Regresion 337 rutas reales, CD cosmeticos (POMS 2007): T = 801 + 76.4·L + 14.2·C |
| Caja grande/densa de rack medio | 2.16 s extra (60 TMU) | MTM-Logistics (1 TMU = 0.036 s) |
| Fijo por linea visitada | 76.4 s (incluye transito: NO usar directo, el sim ya viaja explicito) | idem POMS |
| Velocidad a pie sin carga | 1.35 m/s | Indian Army 2022 + Adhaye 2023 (coinciden) |
| Velocidad con 22 kg | 1.10 m/s (-18.5%) | Indian Army 2022 |
| Velocidad carga a dos manos | 1.02 m/s | Adhaye 2023 |
| Tope duro con carga ~47 kg | 1.33 m/s maximo | Military Research Lab 2000 |
| Velocidad economica optima | 0.9-1.2 m/s (estable ante carga) | Bastien/Weyand 2005 |
| Transpaleta manual vs electrica | 1.3 vs 2.6 m/s | Consultoria (sintesis del doc) |
| Penalizacion por giro en ruta | +10 s/giro | SAP EWM BRFplus |
| Formula de extraccion | E = X + q·Y (identica a nuestro pick_time_model) | SAP EWM Labor Management |
| Recargos por peso/frio | practica estandar (fatigue factors) | Blue Yonder LMS 2024 |
| Distribucion de tiempos humanos | **Log-Normal** (acotada en 0, cola derecha). RECHAZAR Normal (tiempos negativos) y Triangular (muletilla sin datos) | Law/Simio 2024 + Kostrzewski 2016 |
| Deterministico vs estocastico | promedios deterministas SOBREESTIMAN capacidad y esconden cuellos de botella | Kostrzewski 2016 |

## F1 — Catalogo fisico (contrato)

### Hoja Excel `SkuCatalog` (en `layouts/Warehouse_Logic.xlsx`, opcional)

| Columna | Tipo | Nota |
|---|---|---|
| sku_code | str | debe existir en PickingLocations |
| volumen_m3 | float | REAL desde F1 en la hoja; el importador lo toma recien en F2 |
| peso_kg | float | importado en F1 (sin lector hasta F2) |
| clase_manejo | str | `pequeno` / `mediano` / `voluminoso` / `pesado` / `extra_grande` (a DB columna `category`) |

### Clases de manejo del catalogo sintetico (50 SKUs, determinista)

| Clase | Ejemplo | volumen_m3 | peso_kg | Cuantos | Regla de area |
|---|---|---|---|---|---|
| pequeno | polera, cosmetico | 0.002-0.008 | 0.1-0.8 | 18 | Area_Ground |
| mediano | caja estandar | 0.01-0.04 | 1-8 | 15 | Area_Ground |
| voluminoso | almohadon, lampara | 0.12-0.35 | 4-12 | 8 | preferencia Forklift |
| pesado | sacos, herramienta | 0.03-0.09 | 18-45 | 6 | preferencia Forklift |
| extra_grande | linea blanca | 0.6-1.3 | 50-90 | 3 | Forklift |

Asignacion determinista: los SKUs cuya ubicacion primaria esta en areas de
Forklift (Area_High/Area_Special) reciben las clases pesadas primero; el
resto se reparte pequeno/mediano. Reemplazable por datos reales del negocio
editando la hoja (el contrato no cambia).

### Plomeria F1

- Importer: hoja opcional `SkuCatalog` -> UPDATE de `weight_kg` y `category`
  en `sku_catalog` (volumen_m3 NO en F1, ver estrategia de baseline).
- data_manager: `sku_catalog` dicts exponen `weight_kg` y `category` (DB y
  fallback Excel).
- warehouse.SKU: atributos `peso` y `clase` (sin consumidor en F1).

## Decisiones tecnicas de F2 (2026-07-11)

- **Formula final** (operators._compute_pick_time, INIT-4 extendida):
  `t = (base + por_unidad*qty + por_volumen*vol + por_kg*peso_total)
  * clase.mult + clase.recargo`, piso `minimo`. Rama de COMPAT EXACTA
  intacta: configs/presets viejos sin los bloques -> tiempo historico
  identico (pineado por T820).
- **Calibracion canonica** (anclas del doc del Director):
  `base=10 + por_unidad=2` => ~14 s/caja mediana con qty~2 (POMS 2007:
  14.2 s/caja); `por_kg=0.15` (proxy fatigue-factor Blue Yonder: 85 kg =>
  +12.8 s); recargo voluminoso 3 s (MTM caja grande/densa 2.16 s);
  extra_grande mult 2.2 + recargo 15 s (linea blanca, dos puntos de agarre).
  v1 AJUSTABLE editando config.json (sin codigo).
- **Putaway load** tambien escala por clase (`_putaway_load_time`): pallet
  de linea blanca 37 s vs 10 s plano.
- **Volumen real activo**: importer + fallback Excel toman volumen_m3
  (COALESCE si la celda falta). SKU.volumen ahora discrimina de verdad:
  pequeno=1 unidad de carro, extra_grande=66-75 (carro ground de 150 =>
  max 2 refrigeradores por viaje).
- **Impacto medido (canonico, seed 42):** makespan 3122 -> 5696 s (+82%),
  WOs 602 -> 615 (mas splits por volumen real), throughput 0.193 -> 0.108
  wo/s (-44%). El mundo plano SOBREESTIMABA la capacidad ~2x (confirma
  Kostrzewski 2016). Baseline actualizado: `8f9f78d5...`, 7.161.322 bytes.
- Sin UI en F2: `clases_manejo` se edita en config.json (bloque avanzado);
  evaluar UI si el Director la pide tras F3/F4.

## Decisiones tecnicas de F3 (2026-07-11)

- **Bloque `tiempos.velocidad_por_carga`** (opt-in, default off; NO esta en
  el canonico): `{enabled, reduccion_por_kg: 0.0084, reduccion_max: 0.5,
  aplica_forklift: false}`. Calibracion: Indian Army 2022 (1.35 m/s vacio ->
  1.10 m/s con 22 kg = -18.5% => 0.0084/kg). reduccion_max clampeada a 0.9.
- **factor de TIEMPO** (>= 1.0): `speed` en `_recorrer_tramo` es
  multiplicador de tiempo => factor = 1/(1 - reduccion). Aplicado UNA vez a
  la ENTRADA de `_recorrer_tramo`: el plan espacio-temporal (find_path_st
  recibe el speed efectivo => reservas con duracion real), la ejecucion del
  plan y el fallback estatico quedan CONSISTENTES (cero riesgo de
  co-ocupaciones por desincronizacion).
- **`cargo_peso`**: espejo de cargo_volume en los 11 sitios de mutacion
  (picks Ground/Forklift, 3 rutas de descarga, putaway load/deposito,
  resets de fin de tour y _abort_tour, add/clear_cargo).
- **Forklift exento por default** (`aplica_forklift: false`): la maquina
  carga, no el cuerpo del operario. Activable explicito.
- **OFF = identidad IEEE exacta** (speed * 1.0): gate PASS sin update con el
  baseline de F2 (verificado).
- **Efecto medido** (canonico + flag on, seed 42): makespan 5696 -> 5843 s
  (+2.6%). Modesto porque lo pesado va en Forklift (exento) y los tours mixtos
  promedian; crece con perfiles de pedidos pesados.
- **Penalizacion por giro DESCARTADA**: el valor del doc (+10 s/giro, SAP
  BRFplus) aplica a tramos vehiculares largos de DC real; en nuestra grilla
  de celdas ~1 m un caminante gira constantemente y la penalizacion seria
  absurda. Ademas insertaria dwells no planificados dentro de tramos ya
  reservados por el planner espacio-temporal (riesgo de co-ocupacion). Se
  reevalua solo si algun dia se modelan velocidades vehiculares por tramo.

## Regla de validacion por fase

`python -m pytest -q` verde + `python scripts/regression_gate.py` PASS
(F1, F3, F4 sin update; F2 = LA actualizacion intencional unica) + docs al dia.
