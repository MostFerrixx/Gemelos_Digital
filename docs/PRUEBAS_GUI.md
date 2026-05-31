# Guion de pruebas manuales — GUI web (`web_prototype`)

> La **GUI web** es ahora la interfaz oficial del Gemelo Digital. Sustituye a las 3 GUI de
> escritorio (visualizador Pygame, dashboard PyQt6, configurador Tkinter), que fueron
> **deprecadas** y archivadas en `_legacy/gui_escritorio/`.
>
> **Objetivo:** confirmar que la web arranca y que sus funciones (configurador, presets,
> runner de simulación, visor de replay) operan leyendo recursos desde la **raíz**
> canónica, sin tocar nada de `_legacy/`.

Trabaja desde la raíz del proyecto:
```bat
cd /d "D:\Documentos\Martin\Gemelos Digital"
```

---

## 0) Preparación (una sola vez)

```bat
pip install -r requirements.txt
```
Ya incluye las dependencias web (`fastapi`, `uvicorn`, `pydantic`, `python-multipart`).
**Ya NO hace falta** `PyQt6` ni `pygame_gui` (eran de las GUI de escritorio). `pygame-ce`
se instala igual porque el motor headless lo usa internamente.

---

## 1) Arrancar el servidor web

Cualquiera de estas tres formas:
```bat
start_server.bat
```
```bat
.\run web
```
```bat
make web
```
(internamente: `python server_manager.py start`, que lanza `web_prototype\server.py` en
**http://localhost:8000**).

Luego abre el navegador en **http://localhost:8000**. Para detener: `stop_server.bat`
(o `python server_manager.py stop`). Estado: `status_server.bat`.

**Qué deberías ver:** la página principal carga sin error; en la consola/log
(`logs\server.log`) aparece uvicorn escuchando en el puerto 8000, sin trazas de error.

---

## 2) Configurador web

En la interfaz, abre la sección de **configuración** (parámetros: nº de operarios y
montacargas, estrategia de despacho, tipo de tour, capacidades, layout, archivo de secuencia).

**Qué probar:**
- Cambia algún parámetro (p. ej. nº de operarios) y **guarda**.
- Abre `config.json` (raíz) y confirma que el cambio quedó escrito.

**Qué revisar:**
- El `sequence_file` por defecto apunta a **`layouts/Warehouse_Logic.xlsx`** (raíz).
- `order_file_path` es la ruta **relativa** `uploads/orders_ordenes_prueba_real.json`
  (ya corregida), no una ruta absoluta.

---

## 3) Sistema de presets

Guarda la configuración actual como un **preset** con nombre; luego **cárgalo** y **bórralo**.

**Qué revisar:**
- Los presets se guardan como `.json` dentro de **`data\config_presets\`** (esta carpeta
  se preservó viva durante la consolidación de `data/`). Confirma que aparece/desaparece
  el archivo al guardar/borrar.

---

## 4) Work areas desde el Excel

En el configurador, dispara la carga de **work areas** (zonas) desde el archivo de secuencia.

**Qué deberías ver:** 3 áreas — `Area_Ground`, `Area_High`, `Area_Special` — leídas de
`layouts\Warehouse_Logic.xlsx` (raíz). Sin `FileNotFoundError`.

---

## 5) Ejecutar simulación (runner) y ver el replay

Desde la web, lanza una **simulación**. El runner ejecuta el motor **headless**
(`run_generate_replay.py`) por debajo y genera una carpeta `output\simulation_*\` con el
`replay_*.jsonl`, el reporte Excel y el **heatmap PNG** (este último vía `visualizer.py`
de la raíz — que NO se deprecó).

**Qué deberías ver:**
- Progreso de la corrida en la interfaz y, al terminar, el **mapa del almacén** con la
  reproducción del replay (operarios, rutas, métricas) renderizado **en el navegador**.
- En `output\simulation_*\` aparecen el `.jsonl`, el `.xlsx` y el `warehouse_heatmap_*.png`.

**Qué revisar:**
- El mapa carga el layout `layouts\WH1.tmx` (raíz) con sus tiles.
- En `logs\server.log` no aparecen rutas bajo `data\` (salvo `data\config_presets\`) ni
  bajo `_legacy\`, ni `ModuleNotFoundError`/`ImportError`.

---

## Checklist final

- [ ] El servidor arranca en http://localhost:8000 sin errores en `logs\server.log`.
- [ ] El configurador web guarda cambios en `config.json` (raíz).
- [ ] Presets: guardar/cargar/borrar funciona y se reflejan en `data\config_presets\`.
- [ ] Work areas: lee 3 zonas desde `layouts\Warehouse_Logic.xlsx` (raíz).
- [ ] Runner: genera `output\simulation_*\` con `.jsonl` + `.xlsx` + heatmap `.png`.
- [ ] Visor web: el mapa con el replay se renderiza en el navegador.
- [ ] En ningún log aparecen rutas bajo `_legacy\` ni `data\` (excepto `data\config_presets\`).

Si algo falla, copia el error exacto de `logs\server.log` (o de la consola del navegador,
F12) y la ruta que intentaba abrir: eso indica de inmediato si quedó algún recurso
apuntando a algo movido.

---

## Nota: las GUI de escritorio quedaron deprecadas

El visualizador Pygame, el dashboard PyQt6 y el configurador Tkinter ya **no se mantienen**;
su código está en `_legacy/gui_escritorio/` solo como referencia histórica. Si por algún
motivo necesitas correr el visor de escritorio antiguo, está documentado en
`_legacy/gui_escritorio/README.md` (requiere reinstalar `pygame_gui` y `PyQt6`).
