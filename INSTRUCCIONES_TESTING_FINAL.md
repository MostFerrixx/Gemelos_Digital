# INSTRUCCIONES PARA TESTING FINAL

**Fecha:** 2025-10-07  
**Estado:** ✅ TODOS LOS FIXES APLICADOS - Listo para probar

---

## ✅ CAMBIOS COMPLETADOS

### 1. **FASE 1: Conexión replay_buffer** ✅
- `warehouse.py`: Agregado parámetro `replay_buffer`
- `warehouse.py`: `registrar_evento()` escribe a `replay_buffer`
- `simulation_engine.py`: Pasa `replay_buffer` al almacén
- `simulation_engine.py`: Bucle consumidor copia eventos

### 2. **BUGFIX: Atributos WorkOrder** ✅
- Agregadas properties: `sku_id`, `sku_name`, `cantidad_total`, `volumen_restante`, `staging_id`, `work_group`

### 3. **BUGFIX: Bucle infinito** ✅
- `warehouse.py`: `simulacion_ha_terminado()` ahora usa lógica del dispatcher
- `dispatcher.py`: Reducido spam de logs (solo cada 10 segundos)
- `operators.py`: Verifica terminación antes de esperar

---

## 🚀 CÓMO PROBAR

### OPCIÓN 1: Test Rápido (3 órdenes)

```bash
python test_quick_jsonl.py
```

**Tiempo esperado:** 10-30 segundos  
**Debe mostrar:**
```
[ALMACEN] Simulacion finalizada en t=XXX.XX
[DISPATCHER-PROCESS] Simulacion finalizada
[TEST] Simulacion completada exitosamente
[TEST] Directorio de salida: output/simulation_YYYYMMDD_HHMMSS
[TEST] Archivos generados (4-5):
  - replay_YYYYMMDD_HHMMSS.jsonl (XXX bytes)
  - simulacion_completada_YYYYMMDD_HHMMSS.json
  - ...
[TEST] Inspeccionando replay_YYYYMMDD_HHMMSS.jsonl:
  Total lineas: XX
  Tipos de eventos:
    SIMULATION_START: 1
    work_order_update: XX
    SIMULATION_END: 1
```

### OPCIÓN 2: Simulación Normal (50 órdenes)

```bash
# Ejecutar con config normal
python entry_points/run_live_simulation.py --headless
```

**Tiempo esperado:** 1-3 minutos  
**Debe terminar sin bucle infinito**

---

## 📊 VERIFICACIÓN DE ÉXITO

### ✅ Criterios de Éxito:

1. **Simulación termina** (no bucle infinito)
   ```
   [ALMACEN] Simulacion finalizada en t=XXX.XX
   ```

2. **Se crea carpeta output/**
   ```
   output/simulation_YYYYMMDD_HHMMSS/
   ```

3. **Archivo .jsonl existe**
   ```
   replay_YYYYMMDD_HHMMSS.jsonl
   ```

4. **Archivo .jsonl tiene contenido**
   ```bash
   # Ver archivo (PowerShell)
   Get-Content output/simulation_*/replay_*.jsonl | Select-Object -First 5
   
   # Debe mostrar:
   # {"event_type":"SIMULATION_START",...}
   # {"type":"work_order_update",...}
   # ...
   ```

5. **Tipos de eventos correctos**
   - `SIMULATION_START` (1 vez)
   - `work_order_update` (múltiples veces)
   - `SIMULATION_END` (1 vez)

---

## 🔍 COMANDOS DE INSPECCIÓN

### Ver última carpeta generada:
```powershell
Get-ChildItem output/ | Sort-Object LastWriteTime | Select-Object -Last 1
```

### Ver archivos en carpeta:
```powershell
Get-ChildItem output/simulation_*/ | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-ChildItem
```

### Inspeccionar JSONL:
```powershell
# Ver primeras 5 líneas
Get-Content output/simulation_*/replay_*.jsonl | Select-Object -First 5

# Contar líneas
(Get-Content output/simulation_*/replay_*.jsonl).Count

# Buscar tipos de eventos
Get-Content output/simulation_*/replay_*.jsonl | Select-String '"type":"'
```

---

## 🐛 SI ALGO FALLA

### Problema: Simulación no termina (bucle infinito)
**Solución:** Espera 30 segundos, si sigue corriendo presiona `Ctrl+C`

**Verificar:**
```bash
# Revisar log
cat PROBLEMA_BUCLE_INFINITO.md
```

### Problema: No se crea carpeta output/
**Causa:** Simulación falló antes de completar

**Revisar:**
- Error en consola
- Verificar que `config.json` esté bien

### Problema: Archivo .jsonl vacío o con solo 2 líneas
**Causa:** No se capturaron eventos

**Verificar:**
```bash
# Ver contenido
Get-Content output/simulation_*/replay_*.jsonl
```

---

## 📝 DOCUMENTOS CREADOS

| Documento | Descripción |
|-----------|-------------|
| `AUDITORIA_JSONL_GENERATION.md` | Diagnóstico completo del problema |
| `PLAN_REPARACION_JSONL.md` | Plan de reparación detallado |
| `CAMBIOS_IMPLEMENTADOS_FASE1.md` | Cambios realizados |
| `VALIDACION_CAMBIOS.md` | Validación de código |
| `REPORTE_FINAL_REPARACION.md` | Resumen ejecutivo |
| `PROBLEMA_BUCLE_INFINITO.md` | Análisis del bucle infinito |
| `INSTRUCCIONES_TESTING_FINAL.md` | Este archivo |

---

## 🎯 PRÓXIMOS PASOS DESPUÉS DEL TESTING

### Si el testing es exitoso (archivo .jsonl se genera):

1. **Probar con Replay Viewer:**
   ```bash
   python entry_points/run_replay_viewer.py output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
   ```

2. **Opcional - FASE 2:**
   - Agregar eventos `estado_agente` para ver movimiento de operarios
   - Documentado en `PLAN_REPARACION_JSONL.md`

3. **Commit de cambios:**
   ```bash
   git add src/subsystems/simulation/warehouse.py
   git add src/subsystems/simulation/dispatcher.py
   git add src/subsystems/simulation/operators.py
   git add src/engines/simulation_engine.py
   git commit -m "fix(replay): Conectar replay_buffer y corregir terminacion de simulacion"
   ```

---

## ✅ RESUMEN

**TODOS LOS CAMBIOS APLICADOS:**
- ✅ Conexión replay_buffer <-> registrar_evento()
- ✅ Properties de WorkOrder
- ✅ Fix bucle infinito
- ✅ Reducción spam de logs

**LISTO PARA PROBAR:**
```bash
python test_quick_jsonl.py
```

**TIEMPO ESPERADO:** < 30 segundos

---

**¡BUENA SUERTE CON EL TESTING!** 🚀

