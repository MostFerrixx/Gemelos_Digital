# Documentacion antigua (superada)

Esta carpeta contiene documentos de trabajo que **ya no estan vigentes** porque
fueron **reemplazados por la decision de resolver la congestion con la Opcion C**
(ruteo por reserva de rutas en el espacio-tiempo / *time-window / reservation-based
routing*, enfoque 2.11 / Combo C de `docs/INVESTIGACION_CONGESTION_SOLUCIONES.md`).

Se conservan aqui (no se borran) por valor historico y trazabilidad de decisiones.
No deben usarse como referencia del rumbo actual.

## Que se movio y por que

| Documento | Por que quedo superado |
|-----------|------------------------|
| `PLAN_INICIATIVA_2_CONGESTION.md` | Plan de la Iniciativa #2 basado en **exclusion por celda / Combo A-B** y fases F0-F3. La Opcion C reemplaza ese enfoque reactivo por una planificacion de rutas libre de conflictos por construccion, por lo que este plan ya no guia la implementacion. |
| `PROGRESO_INICIATIVA_2.md` | Bitacora de progreso del intento F0-F3 (instrumentacion + dispersion de spawn + espera por timeout). Sirve como registro de lo aprendido, pero la linea de trabajo que documenta queda jubilada al adoptar la Opcion C. |

## Que NO se movio (sigue vigente en `docs/`)

- `INVESTIGACION_CONGESTION_SOLUCIONES.md` — justifica la eleccion de la Opcion C; es la **base del nuevo plan**.
- `ANALISIS_PROFUNDO_INICIATIVAS.md` — hoja de ruta general de iniciativas.
- `PLAN_INICIATIVA_1.md` — registro de la Iniciativa #1 (ya hecha).
- `PLAN_INICIATIVA_2_OPCION_C.md` — el **nuevo** plan vigente de la Iniciativa #2.
- Guias de usuario / referencia (`DYNAMIC_LAYOUTS_USER_GUIDE.md`, `INSTRUCCIONES_LAYOUTS.md`,
  `INSTRUCCIONES_LAYOUT_PERSONALIZADO.md`, `TILES_REFERENCE.md`, `TUTORIAL_EXPLICACION.md`,
  `PRUEBAS_GUI.md`) — siguen siendo material de referencia vivo.

> Nota: el movimiento se hizo con `git mv` (reversible). Para revertir:
> `git mv docs/antiguos/<archivo> docs/<archivo>`.
