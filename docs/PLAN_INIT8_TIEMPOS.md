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
| F2 | Activacion: el motor consume volumen REAL (capacidad/tours) + tiempos por clase y peso (`tiempos.clases_manejo` + `por_kg`) + recargos estilo Blue Yonder. **UNICA actualizacion intencional de baseline de la iniciativa** | pendiente |
| F3 | Velocidad segun carga (curva calibrada) + opcional penalizacion por giro | pendiente |
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

## Regla de validacion por fase

`python -m pytest -q` verde + `python scripts/regression_gate.py` PASS
(F1, F3, F4 sin update; F2 = LA actualizacion intencional unica) + docs al dia.
