# PLAN — Datos maestros gestionables desde la web

**Estado:** PROPUESTO — pendiente de aprobacion del Director. NO se ha tocado
codigo.
**Fecha:** 2026-09-08
**Origen:** observacion del Director — "si algo no se puede configurar desde la
UI web, entonces siempre sera ignorado". Aplicado primero a un campo de tiempos,
llevo a la pregunta de fondo: **lo que vive en el Excel tampoco se puede tocar
desde la web**.
**Alcance elegido por el Director:** Opcion 3 (la completa: cargar + editar +
ver).

---

## 1. HALLAZGOS (lo que hay hoy, verificado)

### 1.1 La cadena real de datos maestros

```
Excel (lo que edita el cliente)
   |
   |  run_migration.py   <-- PASO MANUAL, por consola
   v
warehouse.db (SQLite)    <-- ESTO es lo que lee el motor
   |
   v
data_manager -> simulacion
```

`data_manager` carga de SQLite **si `warehouse.db` existe**, y solo cae al Excel
si no existe. Hoy la base existe, asi que **el motor NO lee el Excel**.

**Consecuencia grave y no documentada: si el cliente edita el Excel, no pasa
nada.** Su cambio no tiene ningun efecto hasta que alguien corra el migrador por
consola. No hay ningun aviso de esto en la UI.

Verificado el 2026-09-08: hoy ambos estan sincronizados (50 SKUs, 360
ubicaciones, 7 zonas de staging, 3 muelles en los dos lados), asi que el
problema esta latente, no activo.

### 1.2 Que hay en el Excel maestro (`layouts/Warehouse_Logic.xlsx`)

| Hoja | Contenido | Registros | Naturaleza |
|---|---|---|---|
| `PickingLocations` | x, y, pick_sequence, sku_initial, qty_initial, WorkGroup, WorkArea | 360 | Tabla grande |
| `SkuCatalog` | sku_code, volumen_m3, peso_kg, clase_manejo | 50 | Tabla media |
| `OutboundStaging` | staging_id, x, y | 7 | Tabla chica |
| `InboundDocks` | dock_id, x, y | 3 | Tabla chica |

### 1.3 Botones mentirosos

En la pestana "Layout y Datos", los dos botones **"Examinar"** (mapa `.tmx` y
Excel) **no tienen ningun manejador**: se aprietan y no pasa nada. Los campos de
ruta son texto libre, asi que hoy la unica forma de cambiar el mapa o el Excel
es copiar el archivo a mano a la carpeta correcta.

### 1.4 Lo que SI existe y sirve de base

- `run_migration.py` ya acepta `--excel <path>`, `--db <path>` y
  `--keep-existing`, y usa `ExcelImporter`, que devuelve un `ImportResult`
  estructurado (ideal para mostrarlo en pantalla).
- Ya hay un patron de subida de archivos con validacion y vista previa:
  `POST /api/upload-orders` (archivo de pedidos, con conteos y exclusiones).
- Ya hay un patron de proceso largo lanzado desde la web: el runner de
  simulacion y el de optimizacion.

**No hay que inventar nada: hay que conectar piezas que ya existen.**

---

## 2. PRINCIPIO QUE GUIA EL DISENO

Excel **no es el enemigo**: es una herramienta excelente para editar tablas
grandes y el cliente ya sabe usarla. Meter 360 ubicaciones en formularios web
seria un retroceso.

Lo que falta no es *reemplazar* Excel, es que **la web pueda recibirlo, validarlo
y mostrar que esta usando**. Por eso el alcance se reparte segun el tamano de
cada tabla:

| Tabla | Que se hace desde la web |
|---|---|
| PickingLocations (360) | Cargar (subiendo el Excel) + VER |
| SkuCatalog (50) | Cargar + VER |
| OutboundStaging (7) | Cargar + VER + **EDITAR** |
| InboundDocks (3) | Cargar + VER + **EDITAR** |

---

## 3. FASES

### F1 — Carga desde la web (los botones "Examinar" funcionando)

1. `POST /api/master-data/upload-excel`: recibe el `.xlsx`, lo guarda en
   `uploads/`, lo **valida** (hojas requeridas, columnas, tipos) y devuelve un
   resumen SIN aplicar nada todavia: "50 SKUs, 360 ubicaciones, 7 zonas, 3
   muelles" + errores/avisos.
