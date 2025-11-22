# PROBLEMA REAL ENCONTRADO - Volumen en Dashboard

**Fecha:** 2025-10-27
**Estado:** DIAGNOSTICADO

---

## PROBLEMA

El usuario reporta que el volumen NO disminuye gradualmente en las barras del dashboard cuando los operarios descargan en multiples staging areas.

---

## DIAGNOSTICO

### Analisis de Logs:

Veamos los eventos que se generan:

```
[PARTIAL-DISCHARGE] GroundOp-01: 80L -> 80L (descargados 0L) en t=340.0s
[DEBUG-VOLUME] Valor en estado_visual despues de update: 80L
```

### Problema Identificado:

1. **Los eventos `partial_discharge` se procesan correctamente**
   - Handler actualiza `estado_visual["operarios"][agent_id]['carga']`
   - El valor SI se actualiza en `estado_visual`

2. **PERO el valor NO cambia porque:**
   - El evento `partial_discharge` tiene `cargo_restante` que es IGUAL al valor anterior
   - Esto indica que `volumen_descargado` es 0L
   - Por lo tanto no hay diferencia entre 80L -> 80L (no hay cambio)

3. **Causa raiz:**
   - `volumen_staging` se calcula como: `sum(wo.calcular_volumen_restante() for wo in staging_wos)`
   - Pero DESPUES del picking, `cantidad_restante = 0` y por lo tanto `calcular_volumen_restante()` retorna 0
   - Por lo tanto `volumen_staging` es siempre 0
   - Por lo tanto `volumen_descargado` es siempre 0
   - Por lo tanto no hay cambio visible

### Flujo Actual (INCORRECTO):

```
1. Operario hace picking de WO -> cargo_volume = 100L
2. Operario navega a staging 1
3. Operario descarga en staging 1:
   - Calcula volumen_staging = sum(wo.calcular_volumen_restante())  <-- RETORNA 0 (cantidad_restante ya es 0!)
   - Genera evento partial_discharge con volumen_descargado = 0
   - cargo_restante = cargo_volume - 0 = 100L (sin cambio!)
4. Dashboard muestra 100L (sin cambio visible)
```

---

## SOLUCION

### Problema:

El calculo de `volumen_staging` es incorrecto porque usa `calcular_volumen_restante()` DESPUES de que `cantidad_restante = 0`.

### Solucion:

En lugar de calcular `volumen_staging` basandose en `calcular_volumen_restante()`, deberiamos calcular el volumen DESPUES de descontarlo de `cargo_volume`:

**CAMBIAR EN `operators.py`:**

```python
# ANTES (INCORRECTO):
volumen_staging = sum(wo.calcular_volumen_restante() for wo in staging_wos)

# DESPUES DE DESCONTAR:
# Primero descontar el volumen
volume_to_discharge = sum(wo.volume for wo in staging_wos)  # Volumen original de los WOs
self.cargo_volume -= volume_to_discharge

# Luego registrar el evento con el volumen que SI se descargo
self.almacen.registrar_evento('partial_discharge', {
    'agent_id': self.id,
    'staging_id': staging_id,
    'wos_descargadas': [wo.id for wo in staging_wos],
    'volumen_descargado': volume_to_discharge,  # <-- VALOR CORRECTO
    'cargo_restante': self.cargo_volume,  # <-- VALOR ACTUALIZADO
    'timestamp': self.env.now
})
```

---

## ARCHIVOS A MODIFICAR

1. `src/subsystems/simulation/operators.py` (Linea ~467 y ~847)
   - Cambiar calculo de `volumen_staging` para usar `wo.volume` en lugar de `wo.calcular_volumen_restante()`
   - Actualizar `cargo_volume` ANTES de generar el evento
   - Asegurar que `volumen_descargado` refleje el volumen real descargado

---

## RESULTADO ESPERADO

Despues de la correccion, los eventos deberian mostrar:

```
[PARTIAL-DISCHARGE] GroundOp-01: 100L -> 70L (descargados 30L) en t=340.0s
[PARTIAL-DISCHARGE] GroundOp-01: 70L -> 40L (descargados 30L) en t=350.0s
[PARTIAL-DISCHARGE] GroundOp-01: 40L -> 0L (descargados 40L) en t=360.0s
```

Y el dashboard deberia mostrar la disminucion gradual del volumen en cada descarga.

---

**ESTADO:** Diagonosticado, requiere implementacion

