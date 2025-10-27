# -*- coding: utf-8 -*-
"""
Data Manager Module - Central Data Loading for Warehouse Simulation
Digital Twin Warehouse Simulator

Responsibilities:
- Load Warehouse_Logic.xlsx (picking locations, staging areas)
- Create and configure LayoutManager
- Validate data consistency between Excel and TMX
- Expose processed data to simulation components

Author: Digital Twin Warehouse Team
Version: V11 - Migration Phase 3
"""

import os
import openpyxl
from typing import List, Dict, Tuple, Optional, Any
from .layout_manager import LayoutManager


class DataManagerError(Exception):
    """Custom exception for DataManager errors"""
    pass


class DataManager:
    """
    Central data loader for warehouse simulation

    Loads Excel data (Warehouse_Logic.xlsx) and TMX layout,
    validates consistency, and exposes processed data.

    This class acts as the single source of truth for all
    warehouse static data (picking points, staging areas, layout).
    """

    def __init__(self, tmx_file_path: str, excel_file_path: str,
                 configuracion: Optional[Dict[str, Any]] = None, headless: bool = False):
        """
        Initialize DataManager and load all warehouse data

        Args:
            tmx_file_path: Path to TMX map file (e.g., 'layouts/WH1.tmx')
            excel_file_path: Path to Warehouse_Logic.xlsx
            configuracion: Optional configuration dict (for future extensions)

        Raises:
            DataManagerError: If data loading or validation fails
            FileNotFoundError: If required files don't exist
        """
        print(f"[DATA-MANAGER] Iniciando carga de TMX '{tmx_file_path}' "
              f"y archivo de secuencia '{excel_file_path}'...")

        self.tmx_file_path = tmx_file_path

        # BUGFIX V11: Resolver ruta relativa del archivo Excel desde raiz del proyecto
        if not os.path.isabs(excel_file_path):
            # Obtener raiz del proyecto (3 niveles arriba desde src/subsystems/simulation/)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            excel_file_path = os.path.join(project_root, excel_file_path)

        self.excel_file_path = os.path.abspath(excel_file_path)
        self.configuracion = configuracion or {}

        # Create LayoutManager first (needed for validation)
        try:
            self.layout_manager = LayoutManager(tmx_file_path, headless=headless)
        except Exception as e:
            raise DataManagerError(f"Failed to create LayoutManager: {e}")

        # Initialize data structures
        self.puntos_de_picking_ordenados: List[Dict[str, Any]] = []
        self.outbound_staging_locations: Dict[int, Tuple[int, int]] = {}

        # Load Excel data
        self._load_excel_data()

        # Validate consistency between Excel and TMX
        self._validate_data_consistency()

        print(f"[DATA-MANAGER] Plan maestro cargado y ordenado con "
              f"{len(self.puntos_de_picking_ordenados)} puntos.")

        if self.puntos_de_picking_ordenados:
            primer = self.puntos_de_picking_ordenados[0]
            ultimo = self.puntos_de_picking_ordenados[-1]
            print(f"  - Primer punto en secuencia: {primer}")
            print(f"  - Ultimo punto en secuencia: {ultimo}")

    # ========================================================================
    # PUBLIC INTERFACE - Data Access Methods
    # ========================================================================

    def get_picking_points(self) -> List[Dict[str, Any]]:
        """
        Return ordered list of picking points with all metadata

        Each point is a dict with keys:
        - x, y: Grid coordinates
        - ubicacion_grilla: Tuple (x, y)
        - pick_sequence: Order in master plan
        - equipment_required: Agent type (e.g., 'GroundOperator')
        - sku_initial: Initial SKU at this location
        - qty_initial: Initial quantity
        - WorkGroup: Work group identifier (e.g., 'WG_A')
        - WorkArea: Work area identifier (e.g., 'Area_Ground')

        Returns:
            List of dicts, sorted by pick_sequence
        """
        return self.puntos_de_picking_ordenados

    def get_outbound_staging_locations(self) -> Dict[int, Tuple[int, int]]:
        """
        Return dict mapping staging_id -> (x, y) grid coordinates

        Returns:
            Dict {staging_id: (x, y)} for all outbound staging areas
        """
        return self.outbound_staging_locations

    def get_layout_manager(self) -> LayoutManager:
        """
        Return configured LayoutManager instance

        Returns:
            LayoutManager with loaded TMX data
        """
        return self.layout_manager

    def get_pathfinder(self):
        """
        Return pathfinder instance (convenience method)

        Creates pathfinder from LayoutManager if not already created.

        Returns:
            Pathfinder instance configured for this layout
        """
        if not hasattr(self.layout_manager, 'pathfinder'):
            from .pathfinder import Pathfinder
            self.layout_manager.pathfinder = Pathfinder(
                self.layout_manager.collision_matrix,
                self.layout_manager.grid_width,
                self.layout_manager.grid_height
            )
        return self.layout_manager.pathfinder

    # ========================================================================
    # PRIVATE METHODS - Data Loading
    # ========================================================================

    def _load_excel_data(self):
        """
        Load and parse Warehouse_Logic.xlsx

        Expects two sheets:
        - PickingLocations: x, y, pick_sequence, WorkArea, etc.
        - OutboundStaging: staging_id, x, y

        Raises:
            DataManagerError: If Excel loading fails
        """
        print(f"[DATA-MANAGER] Leyendo archivo Excel: {self.excel_file_path}")

        try:
            workbook = openpyxl.load_workbook(self.excel_file_path, data_only=True)
        except FileNotFoundError:
            raise DataManagerError(
                f"Excel file not found: {self.excel_file_path}"
            )
        except Exception as e:
            raise DataManagerError(f"Error loading Excel file: {e}")

        # Process PickingLocations sheet (REQUIRED)
        if 'PickingLocations' in workbook.sheetnames:
            sheet = workbook['PickingLocations']
            self._process_picking_locations(sheet)
        else:
            workbook.close()
            raise DataManagerError(
                "Sheet 'PickingLocations' not found in Excel file. "
                "This sheet is required for warehouse operation."
            )

        # Process OutboundStaging sheet (OPTIONAL with fallback)
        if 'OutboundStaging' in workbook.sheetnames:
            sheet = workbook['OutboundStaging']
            self._process_outbound_staging(sheet)
        else:
            print("[DATA-MANAGER WARNING] Sheet 'OutboundStaging' not found - "
                  "generating default staging locations")
            self._generate_default_staging_locations()

        workbook.close()

    def _process_picking_locations(self, sheet):
        """
        Process PickingLocations sheet from Excel

        Expected columns:
        - x: Grid X coordinate
        - y: Grid Y coordinate
        - pick_sequence: Order in master plan
        - equipment_required: Agent type
        - sku_initial: Initial SKU code
        - qty_initial: Initial quantity
        - WorkGroup: Work group identifier
        - WorkArea: Work area identifier

        Args:
            sheet: openpyxl worksheet object

        Raises:
            DataManagerError: If required columns are missing
        """
        # Find header row (should contain 'x' column)
        header_row = None
        for idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
            if row and any(str(cell).lower() == 'x' for cell in row if cell):
                header_row = idx
                break

        if not header_row:
            raise DataManagerError(
                "Header row with 'x' column not found in PickingLocations sheet"
            )

        # Read header
        headers = [cell.value for cell in sheet[header_row]]

        # Process data rows
        data_rows = []
        for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
            if not row or not row[0]:  # Skip empty rows
                continue

            row_dict = {}
            for idx, header in enumerate(headers):
                if header and idx < len(row):
                    row_dict[header] = row[idx]

            data_rows.append(row_dict)

        print(f"[DATA-MANAGER] Hoja 'PickingLocations' cargada con "
              f"{len(data_rows)} registros")

        # Convert to standardized format
        for row_data in data_rows:
            try:
                punto = {
                    'x': int(row_data.get('x', 0)),
                    'y': int(row_data.get('y', 0)),
                    'pick_sequence': int(row_data.get('pick_sequence', 0)),
                    'equipment_required': str(row_data.get('equipment_required', 'GroundOperator')),
                    'sku_initial': str(row_data.get('sku_initial', 'SKU000')),
                    'qty_initial': int(row_data.get('qty_initial', 1)),
                    'WorkGroup': str(row_data.get('WorkGroup', 'WG_Default')),
                    'WorkArea': str(row_data.get('WorkArea', 'Area_Ground')),
                }

                # Add grid location tuple for convenience
                punto['ubicacion_grilla'] = (punto['x'], punto['y'])

                self.puntos_de_picking_ordenados.append(punto)

            except (ValueError, TypeError) as e:
                print(f"[DATA-MANAGER WARNING] Skipping invalid row: {row_data} - {e}")
                continue

        # Sort by pick_sequence
        self.puntos_de_picking_ordenados.sort(key=lambda p: p['pick_sequence'])

        print(f"[DATA-MANAGER] Columna 'WorkGroup' procesada correctamente")
        print(f"[DATA-MANAGER] Columna 'WorkArea' procesada correctamente")

    def _process_outbound_staging(self, sheet):
        """
        Process OutboundStaging sheet from Excel

        Expected columns:
        - staging_id: Unique identifier (integer)
        - x: Grid X coordinate
        - y: Grid Y coordinate

        Args:
            sheet: openpyxl worksheet object
        """
        # Find header row
        header_row = None
        for idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=10, values_only=True), start=1):
            if row and any('staging' in str(cell).lower() for cell in row if cell):
                header_row = idx
                break

        if not header_row:
            # Fallback: assume first row is header
            header_row = 1

        headers = [cell.value for cell in sheet[header_row]]

        # Process staging locations
        staging_dict = {}
        for row in sheet.iter_rows(min_row=header_row + 1, values_only=True):
            if not row or not row[0]:
                continue

            row_dict = {}
            for idx, header in enumerate(headers):
                if header and idx < len(row):
                    row_dict[header] = row[idx]

            try:
                # Handle different header variations
                staging_id_key = None
                for key in row_dict.keys():
                    if 'staging' in str(key).lower() and 'id' in str(key).lower():
                        staging_id_key = key
                        break

                if not staging_id_key:
                    staging_id_key = 'staging_id'

                staging_id = int(row_dict.get(staging_id_key, 0))
                x = int(row_dict.get('x', 0))
                y = int(row_dict.get('y', 0))

                if staging_id > 0:  # Only add valid IDs
                    staging_dict[staging_id] = (x, y)

            except (ValueError, TypeError, KeyError) as e:
                print(f"[DATA-MANAGER WARNING] Skipping invalid staging row: {row_dict} - {e}")
                continue

        self.outbound_staging_locations = staging_dict

        print(f"[DATA-MANAGER] Hoja 'OutboundStaging' cargada con "
              f"{len(staging_dict)} registros")
        print(f"[DATA-MANAGER] OutboundStaging procesado: {staging_dict}")

    def _generate_default_staging_locations(self):
        """
        Generate default staging locations if OutboundStaging sheet is missing

        Creates 7 staging areas along the bottom edge of the map
        """
        grid_h = self.layout_manager.grid_height

        # Create 7 staging areas along bottom edge (y = grid_h - 1)
        # Distributed evenly across the width
        num_staging = 7
        spacing = max(1, self.layout_manager.grid_width // (num_staging + 1))

        staging_dict = {}
        for i in range(1, num_staging + 1):
            x = i * spacing
            y = grid_h - 1
            staging_dict[i] = (x, y)

        self.outbound_staging_locations = staging_dict

        print(f"[DATA-MANAGER] Default staging locations generated: {staging_dict}")

    def _validate_data_consistency(self):
        """
        Validate that Excel coordinates are within TMX grid bounds

        Checks:
        - All picking points are within grid
        - All staging locations are within grid
        - Coordinates are non-negative

        Raises:
            DataManagerError: If critical validation fails
        """
        grid_w = self.layout_manager.grid_width
        grid_h = self.layout_manager.grid_height

        # Validate picking points
        invalid_points = []
        for punto in self.puntos_de_picking_ordenados:
            x, y = punto['x'], punto['y']
            if not (0 <= x < grid_w and 0 <= y < grid_h):
                invalid_points.append((x, y, punto['pick_sequence']))

        if invalid_points:
            # Warning but not fatal - some points may be intentionally outside
            print(f"[DATA-MANAGER WARNING] {len(invalid_points)} puntos fuera "
                  f"del grid {grid_w}x{grid_h}")
            if len(invalid_points) <= 5:
                print(f"  Puntos invalidos: {invalid_points}")
            else:
                print(f"  Primeros 5 puntos invalidos: {invalid_points[:5]}")

        # Validate staging locations (CRITICAL - must be valid)
        invalid_staging = []
        for staging_id, (x, y) in self.outbound_staging_locations.items():
            if not (0 <= x < grid_w and 0 <= y < grid_h):
                invalid_staging.append((staging_id, x, y))

        if invalid_staging:
            raise DataManagerError(
                f"Staging locations out of bounds: {invalid_staging}. "
                f"Valid grid range: 0-{grid_w-1} x 0-{grid_h-1}"
            )

        print(f"[DATA-MANAGER] Validacion completada:")
        print(f"  - {len(self.puntos_de_picking_ordenados)} picking points validados")
        print(f"  - {len(self.outbound_staging_locations)} staging areas validadas")
        print(f"  - Grid bounds: {grid_w}x{grid_h}")

    def __repr__(self):
        return (f"DataManager(picking_points={len(self.puntos_de_picking_ordenados)}, "
                f"staging_areas={len(self.outbound_staging_locations)}, "
                f"grid={self.layout_manager.grid_width}x{self.layout_manager.grid_height})")
