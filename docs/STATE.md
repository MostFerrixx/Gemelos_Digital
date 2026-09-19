# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-19

## Git

- `main` integra por fast-forward (ramas re-apiladas, sin commits de merge):
  INIT-11 F0-F2, el plan de QA de la configuracion web y sus correcciones
  (H-01, H-07, H-14, H-17, H-18, H-19) y la capa anti-colision (BK-15).
- Rama de trabajo del QA: `qa/configuracion-web` (se integra a `main` al
  cerrar cada bloque, con gate PASS).
- Baseline byte-identico vigente: **`sha256=5c7f4c32...`, 16.591.951 bytes**,
  seed 42 (`tests/baseline.json`). Sin cambios desde BK-15 (H-19 no altera
  el canonico: el outbound esta apagado).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan; restaurar con
  `git checkout -- config.json` antes de commitear.

## Red de seguridad

```
python -m pytest -q                # 311 passed, 1 deselected (~20s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 5c7f4c32)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

OJO: el gate solo cubre el canonico (outbound apagado). H-19 se escapo por
eso; `tests/unit/test_qa_h19_espera_con_outbound.py` cubre ahora ese caso.

## En curso: plan de QA de la configuracion web

`docs/PLAN_QA_CONFIGURACION_WEB.md` (documento vivo: seccion 0 = objetivo
inmediato; seccion 9 = registro de cada prueba; seccion 10 = hallazgos).
Metodo: cada control se configura SOLO desde la web y se verifica en 3
niveles (llega a la corrida / cambia el comportamiento / el visor muestra lo
mismo que el JSON, incluidas carga y capacidad desde el bloque 5).
- Hecho: bloques 0, 1, 2, 4 y **5 (Flota, 11/11)**. Corregidos H-01, H-07,
  H-05 (BK-15), H-14, H-17 (panel del visor), H-18 (flota por defecto) y
  H-19 (ociosos trabados con outbound activo).
- **Siguiente: bloque 3 (Motor avanzado).** Luego 7, 8, 6, 10, 9, 11, 12 y
  las pruebas combinadas.
- Servidor de QA: `web-qa` de `.claude/launch.json` (sin recarga automatica;
  ver BK-16). Herramientas en `scripts/qa/`.

## INIT-11 Task Path (en pausa mientras avanza el QA)

Plan v2: **`docs/PLAN_INIT11_TASK_PATH.md`**. F0, F1 y F2 hechas e
integradas. **Siguiente: F3** (pick -> punto de transferencia -> staging), que
es punto de control con el Director.

## Decisiones del Director pendientes

1. **BK-25 / QA H-15 (alta, realismo):** atasco circular en la zona de
   descarga con flota grande (los que esperan tapan la salida del que
   descarga; duplicar la flota casi no rinde).
2. **BK-28 / QA H-22:** una config sin bloque `outbound` corre con outbound
   encendido desde la web y apagado desde consola.
3. **BK-16:** el servidor del cliente se reinicia solo al cambiar un `.py` y
   cancela simulaciones (ligado a BK-10).
4. **BK-19 / BK-23:** reparto del trabajo (un solo operario se lleva todo con
   pocas tareas; segundo equipo mandado a una ubicacion ocupada).
5. **BK-08:** confirmar que Area_High/Area_Special son 100% montacargas.
   **BK-09:** flota 2+2 sub-dimensionada.
6. Reparto de `outbound_staging_distribution` (hoy 100% a la zona 1; agrava
   BK-25).
7. **BK-07** areas mixtas, **BK-02** FIFO en UI, **INIT-10** modelo de
   almacen propio, **BK-24** Cercania.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow ACTIVA en el canonico, con las garantias de BK-15:
  0 co-ocupaciones con la flota canonica fuera de la ventana de arranque (con
  flota grande reaparecen por BK-25); los ociosos esperan en celdas elegidas
  automaticamente o en `zonas_espera`, siempre fuera de los carriles de
  descarga (H-19).
- BK-06: `work_area_equipment` manda; "Generar Flota por Defecto" lo respeta.
- Canonico con `agent_types` explicito (2 terrestres + 2 montacargas).
- INIT-8 nucleo ACTIVO; F3/F4 e inbound opt-in. INIT-11 personas/equipos/
  perfiles/estacionamientos: opt-in, sin editor web todavia (BK-22).

## Bugs conocidos (no criticos)

- Ver `docs/BACKLOG.md`: BK-10, BK-13, BK-14, BK-16 a BK-29.
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000: hay que cerrarlo tambien.
- El visor no interpola posiciones entre snapshots (mitigado con "Saltar
  tiempos muertos").
