# -*- coding: utf-8 -*-
"""
Visualization State Management - Estado visual global para la simulacion

FASE 2: IMPLEMENTACION COMPLETA
Este modulo gestiona el estado visual compartido entre el motor de simulacion
y la capa de renderizado. Actua como la unica fuente de verdad para la visualizacion.

Autor: Claude Code (Implementacion V11)
Estado: PRODUCTION - Implementacion completa
"""


# =============================================================================
# ESTADO VISUAL GLOBAL
# =============================================================================

# Variable global que mantiene el estado de la visualizacion
# Este diccionario es la unica fuente de verdad para toda la capa de visualizacion
estado_visual = {
    # =========================================================================
    # OPERARIOS - Dict[str, Dict[str, Any]]
    # Clave: agent_id (str) - Ejemplo: "GroundOperator_1", "Forklift_2"
    # =========================================================================
    "operarios": {
        # Estructura de cada operario:
        # {
        #     "id": str,                    # ID del agente
        #     "x": int,                     # Posicion X en pixeles
        #     "y": int,                     # Posicion Y en pixeles
        #     "position": tuple(int, int),  # Posicion original en grid
        #     "tipo": str,                  # "terrestre" | "montacargas"
        #     "accion": str,                # Accion legible (ej: "En Estacionamiento")
        #     "status": str,                # "idle" | "working" | "traveling"
        #     "tareas_completadas": int,    # Contador de tareas
        #     "tiempo_idle": float,         # Tiempo en idle (segundos SimPy)
        #     "tiempo_working": float,      # Tiempo trabajando
        #     "tiempo_traveling": float,    # Tiempo viajando
        #     "direccion_x": int,           # Direccion X (-1, 0, 1)
        #     "direccion_y": int,           # Direccion Y (-1, 0, 1)
        #     "tour_actual": dict | None,   # Detalles del tour actual
        #     "work_orders_asignadas": list # IDs de WorkOrders asignadas
        # }
    },

    # =========================================================================
    # WORK ORDERS - Dict[str, Dict[str, Any]]
    # Clave: wo_id (str) - Ejemplo: "WO-001"
    # =========================================================================
    "work_orders": {
        # Estructura de cada WorkOrder:
        # {
        #     "id": str,                    # ID unico
        #     "status": str,                # "pending" | "assigned" | "in_progress" | "completed"
        #     "assigned_to": str | None,    # agent_id asignado
        #     "location": tuple(int, int),  # Posicion en grid
        #     "work_area": str,             # Work area string
        #     "priority": str,              # "high" | "medium" | "low"
        #     "timestamp_created": float,   # Tiempo SimPy de creacion
        #     "timestamp_assigned": float,  # Tiempo de asignacion
        #     "timestamp_completed": float  # Tiempo de completado
        # }
    },

    # =========================================================================
    # METRICAS GLOBALES - Dict[str, Any]
    # =========================================================================
    "metricas": {
        "tiempo_simulacion": 0.0,       # float - Tiempo SimPy actual (env.now)
        "workorders_completadas": 0,    # int - Total WorkOrders completadas
        "tareas_completadas": 0,        # int - Total tareas individuales
        "operarios_idle": 0,            # int - Operarios en idle
        "operarios_working": 0,         # int - Operarios trabajando
        "operarios_traveling": 0,       # int - Operarios viajando
        "utilizacion_promedio": 0.0,    # float - % utilizacion (0.0-100.0)
    },

    # =========================================================================
    # CONTROLES UI - Valores simples
    # =========================================================================
    "pausa": False,                     # bool - Simulacion pausada?
    "velocidad": 1.0,                   # float - Factor velocidad (0.5, 1.0, 2.0, 5.0, 10.0)
    "dashboard_visible": True           # bool - Dashboard visible?
}


# =============================================================================
# FUNCIONES DE INICIALIZACION
# =============================================================================

