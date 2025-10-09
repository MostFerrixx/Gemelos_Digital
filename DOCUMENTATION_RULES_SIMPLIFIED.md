# 📋 REGLAS DE DOCUMENTACIÓN SIMPLIFICADAS

**Proyecto:** Simulador de Gemelo Digital de Almacén  
**Versión:** Simplificada - Solo archivos esenciales  
**Última actualización:** 2025-10-08  

---

## 🚀 ARCHIVOS ESENCIALES (SOLO 4 ARCHIVOS)

### **AL INICIAR CADA SESIÓN (OBLIGATORIO):**

1. **`ACTIVE_SESSION_STATE.md`** - Estado actual de la sesión
2. **`HANDOFF.md`** - Overview completo del proyecto  
3. **`INSTRUCCIONES.md`** - Instrucciones técnicas del sistema
4. **`PLAN_SISTEMA_SLOTS_CONFIGURACION.md`** - Plan actual pendiente (si aplica)

### **VERIFICACIÓN OBLIGATORIA:**
```bash
git status
git log --oneline -3
```

---

## 📁 ESTRUCTURA SIMPLIFICADA

```
📁 Documentación Esencial
├── 📄 ACTIVE_SESSION_STATE.md     ← Estado actual
├── 📄 HANDOFF.md                  ← Overview del proyecto
├── 📄 INSTRUCCIONES.md            ← Instrucciones técnicas
├── 📄 PLAN_SISTEMA_SLOTS_CONFIGURACION.md ← Plan pendiente
└── 📁 archived/                   ← Documentación completada
```

---

## 🔄 ACTUALIZACIÓN DURANTE SESIÓN

### **Actualizar inmediatamente cuando:**
- ✅ Completas una fase importante
- ✅ Encuentras un problema nuevo
- ✅ Cambias de enfoque o tarea
- ✅ Modificas archivos técnicos

### **Archivos a actualizar:**
- **Siempre:** `ACTIVE_SESSION_STATE.md`
- **Si completas fase importante:** `HANDOFF.md`
- **Si cambias algo técnico:** `INSTRUCCIONES.md`

---

## ✅ CHECKLIST AL FINALIZAR SESIÓN

**ANTES de decir "sesión completada", verifica:**

- [ ] `ACTIVE_SESSION_STATE.md` actualizado con estado real
- [ ] Fases completadas marcadas como ✅
- [ ] Próxima acción claramente definida
- [ ] Problemas encontrados documentados
- [ ] `HANDOFF.md` actualizado (si aplica)
- [ ] `INSTRUCCIONES.md` actualizado (si aplica)
- [ ] Git status verificado
- [ ] Archivos mencionados existen

---

## 🎯 OBJETIVO

**Garantizar que cada nueva sesión pueda:**
1. **Entender el contexto** en menos de 5 minutos
2. **Continuar exactamente** donde quedó la sesión anterior
3. **No perder tiempo** en información obsoleta
4. **Ejecutar inmediatamente** el plan aprobado

---

## 📊 BENEFICIOS DE LA SIMPLIFICACIÓN

- ✅ **Reducción de contexto:** De ~50% a ~15% en carga inicial
- ✅ **Información relevante:** Solo archivos actuales y necesarios
- ✅ **Menos confusión:** Sin documentación obsoleta o redundante
- ✅ **Enfoque claro:** En la tarea actual (Sistema de Slots)

---

**¡ESTAS REGLAS SON OBLIGATORIAS Y NO TIENEN EXCEPCIONES!**
