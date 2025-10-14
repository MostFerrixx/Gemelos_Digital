# -*- coding: utf-8 -*-
"""
SimulationContext - Contexto unificado para datos de simulacion.
Fase 2 del refactor AnalyticsExporter - Encapsulacion robusta de datos.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SimulationContext:
    """
    Contexto unificado que encapsula todos los datos necesarios para exportacion.

    Reemplaza el patron de multiples parametros en constructor con un
    objeto cohesivo que garantiza consistencia de datos.

    Attributes:
        almacen: Objeto AlmacenMejorado con datos de simulacion
        configuracion: Dict de configuracion de la simulacion
        session_timestamp: Timestamp unificado de la sesion
        session_output_dir: Directorio de salida de la sesion
        event_log: Lista de eventos capturados durante simulacion
        metadata: Metadatos adicionales opcionales
    """

    # Datos core obligatorios
    almacen: Any  # AlmacenMejorado object
    configuracion: Dict[str, Any]

    # Datos de sesion con defaults inteligentes
    session_timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    session_output_dir: Optional[str] = None

    # Datos de eventos (derivados del almacen)
    event_log: Optional[List[Dict]] = field(default=None)

    # Metadatos opcionales
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-inicializacion para derivar datos automaticamente"""
        # Derivar event_log del almacen si no se proporciona
        if self.event_log is None and self.almacen and hasattr(self.almacen, 'event_log'):
            self.event_log = self.almacen.event_log

        # Generar session_output_dir si no se proporciona
        if self.session_output_dir is None:
            import os
            self.session_output_dir = os.path.join("output", f"simulation_{self.session_timestamp}")

    @classmethod
    def from_simulation_engine(cls, engine):
        """
        Factory method para crear contexto desde SimulationEngine existente.

        Args:
            engine: Instancia de SimulationEngine

        Returns:
            SimulationContext: Contexto completamente inicializado
        """
        return cls(
            almacen=engine.almacen,
            configuracion=engine.configuracion,
            session_timestamp=getattr(engine, 'session_timestamp', None),
            session_output_dir=getattr(engine, 'session_output_dir', None),
            # event_log se deriva automaticamente en __post_init__
        )

    def validate(self) -> bool:
        """
        Valida que el contexto contiene todos los datos necesarios.

        Returns:
            bool: True si el contexto es valido

        Raises:
            ValueError: Si faltan datos criticos
        """
        if not self.almacen:
            raise ValueError("SimulationContext requiere almacen valido")

        if not self.configuracion:
            # Permitir configuracion vacia como caso valido
            self.configuracion = {}

        if not self.session_timestamp:
            raise ValueError("SimulationContext requiere session_timestamp valido")

        if not self.event_log and hasattr(self.almacen, 'event_log'):
            # Intentar derivar event_log automaticamente
            self.event_log = self.almacen.event_log

        return True

    def get_export_metadata(self) -> Dict[str, Any]:
        """
        Genera metadatos para exportacion.

        Returns:
            dict: Metadatos de exportacion
        """
        return {
            'session_timestamp': self.session_timestamp,
            'session_output_dir': self.session_output_dir,
            'total_events': len(self.event_log) if self.event_log else 0,
            'configuration_keys': list(self.configuracion.keys()) if self.configuracion else [],
            'export_generated_at': datetime.now().isoformat(),
        }


@dataclass
class ExportResult:
    """
    Resultado estructurado de operacion de exportacion.

    Proporciona informacion detallada sobre el exito/fallo de exportacion
    con capacidades de rollback y debugging mejorado.

    Attributes:
        success: True si exportacion fue exitosa
        generated_files: Lista de archivos generados exitosamente
        errors: Lista de errores encontrados
        warnings: Lista de warnings no criticos
        execution_time: Tiempo de ejecucion en segundos
        export_metadata: Metadatos de la exportacion
        rollback_info: Informacion para rollback en caso de fallo
    """

    success: bool = True
    generated_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    export_metadata: Dict[str, Any] = field(default_factory=dict)
    rollback_info: Dict[str, Any] = field(default_factory=dict)

    def add_file(self, file_path: str):
        """Agregar archivo generado exitosamente"""
        self.generated_files.append(file_path)

    def add_error(self, error_message: str):
        """Agregar error y marcar como fallido"""
        self.errors.append(error_message)
        self.success = False

    def add_warning(self, warning_message: str):
        """Agregar warning (no afecta success)"""
        self.warnings.append(warning_message)

    def set_execution_time(self, start_time: float, end_time: float):
        """Establecer tiempo de ejecucion"""
        self.execution_time = end_time - start_time

    def rollback_on_failure(self):
        """
        Ejecuta rollback de archivos generados en caso de fallo.

        Returns:
            bool: True si rollback fue exitoso
        """
        if self.success:
            return True  # No rollback necesario

        import os
        rollback_success = True

        for file_path in self.generated_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"[ROLLBACK] Archivo eliminado: {file_path}")
            except Exception as e:
                print(f"[ROLLBACK ERROR] No se pudo eliminar {file_path}: {e}")
                rollback_success = False

        # Limpiar directorio si esta vacio
        if self.rollback_info.get('output_dir'):
            output_dir = self.rollback_info['output_dir']
            try:
                if os.path.exists(output_dir) and not os.listdir(output_dir):
                    os.rmdir(output_dir)
                    print(f"[ROLLBACK] Directorio eliminado: {output_dir}")
            except Exception as e:
                print(f"[ROLLBACK ERROR] No se pudo eliminar directorio {output_dir}: {e}")
                rollback_success = False

        return rollback_success

    def get_summary(self) -> str:
        """
        Genera resumen textual del resultado.

        Returns:
            str: Resumen formateado del resultado
        """
        status = "EXITOSO" if self.success else "FALLIDO"
        summary = [
            f"Exportacion: {status}",
            f"Archivos generados: {len(self.generated_files)}",
            f"Errores: {len(self.errors)}",
            f"Warnings: {len(self.warnings)}",
            f"Tiempo ejecucion: {self.execution_time:.2f}s"
        ]

        if self.generated_files:
            summary.append("Archivos:")
            for i, file_path in enumerate(self.generated_files, 1):
                summary.append(f"  {i}. {file_path}")

        if self.errors:
            summary.append("Errores:")
            for error in self.errors:
                summary.append(f"  - {error}")

        if self.warnings:
            summary.append("Warnings:")
            for warning in self.warnings:
                summary.append(f"  - {warning}")

        return "\n".join(summary)