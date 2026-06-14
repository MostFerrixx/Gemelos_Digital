# CARPETA DE CUARENTENA
**Fecha:** 2026-06-14  
**Movido por:** Cerebellum (análisis: `docs/LIMPIEZA_ARCHIVOS_BASURA.md`)  
**Estado:** Cuarentena — NO borrar hasta validar que el programa funciona sin estos archivos

El programa fue verificado funcionando después de mover estos archivos.
Para revertir cualquier ítem: `mv basura/<subcarpeta>/<archivo> <ruta_original>`

---

## Origen de cada ítem

### `bats_consumidos/` — Scripts .bat de un solo uso ya ejecutados
| Archivo | Ruta original | Motivo |
|---------|--------------|--------|
| `COMMITEAR_CAMBIOS.bat` | `/` | Commit de junio 2026-06-13, ya realizado |
| `PUSH_GITHUB.bat` | `/` | Push de 2026-06-13, ya realizado |
| `REPARAR_GIT.bat` | `/` | Reparación de Git de 2026-06-13, ya realizada |
| `commit_pendiente.bat` | `/` | Commit de 2026-06-11, ya realizado |

### `configs_prueba/` — Configuraciones de prueba y stress obsoletas
| Archivo | Ruta original | Motivo |
|---------|--------------|--------|
| `config.json.backup` | `/` | Backup manual de config.json (el original está limpio) |
| `config_calibrado_v1.json` | `/` | Perfil calibrado de tiempos reales v1 (si se necesita referencia, está aquí) |
| `config_init1_test.json` | `/` | 0 bytes, vacío |
| `config_stress_baseline.json` | `/` | Stress test — baseline |
| `config_stress_f2.json` | `/` | Stress test — con Fase 2 |
| `config_stress_f3.json` | `/` | Stress test — con Fase 3 |
| `config_stress_tw.json` | `/` | Stress test — two-warehouse |
| `config_stress_tw_exec.json` | `/` | Stress test — TW ejecutado |
| `config_stress_tw_off.json` | `/` | Stress test — TW off |
| `config_stress_tw_v2.json` | `/` | Stress test — TW v2 |
| `config_test_congestion.json` | `/` | Test de congestión (fixture de desarrollo) |
| `config_test_f2_small.json` | `/` | Test Fase 2 pequeño |
| `config_test_from_fix_branch.json` | `/` | Config de rama de fix (obsoleto) |
| `config_test_instrument.json` | `/` | Test de instrumentación |
| `config_test_quick.json` | `/` | Test rápido mínimo |
| `config_test_volumen.json` | `/` | Test de volumen |

### `logs/` — Archivos de log vacíos o triviales
| Archivo | Ruta original | Motivo |
|---------|--------------|--------|
| `headless_check4.log` | `/` | Vacío (0 bytes) |
| `headless_check5.log` | `/` | Vacío (0 bytes) |
| `headless_check6.log` | `/` | Vacío (0 bytes) |
| `headless_check4_err.log` | `/` | Error trivial del motor headless (217 bytes) |
| `headless_check5_err.log` | `/` | Error trivial del motor headless (217 bytes) |
| `headless_check6_err.log` | `/` | Error trivial del motor headless (217 bytes) |
| `launcher_debug.log` | `/` | Vacío (0 bytes) |
| `test.log` | `/` | Vacío (0 bytes) |
| `test_module.log` | `/` | Vacío (0 bytes) |

### `scripts_diagnostico/` — Scripts de diagnóstico y testing pasados
| Archivo | Ruta original | Motivo |
|---------|--------------|--------|
| `_stress_harness.py` | `/` | Harness de stress testing (pareja de config_stress_*.json) |
| `_tw_runner.py` | `/` | Runner de pruebas two-warehouse |
| `test_upload.py` | `/` | Script de prueba del endpoint de upload |

### `varios/` — Archivos varios sin uso activo
| Archivo | Ruta original | Motivo |
|---------|--------------|--------|
| `dashboard_theme.json` | `/` | Solo referenciado por tests muertos y _legacy/ |
| `.cursorrules` | `/` | Config de Cursor IDE, desactualizado (CLAUDE.md sec.3 lo marca así) |
| `requirements_tiled_migration.txt` | `/` | Migración Tiled ya completada, deps ya en requirements.txt |
| `dummy_replay.jsonl` | `/` | Replay de prueba mínimo (stub de desarrollo) |
| `ordenes_prueba_real.json` | `/` | Dataset de órdenes de prueba (no referenciado en código vivo) |
| `optuna_study.db` | `/` | DB de Optuna (solo usada por run_optimization.py, no por pipeline principal) |
| `_mount_synctest.txt` | `/` | Archivo de prueba de sincronización FUSE (se regenera solo) |
| `data_manager.py.bak_trunc` | `src/subsystems/simulation/` | Backup truncado vacío (0 bytes) |

### `output/` — Corridas de simulación antiguas (598 MB)
Carpeta completa movida desde `/output/`. Contenía 646 archivos en 60+ subcarpetas  
`simulation_YYYYMMDD_HHMMSS/` desde 2025-09-23 hasta 2026-05-xx.  
La carpeta `/output/` fue recreada vacía para que el motor pueda escribir nuevas corridas.  
**Para recuperar una corrida específica:** `mv basura/output/simulation_FECHA /output/`

### `_backup_iniciativa3/` — Backup de DB pre-Iniciativa 3 (24 MB)
Carpeta completa movida desde `/_backup_iniciativa3/`.  
Contenía `warehouse.db.bak` (192 KB) y `warehouse.db-wal.bak` (23.6 MB) del estado  
pre-Fase 2 (antes del desarrollo del sistema de camión real).  
El `warehouse.db` actual es la versión correcta post-Iniciativa-3.

---

## Qué NO se pudo mover (pendiente para el Director en Windows)

### `.fuse_hidden*` — 7.037 archivos, ~220 MB
Son artefactos del driver WinFsp/FUSE. El sandbox Linux no puede moverlos (EPERM).  
**Para limpiarlos desde Windows:** abrir la carpeta del proyecto en Explorer, ordenar por  
nombre, seleccionar todos los `.fuse_hidden*` y eliminar. O desde PowerShell:
```powershell
cd "D:\Documentos\Martin\Gemelos Digital"
Get-ChildItem -Filter ".fuse_hidden*" | Remove-Item -Force
```
**Precaución:** hacer esto con el servidor detenido.

### `warehouse.db-shm` y `warehouse.db-wal` (SQLite WAL)
No se movieron — son activos del servidor FastAPI en ejecución. Para limpiarlos  
correctamente: detener el servidor → hacer checkpoint SQLite → desaparecen solos.

---

## Para hacer permanente la limpieza

Cuando el Director confirme que todo funciona bien:
```bash
# Borrar esta carpeta completa (en Windows):
rmdir /s /q "D:\Documentos\Martin\Gemelos Digital\basura"
```
O desde PowerShell:
```powershell
Remove-Item -Recurse -Force "D:\Documentos\Martin\Gemelos Digital\basura"
```