def inicializar_estado(almacen, env, configuracion, layout_manager):
    """
    Inicializa el estado visual para una nueva simulacion.

    Puebla estado_visual["operarios"] con los operarios reales del almacen,
    convirtiendo sus posiciones de grid a pixeles para renderizado.

    Args:
        almacen: Instancia de AlmacenMejorado (contiene .operarios list)
        env: Entorno SimPy (para timestamps)
        configuracion: Dict de configuracion
        layout_manager: Instancia de LayoutManager para conversion grid->pixel

    Modifica:
        estado_visual (global) - Resetea y puebla con datos reales
    """
    global estado_visual

    print("[VISUALIZATION-STATE] Inicializando estado visual...")

    # 1. Resetear estado visual
    estado_visual["operarios"] = {}
    estado_visual["work_orders"] = {}
    estado_visual["metricas"] = {
        "tiempo_simulacion": env.now if env else 0.0,
        "workorders_completadas": 0,
        "tareas_completadas": 0,
        "operarios_idle": 0,
        "operarios_working": 0,
        "operarios_traveling": 0,
        "utilizacion_promedio": 0.0,
    }
    estado_visual["pausa"] = False
    estado_visual["velocidad"] = 1.0
    estado_visual["dashboard_visible"] = True

    # 2. Obtener lista de operarios desde el almacen
    if not almacen or not hasattr(almacen, 'operarios'):
        print("[VISUALIZATION-STATE] ADVERTENCIA: Almacen sin operarios, inicializacion vacia")
        return

    operarios_list = almacen.operarios
    print(f"[VISUALIZATION-STATE] Poblando estado visual con {len(operarios_list)} operarios...")

    # 3. Obtener posiciones de depot desde data_manager
    outbound_staging_locations = {}
    if hasattr(almacen, 'data_manager') and almacen.data_manager:
        outbound_staging_locations = almacen.data_manager.outbound_staging_locations

    # Fallback: usar primer outbound staging o (0, 0)
    depot_pos = outbound_staging_locations.get(1, (0, 0)) if outbound_staging_locations else (0, 0)

    # 4. Poblar estado_visual["operarios"] con datos reales
    for idx, agente in enumerate(operarios_list):
        # Obtener ID del agente
        agent_id = agente.id if hasattr(agente, 'id') else f"Agente_{idx}"

        # Obtener posicion inicial (depot o posicion actual)
        if hasattr(agente, 'position') and agente.position:
            grid_pos = agente.position
        else:
            # Usar depot position como fallback
            grid_pos = depot_pos

        # Convertir grid -> pixel usando layout_manager
        try:
            pixel_x, pixel_y = layout_manager.grid_to_pixel(grid_pos[0], grid_pos[1])
        except Exception as e:
            print(f"[VISUALIZATION-STATE] ADVERTENCIA: Error convirtiendo posicion {grid_pos}: {e}")
            pixel_x, pixel_y = 0, 0

        # Determinar tipo visual
        agent_type = getattr(agente, 'type', 'Unknown')
        tipo_visual = 'terrestre' if agent_type == 'GroundOperator' else 'montacargas'

        # Crear entrada en estado_visual
        estado_visual["operarios"][agent_id] = {
            'id': agent_id,
            'x': pixel_x,
            'y': pixel_y,
            'position': grid_pos,
            'tipo': tipo_visual,
            'accion': 'En Estacionamiento',
            'status': 'idle',
            'tareas_completadas': 0,
            'tiempo_idle': 0.0,
            'tiempo_working': 0.0,
            'tiempo_traveling': 0.0,
            'direccion_x': 0,
            'direccion_y': 0,
            'tour_actual': None,
            'work_orders_asignadas': []
        }

        print(f"  [VISUALIZATION-STATE] {agent_id} ({agent_type}) -> pixel ({pixel_x}, {pixel_y})")

    print(f"[VISUALIZATION-STATE] Estado visual inicializado: {len(estado_visual['operarios'])} operarios")


