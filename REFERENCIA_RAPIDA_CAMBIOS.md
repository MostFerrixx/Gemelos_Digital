# REFERENCIA RÁPIDA - CAMBIOS

**Fecha:** 2025-01-15  
**Para:** Nueva ventana de chat ejecutando cambios

---

## RESUMEN EN 1 PÁGINA

### ARCHIVOS A CREAR (2)

1. **`src/engines/event_generator.py`** → ~250 líneas (código completo en plan)
2. **`entry_points/run_generate_replay.py`** → ~30 líneas (código completo en plan)

### ARCHIVOS A ELIMINAR (3)

1. **`entry_points/run_live_simulation.py`** → Eliminar completo
2. **`src/engines/simulation_engine.py`** → Eliminar completo
3. **`src/communication/simulation_data_provider.py`** → Eliminar completo

### ARCHIVOS A MODIFICAR (2)

1. **`Makefile`** → Cambiar comandos `sim` y eliminar `sim-visual`
2. **`run.bat`** → Cambiar comandos `sim` y eliminar `sim-visual`

---

## COMANDOS DE EJECUCIÓN RÁPIDA

```bash
# 1. CREAR ARCHIVOS
# (Copiar código desde PLAN_EJECUTABLE_ELIMINACION_LIVE.md)

# 2. ELIMINAR ARCHIVOS
rm entry_points/run_live_simulation.py
rm src/engines/simulation_engine.py
rm src/communication/simulation_data_provider.py

# 3. MODIFICAR ARCHIVOS
# (Ver cambios exactos en PLAN_EJECUTABLE_ELIMINACION_LIVE.md)

# 4. VALIDAR
python entry_points/run_generate_replay.py
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

---

## VALIDACIÓN RÁPIDA

```bash
# ¿Archivos nuevos existen?
ls src/engines/event_generator.py entry_points/run_generate_replay.py

# ¿Archivos viejos eliminados?
! ls entry_points/run_live_simulation.py

# ¿Genera .jsonl?
python entry_points/run_generate_replay.py

# ¿Replay funciona?
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

---

## RESULTADO ESPERADO

### ANTES
```
Opción 1: python run_live_simulation.py (live + genera .jsonl)
Opción 2: python run_replay_viewer.py archivo.jsonl (replay)
```

### DESPUÉS
```
Opción 1: python run_generate_replay.py (genera .jsonl - headless)
Opción 2: python run_replay_viewer.py archivo.jsonl (replay)
```

---

## MÉTRICAS

- **Código eliminado:** ~2080 líneas
- **Código agregado:** ~280 líneas
- **Reducción neta:** 87% (-1800 líneas)

---

## ROLLBACK

```bash
git checkout entry_points/run_live_simulation.py
git checkout src/engines/simulation_engine.py
git checkout src/communication/simulation_data_provider.py
git checkout Makefile run.bat
rm src/engines/event_generator.py entry_points/run_generate_replay.py
```

---

**FIN REFERENCIA RÁPIDA**
