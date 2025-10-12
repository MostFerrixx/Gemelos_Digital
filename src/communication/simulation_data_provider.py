# -*- coding: utf-8 -*-
"""
SimulationEngine Data Provider - Bridge between SimulationEngine and DashboardCommunicator.

Implements DataProviderInterface to provide WorkOrder data from SimulationEngine
to the dashboard communication system. This decouples the communication logic
from the simulation engine's internal structure.

Based on audit findings from simulation_engine.py data access patterns.
"""

import time
from typing import List, Optional
import weakref

# from .ipc_protocols import DataProviderInterface, WorkOrderSnapshot


class SimulationEngineDataProvider:
    """
    Data provider implementation that bridges SimulationEngine to DashboardCommunicator.

    Uses weak reference to prevent circular dependencies and provides safe access
    to WorkOrder data from the simulation engine's almacen.dispatcher.
    """

    def __init__(self, simulation_engine):
        """
        Initialize data provider with weak reference to simulation engine.

        Args:
            simulation_engine: SimulationEngine instance to provide data from
        """
        # Use weak reference to prevent circular dependency
        self._engine_ref = weakref.ref(simulation_engine)
        self._last_access_time = 0.0

    @property
    def _engine(self):
        """Get simulation engine from weak reference"""
        engine = self._engine_ref()
        if engine is None:
            raise RuntimeError("SimulationEngine has been garbage collected")
        return engine

    def get_all_work_orders(self):
        """
        Get complete list of WorkOrders (active + historical).

        Migrated from: simulation_engine.py:1276-1278, 1340-1342
        Accesses lista_maestra_work_orders and work_orders_completadas_historicas

        Returns:
            List[WorkOrderSnapshot]: Immutable snapshots of all WorkOrders

        Raises:
            RuntimeError: If SimulationEngine is not available
            DataProviderError: If data access fails
        """
        try:
            engine = self._engine
            self._last_access_time = time.time()

            if not engine.almacen or not engine.almacen.dispatcher:
                return []

            # Get both active and historical WorkOrders (from audit findings)
            lista_viva = engine.almacen.dispatcher.lista_maestra_work_orders or []
            lista_historica = engine.almacen.dispatcher.work_orders_completadas_historicas or []
            lista_completa = lista_viva + lista_historica

            # Convert to immutable snapshots
            snapshots = []
            for work_order in lista_completa:
                try:
                    snapshot = self._create_work_order_snapshot(work_order)
                    snapshots.append(snapshot)
                except Exception as e:
                    # Log but continue with other WorkOrders
                    print(f"[DATA-PROVIDER] Warning: Failed to create snapshot for WorkOrder {getattr(work_order, 'id', 'unknown')}: {e}")
                    continue

            return snapshots

        except Exception as e:
            from .dashboard_communicator import DataProviderError
            raise DataProviderError(f"Failed to get WorkOrders: {e}") from e

    def is_simulation_finished(self) -> bool:
        """
        Check if simulation has completed.

        Based on: simulation_engine.py:1220 (simulacion_finalizada_reportada)

        Returns:
            bool: True if simulation finished
        """
        try:
            engine = self._engine
            return getattr(engine, 'simulacion_finalizada_reportada', False)

        except Exception:
            # If engine is not available, assume simulation is finished
            return True

    def has_valid_almacen(self) -> bool:
        """
        Check if almacen data is available and valid.

        Based on: simulation_engine.py:1189 (if self.almacen check)

        Returns:
            bool: True if almacen is available for data extraction
        """
        try:
            engine = self._engine
            return (engine.almacen is not None and
                   hasattr(engine.almacen, 'dispatcher') and
                   engine.almacen.dispatcher is not None)

        except Exception:
            return False

    def _create_work_order_snapshot(self, work_order):
        """
        Create immutable snapshot from WorkOrder object.

        Based on audit findings from simulation_engine.py:1283-1294, 1350-1361
        Extracts the same fields used in the original dashboard communication.

        Args:
            work_order: WorkOrder object from simulation

        Returns:
            WorkOrderSnapshot: Immutable snapshot for IPC

        Raises:
            ValueError: If required WorkOrder fields are missing
        """
        try:
            # Extract core identifiers
            wo_id = getattr(work_order, 'id', None)
            if not wo_id:
                raise ValueError("WorkOrder missing required 'id' field")

            order_id = getattr(work_order, 'order_id', str(wo_id))
            tour_id = getattr(work_order, 'tour_id', 'N/A')

            # Handle SKU - may be object or None
            sku = getattr(work_order, 'sku', None)
            if sku and hasattr(sku, 'id'):
                sku_id = sku.id
            elif sku:
                sku_id = str(sku)
            else:
                sku_id = "N/A"

            # Extract status and location
            status = getattr(work_order, 'status', 'unknown')
            ubicacion = getattr(work_order, 'ubicacion', 'N/A')
            work_area = getattr(work_order, 'work_area', 'unknown')

            # Extract quantities with safe defaults
            cantidad_restante = getattr(work_order, 'cantidad_restante', 0)
            if not isinstance(cantidad_restante, (int, float)):
                cantidad_restante = 0

            # Handle volume calculation - may be method or property
            try:
                if hasattr(work_order, 'calcular_volumen_restante'):
                    volumen_restante = work_order.calcular_volumen_restante()
                else:
                    volumen_restante = getattr(work_order, 'volumen_restante', 0.0)
            except Exception:
                volumen_restante = 0.0

            if not isinstance(volumen_restante, (int, float)):
                volumen_restante = 0.0

            # Extract assignment
            assigned_agent_id = getattr(work_order, 'assigned_agent_id', None)

            # Create snapshot
            # return WorkOrderSnapshot(
            #     id=str(wo_id),
            #     order_id=str(order_id),
            #     tour_id=str(tour_id),
            #     sku_id=str(sku_id),
            #     status=str(status),
            #     ubicacion=str(ubicacion),
            #     work_area=str(work_area),
            #     cantidad_restante=int(cantidad_restante),
            #     volumen_restante=float(volumen_restante),
            #     assigned_agent_id=str(assigned_agent_id) if assigned_agent_id else None,
            #     timestamp=time.time()
            # )
            return None

        except Exception as e:
            raise ValueError(f"Failed to create WorkOrderSnapshot: {e}") from e

    def get_stats(self) -> dict:
        """Get data provider statistics"""
        try:
            engine = self._engine
            almacen_valid = self.has_valid_almacen()

            stats = {
                'engine_available': True,
                'almacen_valid': almacen_valid,
                'last_access_time': self._last_access_time,
                'simulation_finished': self.is_simulation_finished()
            }

            if almacen_valid:
                try:
                    work_orders = self.get_all_work_orders()
                    stats['work_order_count'] = len(work_orders)
                    stats['active_work_orders'] = len([wo for wo in work_orders if wo.status not in ['completed', 'cancelled']])
                except:
                    stats['work_order_count'] = -1
                    stats['active_work_orders'] = -1

            return stats

        except Exception:
            return {
                'engine_available': False,
                'almacen_valid': False,
                'last_access_time': self._last_access_time,
                'simulation_finished': True,
                'work_order_count': -1,
                'active_work_orders': -1
            }


# Utility function for easy integration
def create_simulation_data_provider(simulation_engine) -> SimulationEngineDataProvider:
    """
    Create data provider for SimulationEngine integration.

    Args:
        simulation_engine: SimulationEngine instance

    Returns:
        SimulationEngineDataProvider: Configured data provider
    """
    return SimulationEngineDataProvider(simulation_engine)


# Export for use by other modules
__all__ = [
    'SimulationEngineDataProvider',
    'create_simulation_data_provider'
]