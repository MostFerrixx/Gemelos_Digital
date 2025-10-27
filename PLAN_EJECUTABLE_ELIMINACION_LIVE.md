# PLAN EJECUTABLE - ELIMINACIÓN LIVE SIMULATION

**Fecha:** 2025-01-15  
**Estado:** ✅ LISTO PARA EJECUTAR  
**Objetivo:** Eliminar código de live simulation sin romper replay

---

## ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Archivos a Crear](#archivos-a-crear)
3. [Archivos a Eliminar](#archivos-a-eliminar)
4. [Archivos a Modificar](#archivos-a-modificar)
5. [Validación](#validacion)
6. [Rollback](#rollback)

---

## RESUMEN EJECUTIVO

### OBJETIVO
Eliminar el código de live simulation (renderizado en tiempo real) manteniendo solo:
- Generación de archivos .jsonl (para replay)
- Modo replay (100% funcional)

### CAMBIOS TOTALES
- **Eliminar:** 3 archivos (~2080 líneas)
- **Crear:** 2 archivos (~280 líneas)
- **Modificar:** 2 archivos (Makefile, run.bat)

### REDUCCIÓN
**87% menos código** (1800 líneas eliminadas)

---

## ARCHIVOS A CREAR

### 1. `src/engines/event_generator.py`

**ACCIÓN:** Crear nuevo archivo  
**UBICACIÓN:** `src/engines/event_generator.py`  
**LÍNEAS:** ~250

**CONTENIDO COMPLETO:**

```python
# -*- coding: utf-8 -*-
"""
Event Generator Engine - Motor puro de generacion de eventos para replay.
Sin renderizado, sin Pygame, solo SimPy + generacion de .jsonl
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import simpy
from datetime import datetime

# Imports de subsystems
from subsystems.simulation.warehouse import AlmacenMejorado
from subsystems.simulation.operators import crear_operarios
from subsystems.simulation.layout_manager import LayoutManager
from subsystems.simulation.assignment_calculator import AssignmentCostCalculator
from subsystems.simulation.data_manager import DataManager
from subsystems.simulation.pathfinder import Pathfinder
from subsystems.simulation.route_calculator import RouteCalculator

# Imports de core
from core.config_manager import ConfigurationManager, ConfigurationError
from core.config_utils import get_default_config
from core.replay_utils import volcar_replay_a_archivo

# Imports de analytics
from analytics.exporter_v2 import AnalyticsExporter
from analytics.context import SimulationContext

# Replay buffer
from simulation_buffer import ReplayBuffer


class EventGenerator:
    """
    Motor puro de generacion de eventos para archivos .jsonl
    
    Extrae solo la logica esencial de SimulationEngine:
    - Inicializacion de subsystems (AlmacenMejorado, Dispatcher, Operators)
    - Ejecucion de simulacion SimPy pura (sin Pygame)
    - Generacion de archivos .jsonl para replay
    - Exportacion de analytics (Excel)
    
    NO incluye:
    - Renderizado en tiempo real
    - Pygame
    - Multiproceso visual
    - Dashboard en tiempo real
    """
    
    def __init__(self, headless_mode=True):
        """
        Inicializa el generador de eventos
        
        Args:
            headless_mode: Siempre True (sin UI)
        """
        # Cargar configuracion
        try:
            self.config_manager = ConfigurationManager()
            self.config_manager.validate_configuration()
            self.configuracion = self.config_manager.configuration
            print("[EVENT-GENERATOR] Configuracion cargada exitosamente")
        except ConfigurationError as e:
            print(f"[EVENT-GENERATOR ERROR] Error en configuracion: {e}")
            self.config_manager = None
            self.configuracion = get_default_config()
            print("[EVENT-GENERATOR] Fallback: Usando configuracion por defecto")
        
        # Entorno SimPy
        self.env = None
        self.almacen = None
        
        # Timestamps para compatibilidad con SimulationContext
        self.session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_output_dir = os.path.join("output", f"simulation_{self.session_timestamp}")
        
        # Replay buffer
        self.replay_buffer = ReplayBuffer()
        
        # TMX components
        self.layout_manager = None
        self.pathfinder = None
        self.data_manager = None
        self.cost_calculator = None
        self.route_calculator = None
        
        # Operarios
        self.operarios = []
        self.procesos_operarios = []
        
        print(f"[EVENT-GENERATOR] Inicializado - Session: {self.session_timestamp}")
    
    def crear_simulacion(self):
        """Crea una nueva simulacion (sin Pygame)"""
        if not self.configuracion:
            print("[EVENT-GENERATOR ERROR] No hay configuracion valida")
            return False
        
        print("[EVENT-GENERATOR] Inicializando arquitectura TMX...")
        
        # 1. Inicializar LayoutManager
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        tmx_file = os.path.join(project_root, self.configuracion.get('layout_file', 'layouts/WH1.tmx'))
        print(f"[EVENT-GENERATOR] Cargando layout: {tmx_file}")
        
        try:
            self.layout_manager = LayoutManager(tmx_file)
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] No se pudo cargar TMX: {e}")
            return False
        
        # 2. Inicializar Pathfinder
        print("[EVENT-GENERATOR] Inicializando pathfinding...")
        try:
            self.pathfinder = Pathfinder(self.layout_manager.collision_matrix)
            self.route_calculator = RouteCalculator(self.pathfinder)
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] No se pudo inicializar pathfinder: {e}")
            return False
        
        # 3. Crear entorno SimPy
        self.env = simpy.Environment()
        
        # 4. Crear DataManager
        layout_file = self.configuracion.get('layout_file', '')
        sequence_file = self.configuracion.get('sequence_file', '')
        self.data_manager = DataManager(layout_file, sequence_file)
        
        # 5. Crear calculador de costos
        self.cost_calculator = AssignmentCostCalculator(self.data_manager)
        
        print(f"[EVENT-GENERATOR] Arquitectura TMX inicializada:")
        print(f"  - Dimensiones: {self.layout_manager.grid_width}x{self.layout_manager.grid_height}")
        print(f"  - Puntos de picking: {len(self.layout_manager.picking_points)}")
        print(f"  - Staging areas: {len(self.data_manager.outbound_staging_locations)}")
        
        # 6. Crear AlmacenMejorado
        self.almacen = AlmacenMejorado(
            self.env,
            self.configuracion,
            layout_manager=self.layout_manager,
            pathfinder=self.pathfinder,
            data_manager=self.data_manager,
            cost_calculator=self.cost_calculator,
            route_calculator=self.route_calculator,
            simulador=None,  # No hay simulador en modo headless
            visual_event_queue=None,  # No hay cola visual
            replay_buffer=self.replay_buffer  # SI hay replay buffer
        )
        
        # 7. Crear operarios
        self.procesos_operarios, self.operarios = crear_operarios(
            self.env,
            self.almacen,
            self.configuracion,
            simulador=None,
            pathfinder=self.pathfinder,
            layout_manager=self.layout_manager
        )
        
        # 8. Inicializar almacen y crear ordenes
        self.almacen._crear_catalogo_y_stock()
        self.almacen._generar_flujo_ordenes()
        
        # 9. Capturar snapshot inicial de WorkOrders
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'lista_maestra_work_orders'):
            initial_snapshot = [wo.to_dict() for wo in self.almacen.dispatcher.lista_maestra_work_orders]
            self.almacen.dispatcher.initial_work_orders_snapshot = initial_snapshot
            print(f"[EVENT-GENERATOR] Snapshot inicial capturado: {len(initial_snapshot)} WorkOrders")
        
        # 10. Iniciar proceso del dispatcher
        if hasattr(self.almacen, 'dispatcher') and hasattr(self.almacen.dispatcher, 'dispatcher_process'):
            print("[EVENT-GENERATOR] Iniciando dispatcher...")
            self.env.process(self.almacen.dispatcher.dispatcher_process(self.operarios))
        
        print(f"[EVENT-GENERATOR] Simulacion creada:")
        print(f"  - {len(self.procesos_operarios)} operarios")
        print(f"  - {len(self.almacen.dispatcher.lista_maestra_work_orders)} WorkOrders")
        print(f"  - {self.almacen.total_ordenes} ordenes generadas")
        
        return True
    
    def ejecutar(self):
        """Ejecuta la simulacion y genera archivos de salida"""
        try:
            print("="*60)
            print("GENERADOR DE EVENTOS - GEMELO DIGITAL")
            print(f"Session: {self.session_timestamp}")
            print("Modo: Headless (sin UI)")
            print("="*60)
            
            # Crear simulacion
            if not self.crear_simulacion():
                print("[EVENT-GENERATOR ERROR] Fallo al crear simulacion")
                return False
            
            # Ejecutar simulacion SimPy pura
            print("[EVENT-GENERATOR] Ejecutando simulacion SimPy...")
            step_counter = 0
            
            while not self.almacen.simulacion_ha_terminado():
                try:
                    self.env.run(until=self.env.now + 1.0)
                    step_counter += 1
                    
                    # Log cada 100 pasos
                    if step_counter % 100 == 0:
                        stats = self.almacen.dispatcher.obtener_estadisticas()
                        print(f"[EVENT-GENERATOR] t={self.env.now:.1f}s | "
                              f"Completadas: {stats['completados']}/{stats['total']}")
                
                except simpy.core.EmptySchedule:
                    if self.almacen.simulacion_ha_terminado():
                        break
                    else:
                        print("[EVENT-GENERATOR WARNING] No hay eventos pero simulacion no termino")
                        break
            
            print(f"[EVENT-GENERATOR] Simulacion completada en t={self.env.now:.2f}s")
            
            # Exportar analytics
            print("[EVENT-GENERATOR] Exportando analytics...")
            context = SimulationContext.from_simulation_engine(self)
            analytics_exporter = AnalyticsExporter(context)
            export_result = analytics_exporter.export_complete_analytics()
            
            if not export_result.success:
                print(f"[EVENT-GENERATOR WARNING] Exportacion con errores: {len(export_result.errors)}")
            
            # Generar archivo .jsonl
            print("[EVENT-GENERATOR] Generando archivo .jsonl...")
            os.makedirs(self.session_output_dir, exist_ok=True)
            output_file = os.path.join(self.session_output_dir, f"replay_{self.session_timestamp}.jsonl")
            initial_snapshot = getattr(self.almacen.dispatcher, 'initial_work_orders_snapshot', [])
            
            volcar_replay_a_archivo(
                self.replay_buffer,
                output_file,
                self.configuracion,
                self.almacen,
                initial_snapshot
            )
            
            print(f"[EVENT-GENERATOR] Archivo generado: {output_file}")
            print(f"[EVENT-GENERATOR] Eventos capturados: {len(self.replay_buffer)}")
            print("="*60)
            print("GENERACION COMPLETADA")
            print(f"Archivos en: {self.session_output_dir}")
            print("="*60)
            
            return True
        
        except KeyboardInterrupt:
            print("\n[EVENT-GENERATOR] Interrupcion del usuario")
            return False
        
        except Exception as e:
            print(f"[EVENT-GENERATOR ERROR] Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False


# Export
__all__ = ['EventGenerator']
```

---

### 2. `entry_points/run_generate_replay.py`

**ACCIÓN:** Crear nuevo archivo  
**UBICACIÓN:** `entry_points/run_generate_replay.py`  
**LÍNEAS:** ~30

**CONTENIDO COMPLETO:**

```python
# -*- coding: utf-8 -*-
"""
Generate Replay - Entry point para generar archivos .jsonl
Sin UI, solo generacion de eventos para replay
"""

import sys
import os

# Add src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from engines.event_generator import EventGenerator


def main():
    """Funcion principal - Genera archivo .jsonl sin UI"""
    
    print("="*60)
    print("GENERADOR DE REPLAY - GEMELO DIGITAL")
    print("Modo: Headless (maxima velocidad, sin interfaz)")
    print("="*60)
    print()
    
    # Crear generador y ejecutar
    generator = EventGenerator(headless_mode=True)
    success = generator.ejecutar()
    
    if success:
        print("\nExito: Archivos generados en output/")
        return 0
    else:
        print("\nError: Fallo al generar archivos")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
```

---

## ARCHIVOS A ELIMINAR

### 1. `entry_points/run_live_simulation.py`

**ACCIÓN:** Eliminar archivo completo  
**RAZÓN:** Entry point de live simulation (ya no necesario)

**COMANDO:**
```bash
# Windows
del entry_points\run_live_simulation.py

# Linux/Mac
rm entry_points/run_live_simulation.py
```

---

### 2. `src/engines/simulation_engine.py`

**ACCIÓN:** Eliminar archivo completo  
**RAZÓN:** Motor de live simulation (reemplazado por event_generator.py)

**COMANDO:**
```bash
# Windows
del src\engines\simulation_engine.py

# Linux/Mac
rm src/engines/simulation_engine.py
```

---

### 3. `src/communication/simulation_data_provider.py`

**ACCIÓN:** Eliminar archivo completo  
**RAZÓN:** Solo usado por live simulation para dashboard en tiempo real

**COMANDO:**
```bash
# Windows
del src\communication\simulation_data_provider.py

# Linux/Mac
rm src/communication/simulation_data_provider.py
```

---

## ARCHIVOS A MODIFICAR

### 1. `Makefile`

**ACCIÓN:** Actualizar comandos `sim` y `sim-visual`  
**UBICACIÓN:** `Makefile`

**CAMBIOS:**

```makefile
# BUSCAR (línea 22-24):
sim:
	@echo "Ejecutando simulacion headless..."
	python entry_points/run_live_simulation.py --headless

# REEMPLAZAR POR:
sim:
	@echo "Generando archivo de replay..."
	python entry_points/run_generate_replay.py
```

```makefile
# BUSCAR (línea 26-29):
sim-visual:
	@echo "Ejecutando simulacion con interfaz grafica..."
	python entry_points/run_live_simulation.py

# REEMPLAZAR POR:
# ELIMINADO: sim-visual ya no existe
# Para visualizar, usar: make replay FILE=<archivo.jsonl>
```

**RESULTADO FINAL DEL BLOQUE (líneas 21-30):**

```makefile
# Simulacion (genera replay)
sim:
	@echo "Generando archivo de replay..."
	python entry_points/run_generate_replay.py

# Nota: Para visualizar, usar replay:
#   make replay FILE=output/simulation_*/replay_*.jsonl

# Replay viewer
replay:
```

---

### 2. `run.bat`

**ACCIÓN:** Actualizar comandos `sim` y `sim-visual`  
**UBICACIÓN:** `run.bat`

**CAMBIOS:**

```batch
REM BUSCAR (línea 31-34):
:sim
echo Ejecutando simulacion headless...
python entry_points\run_live_simulation.py --headless
goto end

REM REEMPLAZAR POR:
:sim
echo Generando archivo de replay...
python entry_points\run_generate_replay.py
goto end
```

```batch
REM BUSCAR (línea 36-39):
:sim-visual
echo Ejecutando simulacion con interfaz grafica...
python entry_points\run_live_simulation.py
goto end

REM REEMPLAZAR POR:
REM ELIMINADO: sim-visual ya no existe
REM Para visualizar, usar: run replay <archivo.jsonl>
```

**RESULTADO FINAL DEL BLOQUE (líneas 31-39):**

```batch
:sim
echo Generando archivo de replay...
python entry_points\run_generate_replay.py
goto end

REM Nota: Para visualizar, usar replay:
REM   run replay output\simulation_*\replay_*.jsonl

:replay
if "%2"=="" (
```

---

## VALIDACIÓN

### PASO 1: Verificar archivos creados

```bash
# Verificar que existen los nuevos archivos
ls -la src/engines/event_generator.py
ls -la entry_points/run_generate_replay.py
```

**ESPERADO:** Ambos archivos existen

---

### PASO 2: Verificar archivos eliminados

```bash
# Verificar que NO existen los archivos eliminados
ls -la entry_points/run_live_simulation.py
ls -la src/engines/simulation_engine.py
ls -la src/communication/simulation_data_provider.py
```

**ESPERADO:** "No such file or directory" para los 3 archivos

---

### PASO 3: Generar archivo .jsonl

```bash
# Ejecutar generador
python entry_points/run_generate_replay.py
```

**ESPERADO:**
```
GENERADOR DE EVENTOS - GEMELO DIGITAL
...
[EVENT-GENERATOR] Simulacion completada
[EVENT-GENERATOR] Archivo generado: output/simulation_YYYYMMDD_HHMMSS/replay_YYYYMMDD_HHMMSS.jsonl
GENERACION COMPLETADA
```

---

### PASO 4: Verificar archivo .jsonl generado

```bash
# Listar archivo generado
ls -lh output/simulation_*/replay_*.jsonl

# Verificar contenido (primeras líneas)
head -n 5 output/simulation_*/replay_*.jsonl
```

**ESPERADO:**
- Archivo .jsonl existe
- Tamaño: 5-10 MB
- Primera línea: `{"event_type":"SIMULATION_START",...}`

---

### PASO 5: Probar replay viewer

```bash
# Ejecutar replay con archivo generado
python entry_points/run_replay_viewer.py output/simulation_*/replay_*.jsonl
```

**ESPERADO:**
- Replay viewer abre correctamente
- Muestra WorkOrders
- Muestra operarios moviéndose
- Dashboard funciona

---

### PASO 6: Verificar comandos make

```bash
# Probar comando make
make sim

# Verificar que genera archivo
ls -la output/simulation_*/replay_*.jsonl
```

**ESPERADO:** Archivo .jsonl generado exitosamente

---

## ROLLBACK

Si algo falla, ejecutar estos comandos para revertir:

```bash
# 1. Restaurar archivos desde git
git checkout entry_points/run_live_simulation.py
git checkout src/engines/simulation_engine.py
git checkout src/communication/simulation_data_provider.py
git checkout Makefile
git checkout run.bat

# 2. Eliminar archivos nuevos
rm src/engines/event_generator.py
rm entry_points/run_generate_replay.py

# 3. Verificar estado
git status
```

---

## CHECKLIST FINAL

### Antes de ejecutar:
- [ ] Backup de archivos críticos
- [ ] Git status limpio (commit cambios pendientes)
- [ ] Leer todo el plan

### Durante ejecución:
- [ ] Crear `src/engines/event_generator.py`
- [ ] Crear `entry_points/run_generate_replay.py`
- [ ] Eliminar `entry_points/run_live_simulation.py`
- [ ] Eliminar `src/engines/simulation_engine.py`
- [ ] Eliminar `src/communication/simulation_data_provider.py`
- [ ] Modificar `Makefile`
- [ ] Modificar `run.bat`

### Después de ejecutar:
- [ ] Ejecutar PASO 1: Verificar archivos creados
- [ ] Ejecutar PASO 2: Verificar archivos eliminados
- [ ] Ejecutar PASO 3: Generar .jsonl
- [ ] Ejecutar PASO 4: Verificar .jsonl
- [ ] Ejecutar PASO 5: Probar replay
- [ ] Ejecutar PASO 6: Verificar make
- [ ] Commit de cambios

---

**FIN DEL PLAN EJECUTABLE**
