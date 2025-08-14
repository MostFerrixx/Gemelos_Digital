# 🎨 GUÍA COMPLETA - LAYOUTS DINÁMICOS

## 🚀 Tu Almacén, Tu Diseño - Sin Programar

Esta guía te enseñará a crear y usar tus propios layouts de almacén personalizados usando **Tiled Map Editor** y cargarlos dinámicamente en el simulador.

---

## 📋 **REQUISITOS PREVIOS**

### Software Necesario:
1. **Tiled Map Editor** (Gratis) - [Descargar aquí](https://www.mapeditor.org/)
2. **Simulador de Almacén** (Ya lo tienes)

### Archivos Incluidos:
- ✅ `warehouse_tileset.png` - Imagen del tileset
- ✅ `warehouse_tileset.tsx` - Tileset para Tiled
- ✅ `layouts/` - Carpeta para tus layouts
- ✅ Layouts de ejemplo incluidos

---

## 🎯 **FLUJO DE TRABAJO COMPLETO**

### **Paso 1: Instalar Tiled**
1. Descarga Tiled desde https://www.mapeditor.org/
2. Instala siguiendo las instrucciones del instalador
3. Ejecuta Tiled para verificar que funciona

### **Paso 2: Preparar el Proyecto**
1. Abre Tiled
2. Ve a **File → New Map**
3. Configura tu mapa:
   - **Orientation**: Orthogonal
   - **Tile layer format**: CSV
   - **Tile size**: 32 x 32 pixels
   - **Map size**: Ej. 30 x 20 tiles (ajustable)

### **Paso 3: Importar el Tileset**
1. En Tiled, ve a **View → Tilesets**
2. Haz clic en **New Tileset**
3. Selecciona **Based on Tileset Image**
4. Navega y selecciona: `tilesets/warehouse_tileset.tsx`
5. ¡Listo! Ahora tienes todos los tiles disponibles

---

## 🧱 **TILES DISPONIBLES - REFERENCIA RÁPIDA**

### **🚶 TILES NAVEGABLES (Operarios pueden pasar)**
| ID | Nombre | Uso | Color |
|----|--------|-----|--------|
| **0** | Floor_Walkable | Suelo básico navegable | 🔘 Gris claro |
| **2** | Picking_Point | Puntos de picking | 🟢 Verde |
| **3** | Depot_Zone | Zona de estacionamiento | 🔵 Azul |
| **4** | Inbound_Zone | Zona de entrada | 🟠 Naranja |
| **6** | Corridor_Main | Pasillo principal (más rápido) | 🔷 Azul claro |
| **7** | Workstation | Estación de trabajo | 🟡 Amarillo |

### **🚫 TILES OBSTÁCULOS (Operarios NO pueden pasar)**
| ID | Nombre | Uso | Color |
|----|--------|-----|--------|
| **1** | Rack_Obstacle | Racks de almacén | 🟫 Marrón |
| **5** | Wall_Blocked | Muros y paredes | ⚫ Gris oscuro |
| **10** | Office_Area | Área de oficinas | 🟨 Amarillo claro |

---

## 🏗️ **CREANDO TU PRIMER LAYOUT**

### **Paso 4: Diseñar el Layout Base**
1. **Empieza con el suelo**: Usa tile **ID 0** (Floor_Walkable) para pintar toda el área navegable
2. **Agrega racks**: Usa tile **ID 1** (Rack_Obstacle) para crear los racks de almacén
3. **Crea pasillos**: Usa tile **ID 6** (Corridor_Main) para pasillos principales
4. **Delimita con muros**: Usa tile **ID 5** (Wall_Blocked) para bordes si necesario

### **Consejos de Diseño:**
- ✅ **Deja pasillos de al menos 2-3 tiles de ancho**
- ✅ **Crea rutas alternativas** entre zonas importantes
- ✅ **Usa patrones realistas** de almacén (racks paralelos, pasillos perpendiculares)
- ❌ **Evita espacios completamente cerrados** sin salida

---

## 📍 **AGREGANDO UBICACIONES ESPECIALES**

### **Paso 5: Crear Capa de Objetos**
1. En Tiled, haz clic derecho en **Layers** → **Add Layer** → **Object Layer**
2. Nómbrala: `Special_Locations`
3. Con esta capa seleccionada, podrás agregar objetos

### **Paso 6: Colocar Puntos Importantes**

#### **🏠 Depot (Obligatorio)**
1. Herramienta: **Insert Rectangle** (R)
2. Dibuja un rectángulo en la zona de estacionamiento
3. **Properties**:
   - **Name**: `Main_Depot`
   - **Type**: `depot`
   - **capacity**: `5` (número de operarios)

#### **📥 Inbound (Obligatorio)**
1. Dibuja rectángulo en zona de entrada
2. **Properties**:
   - **Name**: `Inbound_Dock`
   - **Type**: `inbound`
   - **dock_count**: `2` (número de muelles)

#### **📦 Puntos de Picking (Recomendado)**
1. Para cada ubicación de picking:
2. Dibuja pequeño rectángulo
3. **Properties**:
   - **Name**: `Picking_A1`, `Picking_A2`, etc.
   - **Type**: `picking`
   - **priority**: `high`, `medium`, `low`

---

## 💾 **GUARDANDO Y USANDO TU LAYOUT**

### **Paso 7: Guardar el Layout**
1. **File → Save As**
2. **Formato**: Tiled map files (*.tmx)
3. **Carpeta**: `layouts/` (dentro del directorio del simulador)
4. **Nombre**: `mi_almacen_personalizado.tmx`

### **Paso 8: Cargar en el Simulador**
1. Ejecuta el simulador: `python run_simulator.py`
2. En la ventana de configuración:
   - Ve a la pestaña **"📐 Layout del Almacén"**
   - Marca **"Usar layout personalizado (TMX)"**
   - Selecciona tu layout del dropdown
   - Haz clic **"🔄"** si no aparece
3. Configura otros parámetros como siempre
4. **"Iniciar Simulación"**

¡Tu layout personalizado se cargará automáticamente! 🎉

---

## 🔧 **SOLUCIÓN DE PROBLEMAS**

### **Mi layout no aparece en el dropdown**
- ✅ Verifica que esté guardado en la carpeta `layouts/`
- ✅ Asegúrate que la extensión sea `.tmx`
- ✅ Haz clic en el botón "🔄" para refrescar

### **Error: "Layout con errores"**
- ✅ Verifica que usaste el tileset correcto (`warehouse_tileset.tsx`)
- ✅ Asegúrate de tener al menos un objeto Depot e Inbound
- ✅ Revisa que no hay tiles con ID inválidos

### **Los operarios se atascan o no encuentran rutas**
- ✅ Asegúrate que hay rutas navegables entre todas las zonas
- ✅ Usa principalmente tiles navegables (ID 0, 2, 3, 4, 6, 7)
- ✅ Evita crear laberintos sin salida

### **El simulador usa el layout anterior**
- ✅ Verifica que seleccionaste el layout correcto en la configuración
- ✅ Reinicia el simulador completamente
- ✅ Verifica que el checkbox "Usar layout personalizado" esté marcado

---

## 📘 **EJEMPLOS Y PLANTILLAS**

### **Layout Básico Pequeño** (20x15 tiles)
- Perfecto para pruebas rápidas
- 3-4 filas de racks
- Pasillos simples
- Archivo: `layouts/basic_example.tmx`

### **Almacén Típico** (30x20 tiles)
- Layout realista de almacén
- Múltiples zonas de picking
- Pasillos principales y secundarios  
- Archivo: `layouts/warehouse_example.tmx`

### **Plantilla Vacía**
- Solo suelo navegable
- Perfecto para empezar desde cero
- Objetos Depot e Inbound preconfigurados

---

## 🎨 **CONSEJOS DE DISEÑO AVANZADO**

### **Crear Almacenes Realistas:**
1. **Zonas diferenciadas**: Separar entrada, picking, y estacionamiento
2. **Flujo lógico**: Entrada → Picking → Salida/Depot
3. **Pasillos principales**: Usar ID 6 para arterias principales
4. **Redundancia**: Múltiples rutas entre zonas importantes

### **Optimizar Rendimiento:**
1. **Tamaño moderado**: 20-50 tiles por lado funciona bien
2. **Evitar complejidad excesiva**: Demasiados obstáculos ralentizan pathfinding
3. **Probar incrementalmente**: Empezar simple, agregar complejidad gradualmente

### **Hacer Layouts Interesantes:**
1. **Diferentes tipos de zona**: Oficinas, muelles, áreas especiales
2. **Variación en pasillos**: Anchos diferentes, intersecciones
3. **Elementos decorativos**: Usar diferentes tiles para variedad visual

---

## 🎯 **CHECKLIST FINAL - ANTES DE USAR TU LAYOUT**

- [ ] ✅ Layout guardado como archivo `.tmx` en carpeta `layouts/`
- [ ] ✅ Usaste el tileset oficial `warehouse_tileset.tsx`
- [ ] ✅ Incluiste al menos 1 objeto **Depot** (type="depot")
- [ ] ✅ Incluiste al menos 1 objeto **Inbound** (type="inbound")
- [ ] ✅ Hay rutas navegables entre todas las ubicaciones importantes
- [ ] ✅ Probaste que el layout aparece en el dropdown del simulador
- [ ] ✅ Configuraste otros parámetros de simulación
- [ ] ✅ ¡Listo para simular!

---

## 🆘 **¿NECESITAS AYUDA?**

### **Recursos Útiles:**
- 📖 **Manual de Tiled**: https://doc.mapeditor.org/
- 🎬 **Tutoriales en YouTube**: Busca "Tiled Map Editor tutorial"
- 📋 **Referencia de Tiles**: `docs/TILES_REFERENCE.md`

### **Errores Comunes:**
1. **No guardar en la carpeta correcta**: Debe ser `layouts/`
2. **Olvidar objetos obligatorios**: Depot e Inbound son necesarios
3. **Crear zonas sin conexión**: Asegurar rutas navegables

---

## 🎉 **¡YA ESTÁS LISTO!**

Ahora puedes:
- ✅ **Diseñar layouts únicos** para diferentes escenarios
- ✅ **Probar configuraciones** de almacén rápidamente
- ✅ **Experimentar con flujos** de trabajo diferentes
- ✅ **Crear almacenes realistas** basados en casos reales

**¡Diviértete creando y simulando tus propios almacenes!** 🚀

---

*Documentación generada automáticamente - Sistema de Layouts Dinámicos v1.0*