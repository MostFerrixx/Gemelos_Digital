# INVENTARIO DE ARCHIVOS BASURA
**Proyecto:** Gemelo Digital de Almacén  
**Fecha de análisis:** 2026-06-14  
**Estado:** SOLO INVENTARIO — NO SE HA BORRADO NADA

---

## RESUMEN EJECUTIVO

| Categoría | Archivos | Peso aprox. | Acción |
|-----------|----------|-------------|--------|
| `.fuse_hidden*` (artefactos WinFsp) | 7.037 | ~220 MB | Seguro borrar (fuera de sesión) |
| `output/` (corridas viejas) | 646 | **598 MB** | Seguro borrar |
| `.bat` temporales ya consumidos | 6 | <10 KB | Seguro borrar |
| Archivos de log vacíos | 6 | 0 B | Seguro borrar |
| `.bak`/basura de respaldo | 2 | ~24 MB | Seguro borrar |
| Configs de prueba obsoletos | ~12 | <50 KB | Seguro borrar (con confirmación) |
| Archivos raíz varios dudosos | ~6 | <200 KB | Confirmar con Director |
| Scripts de diagnóstico muertos | 3 | ~6 KB | Confirmar con Director |
| `_backup_iniciativa3/` | 20 | 24 MB | Confirmar con Director |

**Peso total recuperable (seguro):** ~820 MB  
**Peso total recuperable (con confirmaciones):** ~850 MB

---

## CATEGORÍA 1: SEGURO BORRAR

### 1.1 Archivos `.fuse_hidden*` — 7.037 archivos (~220 MB)

**Qué son:** Archivos temporales generados por WinFsp (el driver FUSE de Windows que monta la carpeta compartida). Se crean durante operaciones de escritura atómica (`os.replace()`) y permanecen cuando el proceso termina abruptamente. Son copias intermedias de archivos legítimos.

**Por qué es seguro:** Son artefactos del driver de filesystem, no datos del proyecto. WinFsp los puede recrear durante operaciones normales. Todos están en el directorio raíz.

**Precaución:** Borrar mientras el servidor está corriendo podría interrumpir una escritura activa. **Detener el servidor primero.**

**Tamaño individual:** 32 KB o 64 KB cada uno (bloques FUSE). **Total: ~220 MB.**

```bash
# Ejecutar con servidor DETENIDO
cd "D:\Documentos\Martin\Gemelos Digital"
del /q .fuse_hidden*
# En Linux/WSL:
# find . -maxdepth 1 -name ".fuse_hidden*" -delete
```

---

### 1.2 `output/` — 646 archivos, **598 MB**

**Qué es:** Carpeta de resultados de simulaciones. Contiene subcarpetas con nombre `simulation_YYYYMMDD_HHMMSS/` (60+ corridas desde septiembre 2025). Cada subcarpeta tiene `.jsonl` de eventos, Excel de métricas y heatmap PNG.

**Antigüedad:** La más antigua data de `2025-09-23`, la mayoría entre octubre-diciembre 2025. Son corridas de desarrollo/prueba del motor.

**Por qué es seguro:** Son outputs reproducibles. El motor puede regenerarlos en cualquier momento con los mismos config. No hay datos únicos aquí que no estén en el código o en `config.json`.

**Excepción:** Si el Director quiere conservar alguna corrida específica como referencia (ej. la primera con Fase 2 completa), mover esa subcarpeta antes de borrar.

```bash
# Borrar toda la carpeta output (dejando el directorio vacío)
rmdir /s /q "D:\Documentos\Martin\Gemelos Digital\output"
mkdir "D:\Documentos\Martin\Gemelos Digital\output"
```

---

### 1.3 `.bat` temporales ya consumidos

Estos scripts de un solo uso fueron creados durante sesiones de desarrollo para ejecutar comandos de Git y ya cumplieron su función.

