"""
Simulation Buffer - Gestion de estado de eventos de replay

Este modulo proporciona una clase para gestionar de manera explicita 
el buffer de eventos de replay, reemplazando el estado global problematico.

Version: 1.0.0
Autor: Claude Code Assistant
Fecha: 2025-09-11
"""

from typing import List, Dict, Any


class ReplayBuffer:
    """
    Gestiona el buffer de eventos para replay de manera explicita.
    
    Esta clase encapsula la gestion de eventos de replay, eliminando
    la dependencia de variables globales que causaban problemas de
    referencias multiples y perdida de eventos.
    
    Attributes:
        _events (List[Dict[str, Any]]): Lista privada de eventos almacenados
    """
    
    def __init__(self):
        """
        Inicializa un buffer de eventos vacio.
        """
        self._events: List[Dict[str, Any]] = []
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """
        Anade un nuevo evento al buffer.
        
        Args:
            event (Dict[str, Any]): Evento a anadir al buffer
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
        Obtiene el numero de eventos en el buffer.
        
        Returns:
            int: Numero total de eventos almacenados
        """
        return len(self._events)
    
    def __repr__(self) -> str:
        """
        Representacion string del buffer para debugging.
        
        Returns:
            str: Representacion del estado actual del buffer
        """
        return f"ReplayBuffer(events={len(self._events)})"