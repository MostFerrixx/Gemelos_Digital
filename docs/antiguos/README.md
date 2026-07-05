# Documentacion archivada (trabajo completado)

Esta carpeta contiene documentos de trabajo que **ya no estan vigentes** porque
el trabajo que describen fue **completado** o **superado por una decision posterior**.
Se conservan por valor historico y trazabilidad. No deben usarse como referencia activa.

---

## Lote 1 — Junio 2026: Cierre de Iniciativas 1, 2, 3 + Calibracion + Fase 2 Outbound

Movidos al archivar la bateria E2E completa (40 PASS, 0 FAIL). El codigo correspondiente
vive en `main` / `feature/allocation-layer-v12.1`.

| Documento | Por que se archiva |
|-----------|-------------------|
| `PLAN_INICIATIVA_1.md` | Iniciativa #1 (allocation layer V12.1 — picking por ubicacion real + reservas) completada e integrada. |
| `PLAN_INICIATIVA_2_OPCION_C.md` | Iniciativa #2 Opcion C (time-window routing) implementada hasta F2a. F2b se paro por decision del Director (modelar staging/depot como zona de aforo-k, pendiente de nueva sesion). El plan queda archivado; la continuacion partira de nueva hoja de ruta. |
| `PLAN_INICIATIVA_3_DESPACHO_OUTBOUND.md` | Iniciativa #3 (subsistema outbound completo: OutboundProcess, staged_pallets, metricas, visor web) 100% completada (F2.a–F2.d). |
| `PLAN_FASE2_CAMION_REAL.md` | Bitacora de la Fase 2 del camion real. F2.a (OutboundProcess), F2.b (poll-wait columna llena), F2.c (KPIs trucks/shipped en web), F2.d (staging no-transitable para A*) — todas completadas y commiteadas. |
| `PLAN_FIX_GUARDADO_CONFIGURADOR.md` | Fix del guardado del configurador web (null bytes en save_config) completado. Pipeline de config.json sano. |
| `PLAN_PASO2_TOGGLES_UI.md` | Paso 2 de toggles de congestion/outbound en el configurador web completado (seccion "Motor Avanzado" en index.html + load/serialize en app.js + validacion en config_manager.py). |
| `PROGRESO_INICIATIVA_3.md` | Bitacora viva de la Iniciativa #3. Cerrada con la Fase 2 completa y la bateria E2E. |
| `PROGRESO_OPCION_C.md` | Bitacora viva de la Iniciativa #2 Opcion C. Parada en F2b por decision del Director; se archiva hasta nueva sesion. |
| `ANALISIS_IMPACTO_CALIBRACION_TIEMPOS.md` | Analisis + plan de la calibracion de tiempos reales (C1–C5). Completado: constantes hardcodeadas eliminadas, bloque "tiempos" en config.json, card en configurador web, `config_calibrado_v1.json` disponible. |
| `ANALISIS_PROFUNDO_INICIATIVAS.md` | Hoja de ruta de iniciativas redactada en 2026-05-31. Todas las iniciativas priorizadas ahi (I1, I2-OpC, I3) fueron ejecutadas. Superada. |
| `ANALISIS_STAGING_AFORO.md` | Analisis de aforo del staging/muelle para la Iniciativa #2 Opcion A. Decision: se adopto Opcion C y luego F2.d implemento staging no-transitable para A*. El analisis ya no guia nada activo. |
| `INVESTIGACION_CONGESTION_SOLUCIONES.md` | Investigacion comparativa de soluciones a congestion/deadlock para Iniciativa #2. La decision (Opcion C) se tomo e implemento. Archivada como registro de la razon de la eleccion. |
| `INVESTIGACION_TIEMPOS_REALES_OPERACION.md` | Benchmarks de tiempos reales de almacen usados para calibrar el simulador. La calibracion esta implementada en config.json ("tiempos") y en `config_calibrado_v1.json`. Fuente de datos ya consumida. |
| `PRUEBAS_GUI.md` | Guion de pruebas manuales de la GUI web (pre-E2E). Reemplazado por `docs/PRUEBAS_E2E_SISTEMA.md` (bateria formal de 53 casos con resultados en `RESULTADOS_PRUEBAS_E2E.md`). |

---

## Lote 0 — Pre-Junio 2026: Decision Opcion C sobre congestion