| Archivo | Tamaño | Fecha | Por qué es seguro |
|---------|--------|-------|-------------------|
| `COMMITEAR_CAMBIOS.bat` | 1.561 B | 2026-06-13 | Commit ya realizado |
| `COMMIT_FIXES_H1_H4.bat` | 1.304 B | 2026-06-14 | Commit pendiente (Director debe ejecutarlo primero) |
| `COMMIT_VALIDACION.bat` | 707 B | 2026-06-14 | Commit de docs ya incluido |
| `PUSH_GITHUB.bat` | 1.222 B | 2026-06-13 | Push ya realizado |
| `REPARAR_GIT.bat` | 1.207 B | 2026-06-13 | Reparación de Git ya finalizada |
| `commit_pendiente.bat` | 1.232 B | 2026-06-11 | Commit ya realizado |

⚠️ **Nota sobre `COMMIT_FIXES_H1_H4.bat`:** Antes de borrarlo, el Director debe ejecutarlo para hacer el commit de los hallazgos H-1 a H-4.

```bash
del "D:\Documentos\Martin\Gemelos Digital\COMMITEAR_CAMBIOS.bat"
del "D:\Documentos\Martin\Gemelos Digital\COMMIT_FIXES_H1_H4.bat"
del "D:\Documentos\Martin\Gemelos Digital\COMMIT_VALIDACION.bat"
del "D:\Documentos\Martin\Gemelos Digital\PUSH_GITHUB.bat"
del "D:\Documentos\Martin\Gemelos Digital\REPARAR_GIT.bat"
del "D:\Documentos\Martin\Gemelos Digital\commit_pendiente.bat"
```

**`.bat` que deben QUEDARSE (scripts de operación vivos):**
- `reiniciar_servidor.bat` — operación cotidiana
- `restart_server.bat` — operación cotidiana
- `run.bat` — punto de entrada de la simulación
- `start_server.bat` — arranque del servidor FastAPI
- `status_server.bat` — diagnóstico del servidor
- `stop_server.bat` — parada del servidor

---

### 1.4 Archivos de log vacíos (0 B)

| Archivo | Tamaño |
|---------|--------|
| `headless_check4.log` | 0 B |
| `headless_check5.log` | 0 B |
| `headless_check6.log` | 0 B |
| `launcher_debug.log` | 0 B |
| `test.log` | 0 B |
| `test_module.log` | 0 B |

Estos logs quedaron de diagnósticos pasados. Están vacíos — el proceso que los iba a llenar falló antes de escribir, o ya fueron procesados.

```bash
del "D:\Documentos\Martin\Gemelos Digital\headless_check4.log"
del "D:\Documentos\Martin\Gemelos Digital\headless_check5.log"
del "D:\Documentos\Martin\Gemelos Digital\headless_check6.log"
del "D:\Documentos\Martin\Gemelos Digital\launcher_debug.log"
del "D:\Documentos\Martin\Gemelos Digital\test.log"
del "D:\Documentos\Martin\Gemelos Digital\test_module.log"
```

**Logs de error con contenido (217 B) — `headless_check4_err.log`, etc.:** Tienen mensajes de error del motor headless. Son triviales pero pueden conservarse para referencia. Se incluyen en la sección "Dudoso" más abajo.

---

### 1.5 `.bak_trunc` vacío

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `src/subsystems/simulation/data_manager.py.bak_trunc` | 0 B | Backup truncado (quedó vacío por error durante escritura anti-FUSE) |

```bash
del "D:\Documentos\Martin\Gemelos Digital\src\subsystems\simulation\data_manager.py.bak_trunc"
```

---

### 1.6 `_mount_synctest.txt` — 57 B

**Qué es:** Archivo de prueba creado automáticamente por el driver de montura WinFsp/FUSE para verificar que la sincronización funciona.  
**Por qué es seguro:** Se regenera solo en el próximo ciclo de sync. No es dato del proyecto.