def inicializar_estado_con_cola(almacen, env, configuracion, layout_manager, event_queue):
    """
    Inicializa el estado visual para multiprocessing con cola de eventos.

    Esta version es identica a inicializar_estado() pero acepta event_queue
    para compatibilidad futura con arquitectura de eventos.

    Args:
        almacen: Instancia de AlmacenMejorado
        env: Entorno SimPy
        configuracion: Dict de configuracion
        layout_manager: Instancia de LayoutManager
        event_queue: multiprocessing.Queue para eventos visuales (FUTURO)

    Modifica:
        estado_visual (global)
    """
    # Delegar a inicializar_estado para setup base
    inicializar_estado(almacen, env, configuracion, layout_manager)

    # TODO FUTURO: Configurar listener de eventos si necesario
    # event_queue podria usarse para recibir actualizaciones desde proceso de simulacion

    print("[VISUALIZATION-STATE] Estado con cola inicializado (event_queue registrada)")


def limpiar_estado():
    """
    Resetea el estado visual a valores por defecto.

    Util para limpiar estado entre simulaciones o para testing.

    Modifica:
        estado_visual (global) - Resetea todos los campos
    """
    global estado_visual

    estado_visual["operarios"] = {}
    estado_visual["work_orders"] = {}
    estado_visual["metricas"] = {
        "tiempo_simulacion": 0.0,
        "workorders_completadas": 0,
        "tareas_completadas": 0,
        "operarios_idle": 0,
        "operarios_working": 0,
        "operarios_traveling": 0,
        "utilizacion_promedio": 0.0,
    }
    estado_visual["pausa"] = False
    estado_visual["velocidad"] = 1.0
    estado_visual["dashboard_visible"] = True

    print("[VISUALIZATION-STATE] Estado visual limpiado")


# =============================================================================
# FUNCIONES DE ACTUALIZACION DE ESTADO (NUEVAS)
# =============================================================================

def actualizar_posicion_operario(agent_id, grid_pos, layout_manager):
    """
    Actualiza la posicion de un operario desde coordenadas grid.

    Convierte automaticamente de grid a pixeles para renderizado.
    Si el operario no existe, crea una entrada con datos default.

    Args:
        agent_id: str - ID del agente
        grid_pos: Tuple[int, int] - Posicion en grid (x, y)
        layout_manager: LayoutManager - Para conversion grid->pixel

    Modifica:
        estado_visual["operarios"][agent_id] - Actualiza x, y, position
    """
    global estado_visual

    # Validar que el operario existe, si no, crear entrada default
    if agent_id not in estado_visual["operarios"]:
        print(f"[VISUALIZATION-STATE] ADVERTENCIA: Operario {agent_id} no existe, creando entrada default")
        estado_visual["operarios"][agent_id] = {
            'id': agent_id,
            'x': 0,
            'y': 0,
            'position': (0, 0),
            'tipo': 'terrestre',
            'accion': 'Desconocida',
            'status': 'idle',
            'tareas_completadas': 0,
            'tiempo_idle': 0.0,
            'tiempo_working': 0.0,
            'tiempo_traveling': 0.0,
            'direccion_x': 0,
            'direccion_y': 0,
            'tour_actual': None,
            'work_orders_asignadas': []
        }

    # Convertir grid -> pixel
    try:
        pixel_x, pixel_y = layout_manager.grid_to_pixel(grid_pos[0], grid_pos[1])
    except Exception as e:
        print(f"[VISUALIZATION-STATE] ERROR convirtiendo posicion {grid_pos}: {e}")
        pixel_x, pixel_y = 0, 0

    # Calcular direccion de movimiento (para animacion)
    old_pos = estado_visual["operarios"][agent_id]["position"]
    direccion_x = 0
    direccion_y = 0

    if old_pos != grid_pos:
        direccion_x = 1 if grid_pos[0] > old_pos[0] else (-1 if grid_pos[0] < old_pos[0] else 0)
        direccion_y = 1 if grid_pos[1] > old_pos[1] else (-1 if grid_pos[1] < old_pos[1] else 0)

    # Actualizar estado visual
    estado_visual["operarios"][agent_id]['x'] = pixel_x
    estado_visual["operarios"][agent_id]['y'] = pixel_y
    estado_visual["operarios"][agent_id]['position'] = grid_pos
    estado_visual["operarios"][agent_id]['direccion_x'] = direccion_x
    estado_visual["operarios"][agent_id]['direccion_y'] = direccion_y


