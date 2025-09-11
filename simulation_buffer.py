"""
Simulation Buffer - Gestión de estado de eventos de replay

Este módulo proporciona una clase para gestionar de manera explícita 
el buffer de eventos de replay, reemplazando el estado global problemático.

Versión: 1.0.0
Autor: Claude Code Assistant
Fecha: 2025-09-11
"""

from typing import List, Dict, Any


class ReplayBuffer:
    """
    Gestiona el buffer de eventos para replay de manera explícita.
    
    Esta clase encapsula la gestión de eventos de replay, eliminando
    la dependencia de variables globales que causaban problemas de
    referencias múltiples y pérdida de eventos.
    
    Attributes:
        _events (List[Dict[str, Any]]): Lista privada de eventos almacenados
    """
    
    def __init__(self):
        """
        Inicializa un buffer de eventos vacío.
        """
        self._events: List[Dict[str, Any]] = []
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """
        Añade un nuevo evento al buffer.
        
        Args:
            event (Dict[str, Any]): Evento a añadir al buffer
        """
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista completa de eventos almacenados.
        
        Returns:
            List[Dict[str, Any]]: Lista de todos los eventos en el buffer
        """
        return self._events.copy()  # Devolver copia para evitar modificaciones externas
    
    def clear(self) -> None:
        """
        Limpia completamente el buffer de eventos.
        """
        self._events.clear()
    
    def __len__(self) -> int:
        """
        Obtiene el número de eventos en el buffer.
        
        Returns:
            int: Número total de eventos almacenados
        """
        return len(self._events)
    
    def __repr__(self) -> str:
        """
        Representación string del buffer para debugging.
        
        Returns:
            str: Representación del estado actual del buffer
        """
        return f"ReplayBuffer(events={len(self._events)})"