```bash
del "D:\Documentos\Martin\Gemelos Digital\_mount_synctest.txt"
```

---

### 1.7 `dummy_replay.jsonl` — 311 B

**Qué es:** Replay de prueba mínimo creado para testear el viewer sin correr la simulación real.  
**Por qué es seguro:** El motor genera `.jsonl` reales en `output/`. Este es un stub de desarrollo.

```bash
del "D:\Documentos\Martin\Gemelos Digital\dummy_replay.jsonl"
```

---

### 1.8 SQLite WAL/SHM — **solo con servidor DETENIDO**

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `warehouse.db-shm` | 32 KB | Shared memory map de SQLite WAL mode |
| `warehouse.db-wal` | 255 KB | Write-Ahead Log de transacciones pendientes |

⚠️ **ESTOS SON ACTIVOS CUANDO EL SERVIDOR ESTÁ CORRIENDO.** SQLite los usa para integridad transaccional. Si se borran con el servidor activo → corrupción de `warehouse.db`.

**Procedimiento correcto:**
1. Detener el servidor (`stop_server.bat`)
2. Abrir `warehouse.db` con SQLite una vez → auto-checkpoint escribe el WAL a la DB principal
3. Los archivos `-wal` y `-shm` desaparecen solos tras el checkpoint

**Alternativa:** `sqlite3 warehouse.db "PRAGMA wal_checkpoint(TRUNCATE);"` con el servidor detenido.

---

## CATEGORÍA 2: CONFIRMAR CON EL DIRECTOR

### 2.1 `_backup_iniciativa3/` — 20 archivos, 24 MB

**Qué es:** Carpeta de backup manual creada antes de la Iniciativa 3 (Fase 2, camión real). Contiene copias de `warehouse.db` y `warehouse.db-wal` del estado previo.

| Archivo | Tamaño |
|---------|--------|
| `warehouse.db.bak` | 192 KB |
| `warehouse.db-wal.bak` | 23.6 MB |

**Por qué puede borrarse:** La Iniciativa 3 ya está completada y committed en `main`. El `warehouse.db` actual es el estado correcto. Este backup es pre-Iniciativa-3 y no tiene utilidad de recuperación relevante.

**Por qué conservar:** Si en algún momento se necesita comparar comportamiento antes de Fase 2.

**Recomendación Cerebellum:** Borrar. Ya hay un tag de Git como punto de restauración si fuera necesario.

```bash
rmdir /s /q "D:\Documentos\Martin\Gemelos Digital\_backup_iniciativa3"
```

---

### 2.2 Configs de prueba y stress (`config_*.json`)

Se encontraron **12 archivos** de configuración de prueba/stress en la raíz, además del `config.json` canónico:

| Archivo | Tamaño | Naturaleza |
|---------|--------|------------|
| `config.json.backup` | 3.3 KB | Backup manual del config canónico |
| `config_calibrado_v1.json` | 4.1 KB | Perfil calibrado con tiempos reales (referencia para futuro) |
| `config_stress_baseline.json` | 4.7 KB | Config de stress test — baseline |
| `config_stress_f2.json` | 4.7 KB | Config de stress test — con Fase 2 |
| `config_stress_f3.json` | 4.7 KB | Config de stress test — con Fase 3 |
| `config_stress_tw.json` | 4.9 KB | Config de stress test — two-warehouse |
| `config_stress_tw_exec.json` | 5.2 KB | Config de stress test — TW ejecutado |
| `config_stress_tw_off.json` | 4.9 KB | Config de stress test — TW off |
| `config_stress_tw_v2.json` | 5.2 KB | Config de stress test — TW v2 |
| `config_test_congestion.json` | 2.1 KB | Test de congestión |
| `config_test_f2_small.json` | 2.1 KB | Test F2 pequeño |
| `config_test_from_fix_branch.json` | 1.9 KB | Config de rama de fix (posiblemente obsoleto) |
| `config_test_instrument.json` | 2.1 KB | Test de instrumentación |
| `config_test_quick.json` | 985 B | Test rápido (mínimo) |
| `config_test_volumen.json` | 1.1 KB | Test de volumen |
| `config_init1_test.json` | 0 B | Vacío — borrar seguro |

