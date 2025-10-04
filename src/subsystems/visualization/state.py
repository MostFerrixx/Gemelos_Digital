# -*- coding: utf-8 -*-
"""
Visualization State Management - Estado visual global para la simulacion

FASE 1a: ESQUELETO FUNCIONAL MINIMO
Este modulo contiene implementaciones stub que permiten importacion y ejecucion
sin errores, pero sin funcionalidad completa aun.

Estado: SKELETON - Pendiente de implementacion completa
"""

# =============================================================================
# ESTADO VISUAL GLOBAL
# =============================================================================

# Variable global que mantiene el estado de la visualizacion
estado_visual = {
    "operarios": {},           # Dict[agent_id: str, agent_data: dict]
    "work_orders": {},         # Dict[wo_id: str, wo_data: dict]
    "metricas": {},            # Dict de metricas de simulacion
    "pausa": False,            # Estado de pausa de la simulacion
    "velocidad": 1.0,          # Factor de velocidad (0.5x, 1x, 2x, etc.)
    "dashboard_visible": True  # Visibilidad del dashboard
}


# =============================================================================
# FUNCIONES DE INICIALIZACION
# =============================================================================

def inicializar_estado(almacen, env, configuracion, layout_manager):
    """
    Inicializa el estado visual para una nueva simulacion.

    Args:
        almacen: Instancia de AlmacenMejorado
        env: Entorno SimPy
        configuracion: Dict de configuracion
        layout_manager: Instancia de LayoutManager para TMX

    SKELETON: Implementacion minima - solo resetea estado
    """
    global estado_visual

    # Reset basico del estado
    estado_visual["operarios"] = {}
    estado_visual["work_orders"] = {}
    estado_visual["metricas"] = {}
    estado_visual["pausa"] = False
    estado_visual["velocidad"] = 1.0
    estado_visual["dashboard_visible"] = True

    print("[VISUALIZATION-STATE] Estado visual inicializado (SKELETON)")


def inicializar_estado_con_cola(almacen, env, configuracion, layout_manager, event_queue):
    """
    Inicializa el estado visual para multiprocessing con cola de eventos.

    Args:
        almacen: Instancia de AlmacenMejorado
        env: Entorno SimPy
        configuracion: Dict de configuracion
        layout_manager: Instancia de LayoutManager
        event_queue: multiprocessing.Queue para eventos visuales

    SKELETON: Implementacion minima - delega a inicializar_estado
    """
    # Por ahora, simplemente inicializar normalmente
    inicializar_estado(almacen, env, configuracion, layout_manager)

    # TODO: Implementar logica de cola de eventos
    print("[VISUALIZATION-STATE] Estado con cola inicializado (SKELETON)")


def limpiar_estado():
    """
    Resetea el estado visual a valores por defecto.

    SKELETON: Implementacion minima
    """
    global estado_visual

    estado_visual["operarios"] = {}
    estado_visual["work_orders"] = {}
    estado_visual["metricas"] = {}
    estado_visual["pausa"] = False
    estado_visual["velocidad"] = 1.0
    estado_visual["dashboard_visible"] = True

    print("[VISUALIZATION-STATE] Estado visual limpiado (SKELETON)")


# =============================================================================
# FUNCIONES DE ACTUALIZACION DE METRICAS
# =============================================================================

def actualizar_metricas_tiempo(operarios_dict):
    """
    Actualiza las metricas de tiempo de los operarios.

    Args:
        operarios_dict: Dict de operarios del estado visual

    SKELETON: Implementacion minima - no hace nada
    """
    # TODO: Implementar calculo de metricas de tiempo
    pass


# =============================================================================
# FUNCIONES DE CONTROL (TOGGLES)
# =============================================================================

def toggle_pausa():
    """
    Alterna el estado de pausa de la simulacion.

    Returns:
        bool: Nuevo estado de pausa (True si pausado, False si corriendo)

    SKELETON: Implementacion funcional basica
    """
    global estado_visual

    estado_visual["pausa"] = not estado_visual["pausa"]

    return estado_visual["pausa"]


def toggle_dashboard():
    """
    Alterna la visibilidad del dashboard.

    Returns:
        bool: Nuevo estado de visibilidad (True si visible, False si oculto)

    SKELETON: Implementacion funcional basica
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

    SKELETON: Implementacion funcional basica
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

    SKELETON: Implementacion funcional basica
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

    SKELETON: Implementacion funcional completa
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

    # Actualizacion
    'actualizar_metricas_tiempo',

    # Controles
    'toggle_pausa',
    'toggle_dashboard',

    # Velocidad
    'aumentar_velocidad',
    'disminuir_velocidad',
    'obtener_velocidad_simulacion'
]


print("[OK] Modulo 'subsystems.visualization.state' cargado (SKELETON - Funcional minimo)")
