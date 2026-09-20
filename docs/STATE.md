# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-20

## Git

- `main` integra por fast-forward. Rama de trabajo: `qa/configuracion-web`;
  la iniciativa BK-25 se desarrollo en `fix/bk25-estacion-descarga` (ya
  integrada).
- **Baseline vigente: `sha256=02796701...`, 17.088.496 bytes**, seed 42
  (`tests/baseline.json`). Cambio intencional del 2026-09-20 (BK-25 F1: mapa
  nuevo + estacion de descarga con turno). El anterior era `5c7f4c32`.
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan.

## Red de seguridad

```
python -m pytest -q                # 331 passed, 1 deselected (~28s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 02796701)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

## EL CANONICO CAMBIO (2026-09-20)

- **Mapa: `layouts/WH1 v3.tmx`** (32 x 43). Es el v2 del Director mas: anden de
  3 filas delante de los carriles y el ultimo pasillo de picking completo (2
  celdas con racks a ambos lados; antes tenia 1 y era un embudo que
  estrangulaba toda la corrida).
- **Datos: `layouts/Warehouse_Logic_v3.xlsx`** importados a `warehouse.db`
  (respaldo del anterior en `warehouse.db.bak`, sin versionar): **384
  ubicaciones** (antes 360) y **140 celdas de carril** (7 carriles de 2x10).
- **`estaciones: {enabled: true, cola_max: 1}`**: cada carril es una estacion
  con turno (un puesto por columna, entrada por el frente, salida por su
  costado de un solo sentido, fila de 1 y pulmon).
- **`congestion.timewindow.ultimo_recurso: "esperar"`**: el que no puede pasar
  espera; ya no atraviesa a otro (QA D6).
- `database_file` es configurable (antes la base estaba fija en el codigo).

## En curso: BK-25 (atasco en la descarga)

Plan vivo: **`docs/PLAN_BK25_ESTACION_DESCARGA.md`** (fases, decisiones con su
porque y registro de avance). Analisis de fondo del consultor externo en
`docs/PROPUESTA_DISENO_CIRCULACION_Y_LAYOUT.md` y
`docs/PROPUESTA_DISENO_CEDER_EL_PASO.md`.

- **F1 CERRADA** (F0 sobre-reserva, F1.a base multicelda, F1.b datos v3,
  F1.c estacion con turno, F1.c2 salidas de un sentido, F1.d canonico nuevo).
  Medido con semilla 42: 4+4 repartido 4.450 s, 8+8 repartido 2.574 s,
  4+4 todo al carril 1 8.682 s, sin co-ocupaciones fuera del arranque.
- **Siguiente: F2** — cesion por solicitud (que el que espera se corra cuando
  otro necesita pasar), apagada por defecto y medida con flota grande.

## QA de la configuracion web (en pausa mientras avanza BK-25)

`docs/PLAN_QA_CONFIGURACION_WEB.md`. Hechos los bloques 0, 1, 2, 3, 4 y 5.
**Siguiente: bloque 7 (Outbound Staging)**; el 6 (Layout y Datos) conviene
rehacerlo ahora que el canonico cambio de mapa.

## Decisiones del Director pendientes

1. **D3:** con camiones activos, un pallet por linea de pedido (hoy) o un
   contenedor por pedido. Recomendacion: contenedor por pedido.
2. **D9 / D-A6:** reparto real entre los 7 muelles o consolidacion por
   tienda/ruta (`destino_staging_map` ya existe). Hoy el canonico manda el
   100% al carril 1, que es el peor caso.
3. **D5** (pasillos de un solo sentido), **D7** (formato de las reglas),
   **D8** (que hacer con un mapa sin salida posible).
4. **BK-16:** el servidor del cliente se reinicia solo al cambiar un `.py`.
5. **BK-19 / BK-23:** reparto del trabajo entre operarios.
6. **BK-30:** el muelle de salida (outbound) sigue sin ser realista.
7. **BK-02** FIFO en UI, **INIT-10** modelo de almacen propio.

## Que esta VIVO y ACTIVO ahora mismo (ademas de CLAUDE.md §3/§5)

- Congestion timewindow + BK-15 (zonas de espera) + BK-25 (estacion con turno,
  salidas de un solo sentido, esperar en vez de pisar).
- BK-06: `work_area_equipment` manda; "Generar Flota por Defecto" lo respeta.
- INIT-8 nucleo ACTIVO; F3/F4 e inbound opt-in. INIT-11 personas/equipos/
  perfiles/estacionamientos: opt-in, sin editor web (BK-22).

## Bugs conocidos (no criticos)

- Ver `docs/BACKLOG.md`: BK-10, BK-13, BK-14, BK-16 a BK-30.
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000.
- El visor no interpola posiciones entre snapshots (mitigado con "Saltar
  tiempos muertos").
