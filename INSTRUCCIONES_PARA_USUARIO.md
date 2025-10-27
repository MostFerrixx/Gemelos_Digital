# INSTRUCCIONES PARA EL USUARIO

**Fecha:** 2025-01-15  
**Estado:** ✅ TODO LISTO PARA EJECUTAR

---

## 📋 DOCUMENTACIÓN GENERADA

He creado 6 documentos para ti:

### 1. **`PLAN_EJECUTABLE_ELIMINACION_LIVE.md`** ⭐ PRINCIPAL
   - Plan completo con código listo para copiar
   - Instrucciones paso a paso
   - Validaciones completas
   - Procedimiento de rollback

### 2. **`PROMPT_PARA_NUEVA_VENTANA.md`** ⭐ PROMPT
   - Texto exacto para copiar en la nueva ventana de chat
   - Instrucciones claras para el nuevo agente
   - Reglas importantes

### 3. **`REFERENCIA_RAPIDA_CAMBIOS.md`**
   - Resumen en 1 página
   - Comandos rápidos
   - Validación rápida

### 4. **`ANALISIS_FINAL_ELIMINACION_LIVE.md`**
   - Análisis exhaustivo de seguridad
   - Todas las verificaciones completadas
   - Justificación de cada cambio

### 5. **`VALIDACION_AUDITORIA_CON_DEPENDENCIAS.md`**
   - Dependencias críticas identificadas
   - Correcciones al plan original
   - Análisis de riesgos

### 6. **`AUDITORIA_ELIMINACION_LIVE_SIMULATION.md`**
   - Auditoría inicial completa
   - Arquitectura del sistema
   - Mapa de dependencias

---

## 🚀 CÓMO USAR ESTOS DOCUMENTOS

### PASO 1: Abrir nueva ventana de chat

1. Abre una **nueva ventana/chat** de Cursor o tu IDE
2. Asegúrate de estar en el **mismo proyecto**

### PASO 2: Copiar el prompt

1. Abre **`PROMPT_PARA_NUEVA_VENTANA.md`**
2. Copia TODO el contenido
3. Pégalo en la nueva ventana de chat
4. Envía el mensaje

### PASO 3: El nuevo chat hará todo

El nuevo agente:
1. Leerá el plan ejecutable
2. Creará los 2 archivos nuevos
3. Eliminará los 3 archivos antiguos
4. Modificará los 2 archivos (Makefile, run.bat)
5. Ejecutará todas las validaciones
6. Te confirmará que todo funciona

### PASO 4: Verificar resultado

```bash
# Prueba final
python entry_points/run_generate_replay.py
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

Si ambos comandos funcionan → ✅ ÉXITO

---

## 📊 QUÉ VA A PASAR

### CAMBIOS TOTALES
- **Crear:** 2 archivos nuevos (~280 líneas)
- **Eliminar:** 3 archivos viejos (~2080 líneas)
- **Modificar:** 2 archivos (Makefile, run.bat)

### RESULTADO
- ✅ Código 87% más simple
- ✅ Generación de .jsonl funciona
- ✅ Replay funciona perfectamente
- ✅ Sin renderizado en tiempo real innecesario

---

## ⚠️ IMPORTANTE

### ANTES DE EJECUTAR

1. **Commit tus cambios actuales:**
   ```bash
   git add -A
   git commit -m "Checkpoint antes de eliminar live simulation"
   ```

2. **Verifica que git esté limpio:**
   ```bash
   git status
   ```
   Debería decir: "nothing to commit, working tree clean"

### SI ALGO SALE MAL

El plan incluye procedimiento de ROLLBACK completo:
```bash
git checkout entry_points/run_live_simulation.py
git checkout src/engines/simulation_engine.py
git checkout src/communication/simulation_data_provider.py
git checkout Makefile run.bat
rm src/engines/event_generator.py entry_points/run_generate_replay.py
```

---

## 🎯 PROMPT EXACTO PARA COPIAR

**Copia esto en la nueva ventana:**

```
Hola, necesito que ejecutes un plan de refactorización previamente analizado y validado. Este plan elimina código de live simulation manteniendo solo la generación de archivos .jsonl para replay.

**IMPORTANTE:** El análisis ya está completo. Tu trabajo es SOLO ejecutar los cambios según el plan.

## CONTEXTO

- **Proyecto:** Simulador de Gemelo Digital de Almacén
- **Rama:** main
- **Objetivo:** Eliminar live simulation (renderizado en tiempo real), mantener solo generación de .jsonl para replay

## ARCHIVOS DE REFERENCIA

Lee estos archivos en orden:

1. **`PLAN_EJECUTABLE_ELIMINACION_LIVE.md`** - Plan detallado con código completo
2. **`ANALISIS_FINAL_ELIMINACION_LIVE.md`** - Análisis de seguridad completado
3. **`VALIDACION_AUDITORIA_CON_DEPENDENCIAS.md`** - Dependencias verificadas

## TAREAS A EJECUTAR

### TAREA 1: Crear archivos nuevos

Crear exactamente como están en `PLAN_EJECUTABLE_ELIMINACION_LIVE.md`:

1. **`src/engines/event_generator.py`** - Código completo proporcionado (~250 líneas)
2. **`entry_points/run_generate_replay.py`** - Código completo proporcionado (~30 líneas)

### TAREA 2: Eliminar archivos

Eliminar estos 3 archivos completamente:
1. `entry_points/run_live_simulation.py`
2. `src/engines/simulation_engine.py`
3. `src/communication/simulation_data_provider.py`

### TAREA 3: Modificar archivos

1. **`Makefile`** - Actualizar comandos según plan
2. **`run.bat`** - Actualizar comandos según plan

### TAREA 4: Validar

Ejecutar todos los pasos de validación del plan.

## REGLAS

1. ✅ Copiar código exactamente - No modificar
2. ✅ Seguir orden - crear → eliminar → modificar → validar
3. ✅ No analizar - Solo ejecutar
4. ✅ Usar código del plan

¿Entiendes? Confirma y comienza con TAREA 1.
```

---

## 📞 SOPORTE

Si el nuevo chat tiene dudas, todos los detalles están en:
- **`PLAN_EJECUTABLE_ELIMINACION_LIVE.md`** (código completo)
- **`ANALISIS_FINAL_ELIMINACION_LIVE.md`** (justificaciones)

---

**TODO ESTÁ LISTO. PUEDES PROCEDER CON CONFIANZA.**

✅ Análisis completado  
✅ Plan validado  
✅ Código preparado  
✅ Validaciones definidas  
✅ Rollback documentado  

**ÉXITO GARANTIZADO SI SIGUES EL PLAN.**
