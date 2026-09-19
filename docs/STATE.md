# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-19

## Git

- `main` integra por fast-forward (ramas re-apiladas, sin commits de merge):
  INIT-11 F0-F2, el plan de QA de la configuracion web con sus correcciones
  (H-01, H-07) y la correccion de la capa anti-colision (BK-15 / QA H-05).
- Baseline byte-identico vigente: **`sha256=5c7f4c32...`, 16.591.951 bytes**,
  seed 42 (`tests/baseline.json`). Cambio intencional del 2026-09-18 (BK-15:
  nunca dos agentes en la misma celda; los ociosos esperan donde no estorban).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan; restaurar con
  `git checkout -- config.json` antes de commitear.

## Red de seguridad

```
python -m pytest -q                # 308 passed, 1 deselected (~20s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 5c7f4c32)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

## En curso: plan de QA de la configuracion web

`docs/PLAN_QA_CONFIGURACION_WEB.md` (documento vivo: seccion 0 = objetivo
inmediato; seccion 9 = registro de cada prueba; seccion 10 = hallazgos).
Metodo: cada control se configura SOLO desde la web y se verifica en 3
niveles (llega a la corrida / cambia el comportamiento / el visor muestra lo
mismo que el JSON). Modo de trabajo del Director: cada error se corrige apenas
se confirma, se reprueba y recien entonces se sigue.
- Hecho: bloques 0 (metodo), 1 (Carga de Trabajo), 2 (Despacho y tours) y
  4 (Tiempos). Corregidos H-01 (Run descartaba la config sin control web),
  H-07 (un 0 se reemplazaba por el default), H-05 (co-ocupaciones, BK-15) y
  H-14 (el tiempo por celda se ignoraba).
- **Siguiente: bloque 5 (Flota).**
- Para QA usar el servidor `web-qa` de `.claude/launch.json` (sin recarga
  automatica; ver BK-16). Herramientas: `scripts/qa/analizar_replay.py`,
  `scripts/qa/esperar_corrida.py`.

## INIT-11 Task Path (en pausa mientras avanza el QA)

Plan v2: **`docs/PLAN_INIT11_TASK_PATH.md`**. F0, F1 y F2 hechas e
integradas. **Siguiente: F3** (pick -> punto de transferencia -> staging), que
es punto de control con el Director.

## Decisiones del Director pendientes

1. **BK-16:** el servidor del cliente se reinicia solo al cambiar un `.py` y
   cancela simulaciones (ligado a BK-10, el boton Restart depende de eso).
2. **BK-19 / BK-23:** reparto del trabajo (un solo operario se lleva todo con
   pocas tareas; el despacho manda un segundo equipo a una ubicacion ocupada).
3. **BK-08 (alta):** confirmar con el almacen real que Area_High/Area_Special son
   100% montacargas. **BK-09:** flota 2+2 sub-dimensionada.
4. Reparto de `outbound_staging_distribution` (hoy 100% a la zona 1).
5. **BK-07** areas mixtas, **BK-02** FIFO en UI, **INIT-10** modelo de almacen propio.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow ACTIVA en el canonico, con las garantias de BK-15:
  0 co-ocupaciones fuera de la ventana de arranque; los ociosos esperan en
  celdas elegidas automaticamente (fila 29 entre zonas de descarga) o en
  `zonas_espera` si se configuran.
- BK-06: `work_area_equipment` manda; capacidad por area de la flota real.
- Canonico con `agent_types` explicito (2 terrestres + 2 montacargas).
- INIT-8 nucleo ACTIVO; F3/F4 e inbound opt-in. INIT-11 personas/equipos/
  perfiles/estacionamientos: opt-in, sin editor web todavia (BK-22).

## Bugs conocidos (no criticos)

- Ver `docs/BACKLOG.md`: BK-10, BK-13, BK-14, BK-16 a BK-23.
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000: hay que cerrarlo tambien.
- El visor no interpola posiciones entre snapshots (mitigado con "Saltar
  tiempos muertos").
