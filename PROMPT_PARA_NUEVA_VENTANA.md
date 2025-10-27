# PROMPT PARA NUEVA VENTANA DE CHAT

**Copiar y pegar esto en la nueva ventana de chat:**

---

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

1. **`src/engines/event_generator.py`**
   - Código completo proporcionado en el plan
   - ~250 líneas
   - NO modificar nada, copiar exactamente

2. **`entry_points/run_generate_replay.py`**
   - Código completo proporcionado en el plan
   - ~30 líneas
   - NO modificar nada, copiar exactamente

### TAREA 2: Eliminar archivos

Eliminar estos 3 archivos completamente:

1. `entry_points/run_live_simulation.py`
2. `src/engines/simulation_engine.py`
3. `src/communication/simulation_data_provider.py`

### TAREA 3: Modificar archivos

1. **`Makefile`** - Actualizar comandos según plan
2. **`run.bat`** - Actualizar comandos según plan

Los cambios exactos están en `PLAN_EJECUTABLE_ELIMINACION_LIVE.md`.

### TAREA 4: Validar

Ejecutar todos los pasos de validación en orden:
1. Verificar archivos creados
2. Verificar archivos eliminados
3. Generar .jsonl de prueba
4. Verificar .jsonl
5. Probar replay viewer
6. Verificar comandos make

## REGLAS IMPORTANTES

1. ✅ **Copiar código exactamente** - No modificar nada del código proporcionado
2. ✅ **Seguir orden** - Ejecutar tareas en orden: crear → eliminar → modificar → validar
3. ✅ **No analizar** - El análisis ya está completo, solo ejecutar
4. ✅ **No optimizar** - No intentar mejorar el código, solo copiarlo
5. ✅ **Usar código del plan** - Todo el código está en `PLAN_EJECUTABLE_ELIMINACION_LIVE.md`

## VERIFICACIÓN FINAL

Después de completar todas las tareas, confirmar:
- [ ] 2 archivos creados
- [ ] 3 archivos eliminados
- [ ] 2 archivos modificados
- [ ] Todas las validaciones pasadas
- [ ] Archivo .jsonl generado exitosamente
- [ ] Replay viewer funciona

## PREGUNTA INICIAL

¿Entiendes las tareas? Confirma que:
1. Leíste `PLAN_EJECUTABLE_ELIMINACION_LIVE.md`
2. Vas a copiar el código exactamente como está
3. Vas a ejecutar las tareas en orden
4. Vas a validar cada paso

Si todo está claro, responde: "Entendido. Voy a ejecutar el plan paso a paso." y comienza con TAREA 1.

---

**FIN DEL PROMPT**