| Documento | Por que quedo superado |
|-----------|------------------------|
| `PLAN_INICIATIVA_2_CONGESTION.md` | Plan basado en exclusion por celda / Combo A-B. Reemplazado por la Opcion C (ruteo libre de conflictos por construccion). |
| `PROGRESO_INICIATIVA_2.md` | Bitacora del intento F0-F3 (instrumentacion + dispersion de spawn + espera por timeout). Linea de trabajo jubilada al adoptar la Opcion C. |

---

## Lote 2 — Junio 2026: Cierre de H-6, Auditoria Estrategias, Limpieza de Basura

Movidos con `git mv` en sesion 2026-06-27 (auditoria documental post-V12.1).

| Documento | Por que se archiva |
|-----------|-------------------|
| `ANALISIS_H6_CERCANIA_DEADLOCK.md` | Analisis y plan del bug H-6 (deadlock de Cercania). Fix implementado en `8a2fe86` (radio blando). Ahora es registro historico. |
| `AUDITORIA_ESTRATEGIAS.md` | Auditoria completa de estrategias de despacho (2026-06-14). Sus resultados estan integrados: BK-01 implementado, H-5 corregido, BK-03 descartado con evidencia, BK-02 en BACKLOG. El documento ya no guia ninguna accion activa. |
| `LIMPIEZA_ARCHIVOS_BASURA.md` | Inventario de archivos basura (2026-06-14) cuando la limpieza aun no se habia hecho. La cuarentena se ejecuto en commit `8fd8a3c` (40+ archivos a basura/). El doc describe un trabajo completado y su estado actual es inexacto ("NO SE HA BORRADO NADA"). |

---

## Lote 3 — 2026-07-05: Reestructuracion de documentacion (ver `docs/META_DOCUMENTACION.md`)

Consolidacion de las 3 ubicaciones de archivo historico en una sola
(`docs/antiguos/`), y democion de planes ya ejecutados / docs auto-descritos
como "referencia" que seguian viviendo en `docs/` activo.

| Documento/carpeta | Por que se archiva |
|---|---|
| `archived_root/` (22 archivos) | Contenido completo del ex `archived/` (raiz del repo) — segunda ubicacion de archivo historico que existia en paralelo a esta. Consolidado aca via `git mv`. |
| `eliminacion_live_simulation/` (5 archivos) | Idem, subcarpeta del ex `archived/` sobre la eliminacion de la simulacion en vivo (2025-10-27). |
| `PLAN_MEJORA_1_RED_SEGURIDAD.md` | MEJ-1 (red de seguridad: pytest + gate + CI) HECHA y en `main`. Plan ejecutado. |
| `PLAN_MEJORA_4_ANTICOLISIONES.md` | MEJ-4 (anti-colisiones completo) HECHA y en `main`. Plan ejecutado; el hallazgo de makespan +55% quedo redefinido como INIT-6 (ver BACKLOG.md). |
| `PLAN_INIT4.md` | INIT-4 (prioridad/SLA/olas + tiempos de pick) HECHA. Plan ejecutado. |
| `VALIDACION_UI_WEB.md` | Auto-descrito como validacion puntual de 60 controles UI (2026-06-27); no vigente, historico. |
| `PRUEBAS_E2E_SISTEMA.md` | Catalogo formal de 53 casos E2E (2026-06-13); referencia puntual, no vigente. |
| `RESULTADOS_PRUEBAS_E2E.md` | Resultados de esa bateria (2026-06-13); referencia puntual, no vigente. |

El detalle de iniciativas cerradas DESDE 2026-07-04 en adelante ya no vive en
docs individuales por sesion — vive en `docs/CHANGELOG.md` (formato terso,
append-only). Este README sigue documentando los lotes historicos previos a
esa convencion.

## Que NO se archiva (sigue vigente en `docs/`)

- `docs/STATE.md` — foto del presente; se reescribe entera cada sesion.
- `docs/CHANGELOG.md` — historial de iniciativas cerradas (append-only).
- `docs/BACKLOG.md` — solo items pendientes/abiertos.
- `docs/META_DOCUMENTACION.md` — por que la documentacion esta organizada asi.
- `PROPUESTA_MEJORA_DISENO_UI.md` — D-01..D-16 implementadas; actualizado 2026-06-27.
- `VISION_PRODUCTO.md` — norte estrategico del producto; atemporal.
- `COMO_FUNCIONA_EL_PROGRAMA.md` — guia practica de como funciona el simulador.
- `INSTRUCCIONES_LAYOUT_PERSONALIZADO.md` — instrucciones operativas de layouts TMX.
- `INSTRUCCIONES_PROYECTO_COWORK.md` — metodologia atemporal del proyecto.