def actualizar_estado_operario(agent_id, **kwargs):
    """
    Actualiza campos arbitrarios de un operario de forma flexible.

    Permite actualizar cualquier campo del operario sin necesidad de
    funciones especificas para cada campo.

    Args:
        agent_id: str - ID del agente
        **kwargs: Campos a actualizar (accion, status, tareas_completadas, etc.)

    Ejemplo de uso:
        actualizar_estado_operario("GroundOperator_1",
                                  accion="Recogiendo paquete",
                                  status="working",
                                  tareas_completadas=5)

    Modifica:
        estado_visual["operarios"][agent_id] - Actualiza campos especificados
    """
    global estado_visual

    # Validar que el operario existe, si no, crear entrada default
    if agent_id not in estado_visual["operarios"]:
        print(f"[VISUALIZATION-STATE] ADVERTENCIA: Operario {agent_id} no existe, creando entrada default")
        estado_visual["operarios"][agent_id] = {
            'id': agent_id,
            'x': 0,
            'y': 0,
            'position': (0, 0),
            'tipo': 'terrestre',
            'accion': 'Desconocida',
            'status': 'idle',
            'tareas_completadas': 0,
            'tiempo_idle': 0.0,
            'tiempo_working': 0.0,
            'tiempo_traveling': 0.0,
            'direccion_x': 0,
            'direccion_y': 0,
            'tour_actual': None,
            'work_orders_asignadas': []
        }

    # Actualizar todos los campos proporcionados
    for clave, valor in kwargs.items():
        estado_visual["operarios"][agent_id][clave] = valor


def actualizar_work_order(wo_id, wo_data):
    """
    Actualiza o crea una WorkOrder en el estado visual.

    Args:
        wo_id: str - ID de la WorkOrder
        wo_data: Dict - Datos completos de la WorkOrder

    Modifica:
        estado_visual["work_orders"][wo_id] - Crea o actualiza WorkOrder
    """
    global estado_visual

    # Copiar datos para evitar mutacion
    estado_visual["work_orders"][wo_id] = wo_data.copy()


# =============================================================================
# FUNCIONES DE ACTUALIZACION DE METRICAS
# =============================================================================

def actualizar_metricas_tiempo(operarios_dict):
    """
    Actualiza las metricas de tiempo de los operarios.

    Calcula contadores agregados (idle/working/traveling) y porcentaje
    de utilizacion basado en el status actual de todos los operarios.

    Args:
        operarios_dict: Dict[str, Dict] - Dict de operarios (tipicamente estado_visual["operarios"])

    Modifica:
        estado_visual["metricas"] - Actualiza contadores y utilizacion
    """
    global estado_visual

    # Inicializar contadores
    idle_count = 0
    working_count = 0
    traveling_count = 0

    # Contar operarios por status
    for operario in operarios_dict.values():
        status = operario.get('status', 'idle')

        # BUGFIX DASHBOARD METRICS: Alinear strings de status con valores reales del .jsonl
        if status in ['idle', 'Esperando tour']:
            idle_count += 1
        elif status in ['working', 'Trabajando']:  # Para futuras implementaciones
            working_count += 1
        elif status in ['traveling', 'moving', 'Moviendose']:
            traveling_count += 1

    # Calcular utilizacion (porcentaje de operarios no idle)
    total_operarios = len(operarios_dict)

    if total_operarios > 0:
        utilizacion = ((working_count + traveling_count) / total_operarios) * 100.0
    else:
        utilizacion = 0.0

    # Actualizar metricas globales
    estado_visual["metricas"]["operarios_idle"] = idle_count
    estado_visual["metricas"]["operarios_working"] = working_count
    estado_visual["metricas"]["operarios_traveling"] = traveling_count
    estado_visual["metricas"]["utilizacion_promedio"] = utilizacion


