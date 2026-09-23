# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-23

## Git

- `main` integra por fast-forward. Rama de trabajo: `qa/configuracion-web`.
- **Baseline vigente: `sha256=62c65ebf...`, 17.302.142 bytes**, seed 42
  (`tests/baseline.json`). Cambio intencional del 2026-09-23 (BK-29: cada
  operario empieza el turno en una celda propia; y el que espera turno sin
  lugar en la fila va de verdad al pulmon). Anteriores del mismo dia:
  `f9089cba` (QA H-29/H-30), `0c441704`.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan.

## Red de seguridad

```
python -m pytest -q                # 364 passed, 1 deselected (~30s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 62c65ebf)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

## Canonico

- Mapa `layouts/WH1 v3.tmx` (32 x 43, anden de 3 filas, 8 pasillos de picking
  de 2 celdas) + datos `layouts/Warehouse_Logic_v3.xlsx` importados a
  `warehouse.db` (384 ubicaciones, 7 carriles de 2x10).
- `estaciones {enabled: true, cola_max: 1}`: cada carril es una estacion con
  turno (puesto por columna, entrada por el frente, salida por su costado de
  un solo sentido). Desde H-30 la fila se respeta y quien recibe un puesto
  aparta la entrada hasta llegar.
- `congestion.timewindow.ultimo_recurso: "esperar"`.
- Despacho: una ubicacion, un operario (BK-23 capa 1) y reparto de
  piqueadores entre muelles (`despacho.repartir_por_staging`), ambos activos.
- Reparto de salida: sigue 100% al carril 1 (decision D9 pendiente).
- Inicio del turno (BK-29): cada operario nace en una celda propia (zonas de
  inicio > estacionamiento de su equipo > celdas de espera). Semilla 42:
  **0 co-ocupaciones en los 10 escenarios medidos**, tambien en el arranque.

## Opt-in nuevos (apagados por defecto)

- `rutas_estocasticas {enabled, cantidad}`: N rutas atadas a muelles en modo
  aleatorio (control web "Rutas a Piquear").
- `zonas_picking` (una zona por pasillo) y `pasillos` (cupo por pasillo):
  apagados. RE-MEDIDOS el 23/09 (sus mediciones previas estaban afectadas por
  el error del pulmon): zonas 2.714 s vs 2.652 s sin zonas (+2%, empate
  practico); cupo 3.345 s (+26%).
- `inicio_turno {zonas, usar_estacionamientos, radio_estacionamiento}`
  (BK-29): opcional; sin control web todavia (BK-22).

## QA de la configuracion web

`docs/PLAN_QA_CONFIGURACION_WEB.md`. Hechos los bloques 0, 1, 2, 3, 4, 5 y 7.
**Siguiente: bloque 8 (Inbound)**; despues 6 (rehacer con el mapa nuevo), 10,
9, 11, 12 y las combinadas.
El bloque 7 corrigio H-29, H-30 y H-31; abiertos H-32 (BK-32) y H-33
(BK-33). H-34 cerrado con BK-29.

## BK-25 (atasco en la descarga)

Plan vivo: `docs/PLAN_BK25_ESTACION_DESCARGA.md`. F1 cerrada; el atasco con
flota grande esta resuelto (8+8 repartido 26.736 -> 2.604 s). **F2 (cesion
del paso) probablemente innecesaria**: se retoma solo si una medicion la pide.

## Decisiones del Director pendientes

1. **D9:** reparto real entre los 7 muelles (hoy 100% al carril 1) o rutas.
2. **D3:** con camiones activos, pallet por linea (hoy) o contenedor por
   pedido. Recomendacion: contenedor por pedido.
3. **D5** (pasillos de un solo sentido), **D7** (formato de las reglas),
   **D8** (mapa sin salida posible).
4. Zonas de picking: tras la re-medicion empatan con "sin zonas"; decidir
   si se encienden (realismo: operario asignado a pasillos) o quedan apagadas.
5. **BK-16:** el servidor del cliente se reinicia solo al cambiar un `.py`.
6. **BK-30:** el muelle de salida (outbound) sigue sin ser realista.
7. **BK-02** FIFO en UI, **INIT-10** modelo de almacen propio.

## Bugs conocidos (no criticos)

- Ver `docs/BACKLOG.md`: BK-10, BK-13, BK-14, BK-16 a BK-33 (BK-29 cerrado).
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000.