**Recomendación Cerebellum:**
- `config_init1_test.json` (0B): **seguro borrar** sin confirmar.
- `config.json.backup`: Su valor depende de si el `config.json` actual está bien. Sí lo está → borrar.
- `config_calibrado_v1.json`: **conservar** — es la referencia de tiempos calibrados que costó trabajo analizar. Moverlo a `docs/` o `configs/` en lugar de borrarlo.
- `config_stress_*.json` (7 archivos): El `_stress_harness.py` que los usa podría estar muerto. Si el harness ya no se usa, estos también son candidatos a borrar. Confirmar con Director.
- `config_test_*.json` (6 archivos): Candidatos a borrar — son fixtures de prueba de etapas pasadas.

```bash
# Solo seguros:
del "D:\Documentos\Martin\Gemelos Digital\config_init1_test.json"
```

---

### 2.3 Scripts de diagnóstico / harness de prueba

| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `_stress_harness.py` | 3.1 KB | Harness para correr stress tests (carga los `config_stress_*.json`) |
| `_tw_runner.py` | 2.1 KB | Runner de pruebas "two-warehouse" |
| `test_upload.py` | 909 B | Script de prueba del endpoint de upload del servidor |

**Por qué son dudosos:** El prefijo `_` indica código de soporte/diagnóstico. El `_stress_harness.py` tiene pareja en los `config_stress_*.json`. Si el Director ya no usa estos tests, son candidatos a poda.

**Recomendación:** Preguntar al Director si `_stress_harness.py` y `_tw_runner.py` siguen en uso activo o son vestigios de la etapa de calibración.

---

### 2.4 Logs de error con contenido

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `headless_check4_err.log` | 217 B | Error del motor headless (run 4) |
| `headless_check5_err.log` | 217 B | Error del motor headless (run 5) |
| `headless_check6_err.log` | 217 B | Error del motor headless (run 6) |

Son triviales (el mismo error en 3 runs). Se pueden borrar junto con sus pares vacíos.

---

### 2.5 `ordenes_prueba_real.json` — 2.8 KB

**Qué es:** Dataset de órdenes de trabajo "reales" para pruebas. Puede ser un fixture que el Director preparó manualmente para probar el motor con datos auténticos del almacén.

**Riesgo de borrar:** Si este fixture refleja datos reales del negocio que costó preparar, borrarlo es una pérdida. Si es sintético, es descartable.

**Recomendación:** Confirmar con Director si tiene valor como datos de referencia del negocio.

---

### 2.6 `optuna_study.db` — 128 KB

**Qué es:** Base de datos de Optuna con resultados de optimización de parámetros (la corrida de `run_optimization.py`).

**Por qué conservar:** Contiene el historial de trials de Optuna. Si el Director quiere retomar la optimización, este archivo le da ventaja (Optuna puede continuar desde donde dejó). Borrarlo obliga a empezar de cero.

**Por qué borrar:** 128 KB, y los resultados de la optimización ya deberían estar reflejados en `config.json` o `config_calibrado_v1.json`.

---

### 2.7 `server.pid` — 7 B

**Qué es:** Archivo con el PID del proceso del servidor FastAPI en ejecución. Lo escribe `server_manager.py` al arrancar el servidor.

**Por qué es dudoso:** Se regenera en cada arranque. Pero si existe con un PID inválido (servidor parado pero archivo persistió), puede confundir a `server_manager.py` al verificar el estado.

**Recomendación:** No borrarlo manualmente. Usar `stop_server.bat` que lo limpia correctamente.

---

### 2.8 `.cursorrules` — 1.7 KB