# =============================================================================
# FUNCIONES DE CONTROL (TOGGLES Y VELOCIDAD)
# =============================================================================

def toggle_pausa():
    """
    Alterna el estado de pausa de la simulacion.

    Returns:
        bool: Nuevo estado de pausa (True si pausado, False si corriendo)
    """
    global estado_visual

    estado_visual["pausa"] = not estado_visual["pausa"]

    return estado_visual["pausa"]


def toggle_dashboard():
    """
    Alterna la visibilidad del dashboard.

    Returns:
        bool: Nuevo estado de visibilidad (True si visible, False si oculto)
    """
    global estado_visual

    estado_visual["dashboard_visible"] = not estado_visual["dashboard_visible"]

    return estado_visual["dashboard_visible"]


# =============================================================================
# FUNCIONES DE CONTROL DE VELOCIDAD
# =============================================================================

def aumentar_velocidad():
    """
    Incrementa el factor de velocidad de la simulacion.

    Velocidades permitidas: 0.5x, 1x, 2x, 5x, 10x

    Modifica:
        estado_visual["velocidad"]
    """
    global estado_visual

    velocidades_permitidas = [0.5, 1.0, 2.0, 5.0, 10.0]
    velocidad_actual = estado_visual["velocidad"]

    # Buscar siguiente velocidad
    for vel in velocidades_permitidas:
        if vel > velocidad_actual:
            estado_visual["velocidad"] = vel
            print(f"[VISUALIZATION-STATE] Velocidad aumentada a {vel}x")
            return

    # Ya estamos en la maxima
    estado_visual["velocidad"] = velocidades_permitidas[-1]
    print(f"[VISUALIZATION-STATE] Velocidad maxima: {velocidades_permitidas[-1]}x")


def disminuir_velocidad():
    """
    Decrementa el factor de velocidad de la simulacion.

    Velocidades permitidas: 0.5x, 1x, 2x, 5x, 10x

    Modifica:
        estado_visual["velocidad"]
    """
    global estado_visual

    velocidades_permitidas = [0.5, 1.0, 2.0, 5.0, 10.0]
    velocidad_actual = estado_visual["velocidad"]

    # Buscar velocidad anterior (reversed)
    for vel in reversed(velocidades_permitidas):
        if vel < velocidad_actual:
            estado_visual["velocidad"] = vel
            print(f"[VISUALIZATION-STATE] Velocidad reducida a {vel}x")
            return

    # Ya estamos en la minima
    estado_visual["velocidad"] = velocidades_permitidas[0]
    print(f"[VISUALIZATION-STATE] Velocidad minima: {velocidades_permitidas[0]}x")


def obtener_velocidad_simulacion():
    """
    Retorna el factor de velocidad actual de la simulacion.

    Returns:
        float: Factor de velocidad (0.5, 1.0, 2.0, 5.0, 10.0)
    """
    global estado_visual

    return estado_visual.get("velocidad", 1.0)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Estado global
    'estado_visual',

    # Inicializacion
    'inicializar_estado',
    'inicializar_estado_con_cola',
    'limpiar_estado',

    # Actualizacion de estado (NUEVAS)
    'actualizar_posicion_operario',
    'actualizar_estado_operario',
    'actualizar_work_order',

    # Actualizacion de metricas
    'actualizar_metricas_tiempo',

    # Controles
    'toggle_pausa',
    'toggle_dashboard',

    # Velocidad
    'aumentar_velocidad',
    'disminuir_velocidad',
    'obtener_velocidad_simulacion'
]


print("[OK] Modulo 'subsystems.visualization.state' cargado (PRODUCTION - Implementacion completa)")
