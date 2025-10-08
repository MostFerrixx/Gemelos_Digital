# 📋 REGLAS OBLIGATORIAS DE MANTENIMIENTO DE DOCUMENTACIÓN

**Para TODAS las sesiones de Claude Code**

---

## 🚨 **REGLAS OBLIGATORIAS - SIN EXCEPCIONES**

### **REGLA #1: ACTUALIZACIÓN OBLIGATORIA AL FINALIZAR SESIÓN**

**ANTES de terminar cualquier sesión, DEBES:**

1. **Leer ACTIVE_SESSION_STATE.md actual**
2. **Actualizar con el estado real de la sesión:**
   - ✅ Marcar fases completadas
   - ✅ Actualizar próxima acción
   - ✅ Documentar problemas encontrados
   - ✅ Actualizar tiempo estimado restante
3. **Si completaste una fase importante:** Actualizar HANDOFF.md
4. **Si cambió algo técnico:** Actualizar INSTRUCCIONES.md

**COMANDO OBLIGATORIO:**
```bash
# Verificar estado antes de actualizar
git status
git log --oneline -3

# Actualizar documentación
# (Usar herramientas de edición para actualizar los .md)
```

---

### **REGLA #2: VALIDACIÓN OBLIGATORIA AL INICIAR SESIÓN**

**AL INICIAR cualquier sesión, DEBES:**

1. **Leer los 3 archivos clave en orden**
2. **Verificar que el estado documentado coincide con la realidad:**
   - ✅ Git status coincide con documentación
   - ✅ Archivos mencionados existen
   - ✅ Estado del proyecto es correcto
3. **Si hay inconsistencias:** Actualizar documentación inmediatamente

**COMANDO OBLIGATORIO:**
```bash
# Validar estado documentado vs realidad
git status
git log --oneline -3
ls -la [ARCHIVOS_MENCIONADOS_EN_DOCUMENTACION]
```

---

### **REGLA #3: ACTUALIZACIÓN EN TIEMPO REAL**

**DURANTE la sesión, DEBES actualizar cuando:**

- ✅ **Completas una fase:** Marcar inmediatamente en ACTIVE_SESSION_STATE.md
- ✅ **Encuentras un problema:** Documentar en ACTIVE_SESSION_STATE.md
- ✅ **Cambias de enfoque:** Actualizar próxima acción
- ✅ **Modificas archivos técnicos:** Actualizar INSTRUCCIONES.md

---

### **REGLA #4: TEMPLATE OBLIGATORIO**

**SIEMPRE usa estos templates para actualizar:**

#### **Para ACTIVE_SESSION_STATE.md:**
```markdown
# 🚀 ESTADO DE SESIÓN ACTIVA - [NOMBRE_TAREA]

**Fecha:** [FECHA_ACTUAL]
**Sesión:** [NOMBRE_SESIÓN]
**Estado:** [ESTADO_ACTUAL]

## 📋 CONTEXTO INMEDIATO
### TAREA ACTUAL: [DESCRIPCIÓN_CLARA]
### PROBLEMA IDENTIFICADO: [LISTA_PROBLEMAS]
### SOLUCIÓN DISEÑADA: [LISTA_SOLUCIONES]

## 🛠️ PLAN DE IMPLEMENTACIÓN
### FASE 1: [NOMBRE] ([TIEMPO]) - ✅/⏳
- [ ] Tarea 1
- [ ] Tarea 2

### PRÓXIMO PASO: [ACCIÓN_INMEDIATA]
**ESTADO:** ✅ [ESTADO_ACTUAL]
```

#### **Para HANDOFF.md:**
```markdown
## What Has Been Done
✅ **[NUEVA_FASE]:** [DESCRIPCIÓN]
- [Detalle 1]
- [Detalle 2]

## What Needs to Be Done Next
### IMMEDIATE TASK: [NUEVA_TAREA] ✅/⏳
**Próximo Paso:** [DESCRIPCIÓN]
```

---

## 🔧 **HERRAMIENTAS OBLIGATORIAS**

### **COMANDOS DE VALIDACIÓN (EJECUTAR SIEMPRE):**
```bash
# 1. Verificar estado del proyecto
git status
git log --oneline -3

# 2. Verificar archivos mencionados en documentación
ls -la [ARCHIVOS_MENCIONADOS]

# 3. Verificar estructura de directorios
find . -name "*.md" -type f | head -10
```

### **COMANDOS DE ACTUALIZACIÓN (EJECUTAR CUANDO SEA NECESARIO):**
```bash
# Actualizar fecha en archivos
# (Usar herramientas de edición para cambiar fechas)

# Verificar consistencia
grep -n "Fecha:" *.md
grep -n "Estado:" *.md
```

---

## ⚠️ **SANCIONES POR INCUMPLIMIENTO**

**Si NO actualizas la documentación:**

1. **Primera vez:** Advertencia y actualización obligatoria
2. **Segunda vez:** Sesión marcada como "incompleta"
3. **Tercera vez:** Requerir revisión completa de documentación

**CRITERIOS DE ÉXITO:**
- ✅ Documentación actualizada al final de cada sesión
- ✅ Estado documentado coincide con realidad
- ✅ Próxima sesión puede continuar sin problemas
- ✅ No hay información obsoleta o contradictoria

---

## 📝 **CHECKLIST OBLIGATORIO AL FINALIZAR SESIÓN**

**ANTES de decir "sesión completada", verifica:**

- [ ] ACTIVE_SESSION_STATE.md actualizado con estado real
- [ ] Fases completadas marcadas como ✅
- [ ] Próxima acción claramente definida
- [ ] Problemas encontrados documentados
- [ ] Tiempo estimado restante actualizado
- [ ] HANDOFF.md actualizado (si aplica)
- [ ] INSTRUCCIONES.md actualizado (si aplica)
- [ ] Git status verificado
- [ ] Archivos mencionados existen
- [ ] Documentación es consistente

**SOLO después de completar este checklist puedes finalizar la sesión.**

---

## 🎯 **OBJETIVO FINAL**

**Garantizar que cada nueva sesión pueda:**
1. **Entender el contexto** en menos de 5 minutos
2. **Continuar exactamente** donde quedó la sesión anterior
3. **No perder tiempo** en información obsoleta
4. **Ejecutar inmediatamente** el plan aprobado

**¡ESTAS REGLAS SON OBLIGATORIAS Y NO TIENEN EXCEPCIONES!**