**Qué es:** Archivo de configuración de Cursor IDE con instrucciones para el asistente de Cursor. El `CLAUDE.md` (sección 3) lo marca explícitamente como desactualizado ("menciona archivos inexistentes como ACTIVE_SESSION_STATE.md").

**Por qué confirmar antes de borrar:** Aunque el contenido esté obsoleto, puede que el Director todavía use Cursor IDE y no quiera que desaparezca el archivo.

---

### 2.9 `requirements_tiled_migration.txt` — 291 B

**Qué es:** Archivo de requisitos pip específico para la migración de mapas Tiled TMX. La migración ya está completada y el código relevante está en `run_migration.py`.

**Recomendación:** Si las dependencias de migración ya están en `requirements.txt`, este archivo es redundante. Verificar antes de borrar.

---

## CATEGORÍA 3: NO TOCAR

Estos archivos parecen candidatos a limpieza pero son activos del sistema:

| Archivo | Por qué NO borrar |
|---------|-------------------|
| `config.json` | Fuente de verdad canónica del backend |
| `warehouse.db` | Base de datos principal (datos de stock, WOs) |
| `CLAUDE.md` | Instrucciones activas del proyecto |
| `AUDITORIA.md` | Diagnóstico completo del proyecto |
| `README.md` | Documentación del proyecto |
| `Makefile` | Comandos de build/run |
| `requirements.txt` | Dependencias del proyecto |
| `.gitignore` | Config de Git |
| `dashboard_theme.json` | Tema del dashboard (¿vivo?) — confirmar |
| `run_migration.py` | Script de migración Excel → SQLite (vivo) |
| `server_manager.py` | Gestor del servidor FastAPI (vivo) |
| `start_hidden.py` | Arranque silencioso del servidor (vivo) |
| `simulation_buffer.py` | Buffer de simulación usado por event_generator (vivo) |
| `visualizer.py` | Generador de heatmap por subprocess (vivo) |
| `setup.py` | Configuración del paquete Python |
| `start_server.bat` y otros .bat operativos | Scripts de operación cotidiana |

---

## PLAN DE EJECUCIÓN SUGERIDO

### Fase 1 — Ejecutar ya (0 riesgo):
```batch
:: 1. Detener servidor
stop_server.bat

:: 2. Borrar .fuse_hidden* (con servidor detenido)
del /q "D:\Documentos\Martin\Gemelos Digital\.fuse_hidden*"

:: 3. Borrar logs vacíos
del "D:\Documentos\Martin\Gemelos Digital\headless_check*.log"
del "D:\Documentos\Martin\Gemelos Digital\launcher_debug.log"
del "D:\Documentos\Martin\Gemelos Digital\test.log"
del "D:\Documentos\Martin\Gemelos Digital\test_module.log"

:: 4. Borrar .bak_trunc vacío
del "D:\Documentos\Martin\Gemelos Digital\src\subsystems\simulation\data_manager.py.bak_trunc"

:: 5. Borrar archivos triviales
del "D:\Documentos\Martin\Gemelos Digital\_mount_synctest.txt"
del "D:\Documentos\Martin\Gemelos Digital\dummy_replay.jsonl"
del "D:\Documentos\Martin\Gemelos Digital\config_init1_test.json"
```

### Fase 2 — Después de confirmar con Director:
- Vaciar `output/` (598 MB)
- Borrar `.bat` de un solo uso (esperar a que se ejecute `COMMIT_FIXES_H1_H4.bat` primero)
- Borrar `_backup_iniciativa3/`
- Decidir sobre `config_stress_*/config_test_*`

### Fase 3 — Git tag antes de borrar en masa:
```bash
git tag pre-limpieza-2026-06-14
git push origin pre-limpieza-2026-06-14
```
Así cualquier archivo borrado se puede recuperar del historial si fuera necesario.

---

*Documento generado por Cerebellum | Análisis: 2026-06-14 | Sin acciones ejecutadas*
