# STATE — Gemelo Digital de Almacen

> Este archivo se REESCRIBE ENTERO cada sesion (no acumula). Es la foto del
> presente, nada mas. Historial -> `docs/CHANGELOG.md`. Pendientes ->
> `docs/BACKLOG.md`. Identidad/reglas/arquitectura -> `CLAUDE.md`.

**Ultima actualizacion:** 2026-09-26

## Git

- `main` integra por fast-forward. Rama de trabajo: `qa/configuracion-web`.
- **Baseline vigente: `sha256=6fe69d88...`, 19.724.749 bytes**, seed 42
  (`tests/baseline.json`). Cambio intencional del 2026-09-26 (BK-39: perfil
  Real; 624 tareas en 195,5 min, 191,6 tareas/h). Anteriores del mismo dia:
  `0c22f1c7` (H-53), y `62c65ebf` (BK-29, 2026-09-23).
- REGLA pinneada por tests BN-05 e IN-43: la metadata del .jsonl NO puede
  contener valores wall-clock.
- En Windows `core.autocrlf=true`: `config.json` puede figurar como modificado
  solo por finales de linea. Git y el gate normalizan.

## Red de seguridad

```
python -m pytest -q                # 405 passed, 1 deselected (~40s)
python scripts/regression_gate.py  # GATE PASS esperado (baseline 6fe69d88)
python scripts/check_equivalencia_personas.py  # INIT-11 F1: EQUIVALENTE (~1 min)
```

## Canonico

- **Perfil de velocidad Real** (BK-39, 2026-09-26): 1 s/celda a pie, montacargas
  0,5 (2 m/s), horquilla 8 s. "Demo" ya no existe.
- Configuraciones guardadas = replicas completas en `data/config_presets/`
  (BK-36): "Canonico v3 (referencia)" + las de QA ("QA-<caso> ...", entre
  ellas las 21 `QA-C-nn` de las pruebas combinadas, listas para reusar).
- "Aplicar" REEMPLAZA `config.json` por la pantalla (H-60) y avisa lo que
  quita; "Run" usa una copia temporal (BK-11). `uploads/` solo se limpia de lo
  que `config.json` no usa (H-57).

- `config_default.json` (raiz, versionado) = valores de fabrica del boton
  "Default"; hoy igual a `config.json`. Si el canonico cambia de mapa o Excel,
  actualizarlo (un test verifica que encaje con los datos).

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
  apagados POR DECISION del Director (se usan para pruebas); desde el 23/09
  tienen control en la web (pestana Estrategias). RE-MEDIDOS el 23/09 (sus mediciones previas estaban afectadas por
  el error del pulmon): zonas 2.714 s vs 2.652 s sin zonas (+2%, empate
  practico); cupo 3.345 s (+26%).
- `inicio_turno {zonas, usar_estacionamientos, radio_estacionamiento}`
  (BK-29): opcional; sin control web todavia (BK-22).

## QA de la configuracion web

`docs/PLAN_QA_CONFIGURACION_WEB.md`. Hechos los bloques 0 a 12 **y las
pruebas combinadas** (`docs/PLAN_QA_COMBINADAS.md`, 2026-09-26): 21
escenarios + fase de replica; 19 PASAN, C-14 (BK-40) y C-17 (H-59) quedan con
hallazgos abiertos; replicas 21/21 correctas; A/B replica = IDENTICO.
Corregidos H-53 a H-58 y H-60 (H-56 parcial). **El QA de la configuracion web
queda completo.** El
bloque 11 corrigio H-47 (critico: el optimizador corria siempre la misma flota),
H-49 y H-50; tabla de trials nueva. El bloque 10 corrigio H-44 ("Default" viejo) y H-45 (Abrir Visor). El bloque 6 corrigio H-43 (mapas y Excel
incompatibles se aceptaban), H-39 y H-41; H-40 y H-42 cerrados con BK-35.
Metodo: cada bloque cierra con una pasada visual (clics reales + capturas,
`scripts/qa/capturas_web.py`). El bloque 8 corrigio H-35, H-36 y H-38 (stock de
la base entre corridas); abierto H-37 (BK-34).
El bloque 7 corrigio H-29, H-30 y H-31; abiertos H-32 (BK-32) y H-33
(BK-33). H-34 cerrado con BK-29.

## BK-25 (atasco en la descarga)

Plan vivo: `docs/PLAN_BK25_ESTACION_DESCARGA.md`. F1 cerrada; el atasco con
flota grande esta resuelto (8+8 repartido 26.736 -> 2.604 s). **F2 (cesion
del paso): ahora hay una medicion que la pide** (QA H-59, almacen B +
outbound: 2 co-ocupaciones al salir de un carril sobre otro que espera en la
boca).

## Decisiones del Director pendientes

1. **D9:** reparto real entre los 7 muelles (hoy 100% al carril 1) o rutas.
2. **D3:** con camiones activos, pallet por linea (hoy) o contenedor por
   pedido. Recomendacion: contenedor por pedido.
3. **D5** (pasillos de un solo sentido), **D7** (formato de las reglas),
   **D8** (mapa sin salida posible).
4. **BK-16:** el servidor del cliente se reinicia solo al cambiar un `.py`.
5. **BK-30:** el muelle de salida (outbound) sigue sin ser realista.
6. **BK-02** FIFO en UI, **INIT-10** modelo de almacen propio.
7. **BK-37:** que mide el optimizador (hoy eficiencia: gana la flota mas chica)
   o cumplir el turno.
8. **BK-40:** cupo por pasillo estricto (esperar afuera + no cruzar pasillos
   ajenos); necesita diseno.
9. **BK-38:** archivar 3 mapas-esqueleto de `layouts/` (poda).

## Bugs conocidos (no criticos)

- Ver `docs/BACKLOG.md`: BK-10, BK-13, BK-14, BK-16 a BK-40 (BK-29, BK-35, BK-36 y BK-39 cerrados).
- `warehouse.db` es la copia de trabajo del stock: cada corrida la restaura al
  arrancar desde `inventory_baseline`; "Aplicar Excel" borra esa foto (H-38).
  El respaldo de la base anterior al v3 es `warehouse_pre_v3_backup.db` (sin
  versionar); `warehouse.db.bak` ahora es la del v3.
- Al reiniciar el servidor a mano puede quedar un proceso hijo de
  `multiprocessing` reteniendo el puerto 8000.