2. `POST /api/master-data/apply`: corre la migracion a `warehouse.db` (invocando
   el migrador existente) y devuelve el `ImportResult`.
   **Backup automatico de `warehouse.db` antes de tocarla.**
3. `POST /api/master-data/upload-tmx`: idem para el mapa (validar que se pueda
   abrir y tenga las capas esperadas).
4. UI: los botones "Examinar" abren el selector de archivo; se muestra el
   resumen de validacion y un boton **"Aplicar"** explicito. Nada se aplica solo.

**Ademas (importante): un aviso permanente en la pestana Layout y Datos cuando
el Excel del disco sea MAS NUEVO que `warehouse.db`** — es decir, cuando alguien
edito el Excel y no aplico los cambios. Hoy ese estado es invisible.

### F2 — Ver los datos maestros cargados

5. `GET /api/master-data/summary`: conteos por tabla + fecha de la ultima
   importacion.
6. `GET /api/master-data/table/{nombre}`: contenido paginado (`limit`/`offset`)
   con busqueda simple.
7. UI: tarjeta "Datos Maestros Cargados" en Layout y Datos, con pestanas o
   selector por tabla, buscador y paginado. **Solo lectura** para
   PickingLocations y SkuCatalog.

### F3 — Editar las tablas chicas

8. `PUT /api/master-data/staging-areas` y `PUT /api/master-data/inbound-docks`:
   validan (ids unicos, coordenadas dentro del mapa, sin pisar obstaculos) y
   escriben en `warehouse.db`.
9. UI: edicion en linea de las 7 zonas y los 3 muelles, con el mismo estilo de
   tarjetas del resto.

### F4 — Documentacion y cierre

10. Manual de usuario: seccion nueva explicando el flujo (subir -> revisar ->
    aplicar) y que el Excel no tiene efecto hasta aplicarlo.
11. `CLAUDE.md`: corregir la descripcion de la cadena de datos, que hoy no dice
    que la BD le gana al Excel.

---

## 4. DECISIONES QUE NECESITO DEL DIRECTOR

**D1 — Que pasa con las ediciones web al re-importar el Excel.**
Si el cliente edita las zonas de staging desde la web y despues sube un Excel
nuevo, la importacion **pisa** esas ediciones (el Excel manda). Opciones:
(a) que las pise y avisar claramente antes de aplicar;
(b) intentar preservar lo editado en web;
(c) que la edicion web tambien escriba el Excel.
**Recomiendo (a):** simple, predecible y sin dos fuentes de verdad peleando. La
(c) suena ideal pero convierte cada edicion en una escritura de Excel, con
riesgo de corromper el archivo del cliente.

**D2 — Alcance de la importacion.**
El migrador por defecto **resetea** las tablas. Existe `--keep-existing`.
Recomiendo el reset completo (es lo que hace hoy) **con backup automatico
previo**, porque un import parcial deja estados hibridos dificiles de explicar.

**D3 — Inventario/stock.**
`PickingLocations` trae `qty_initial` (stock inicial). Re-importar **reinicia el
stock**. Hay que decir esto MUY claro en pantalla antes de aplicar. Confirmar
que ese es el comportamiento deseado.

---

## 5. VALIDACION

1. `python -m pytest -q` verde tras cada fase (hoy: 228).
2. `python scripts/regression_gate.py` **PASS byte-identico en TODAS las fases**:
   esto no cambia el motor. Si el gate falla, algo se toco de mas.
3. Tests nuevos: validacion de un Excel bueno, uno con una hoja faltante, uno
   con columnas mal, y que la deteccion de "Excel mas nuevo que la BD" funcione.
4. Prueba de extremo a extremo en el navegador: subir el Excel real, ver el
   resumen, aplicar, y confirmar que los conteos cambian en la vista.
5. Prueba de no-regresion: tras aplicar el MISMO Excel que ya estaba, el gate
   debe seguir dando PASS (la BD reconstruida es equivalente).

**El punto 5 es la red de seguridad principal de esta iniciativa:** si
reconstruir la base desde el mismo Excel cambiara el comportamiento del motor,
significaria que la BD y el Excel divergieron en algun momento, y eso hay que
saberlo antes de tocar nada.

---

## 6. ESFUERZO ESTIMADO

- F1: 1 dia (es el grueso: subida, validacion, migracion, avisos).
- F2: medio dia.
- F3: medio dia.
- F4: 2 horas.

Total aproximado: **2 a 2,5 dias** de trabajo, en fases entregables por
separado. F1 sola ya elimina el problema principal.
