# -*- coding: utf-8 -*-
"""
Configuration Manager for Web Configurator
Manages configuration loading, saving, validation, and presets.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import openpyxl


class WebConfigurationManager:
    """Manages configurations for the web configurator"""
    
    def __init__(self, project_root: str):
        """
        Initialize configuration manager
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.config_path = os.path.join(project_root, "config.json")
        self.presets_dir = os.path.join(project_root, "data", "config_presets")
        
        # Create presets directory if it doesn't exist
        os.makedirs(self.presets_dir, exist_ok=True)
        
        print(f"[CONFIG_MANAGER] Initialized with root: {project_root}")
        print(f"[CONFIG_MANAGER] Config path: {self.config_path}")
        print(f"[CONFIG_MANAGER] Presets directory: {self.presets_dir}")
    
    def load_config(self) -> Dict:
        """
        Load current config.json
        
        Returns:
            Configuration dictionary
        """
        try:
            if not os.path.exists(self.config_path):
                print(f"[CONFIG_MANAGER] Config file not found, using defaults")
                return self._get_default_config()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"[CONFIG_MANAGER] Loaded config from {self.config_path}")
            return config
            
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error loading config: {e}")
            return self._get_default_config()
    
    def save_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """
        Save configuration to config.json with validation
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (success, error_messages)
        """
        try:
            # Validate first
            is_valid, errors = self.validate_config(config)
            if not is_valid:
                return False, errors
            
            # Backup existing config
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup"
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                print(f"[CONFIG_MANAGER] Created backup: {backup_path}")
            
            # Save new config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print(f"[CONFIG_MANAGER] Saved config to {self.config_path}")
            return True, []
            
        except Exception as e:
            error_msg = f"Error saving config: {str(e)}"
            print(f"[CONFIG_MANAGER ERROR] {error_msg}")
            return False, [error_msg]
    
    def validate_config(self, config: Dict) -> Tuple[bool, List[str]]:
        """
        Validate configuration structure and values
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Validate total_ordenes
            if 'total_ordenes' not in config or config['total_ordenes'] <= 0:
                errors.append("total_ordenes must be greater than 0")
            
            # Validate distribucion_tipos
            if 'distribucion_tipos' in config:
                dist = config['distribucion_tipos']
                total_pct = 0
                
                for tipo in ['pequeno', 'mediano', 'grande']:
                    if tipo not in dist:
                        errors.append(f"Missing distribution type: {tipo}")
                        continue
                    
                    if 'porcentaje' not in dist[tipo]:
                        errors.append(f"Missing percentage for {tipo}")
                    else:
                        total_pct += dist[tipo]['porcentaje']
                    
                    if 'volumen' not in dist[tipo]:
                        errors.append(f"Missing volume for {tipo}")
                
                if total_pct != 100:
                    errors.append(f"Distribution percentages must sum to 100% (current: {total_pct}%)")
            else:
                errors.append("Missing distribucion_tipos")
            
            # Validate capacidad_carro
            if 'capacidad_carro' not in config or config['capacidad_carro'] <= 0:
                errors.append("capacidad_carro must be greater than 0")
            
            # Validate staging distribution
            if 'outbound_staging_distribution' in config:
                staging_dist = config['outbound_staging_distribution']
                total_staging = sum(staging_dist.values())
                
                if total_staging != 100:
                    errors.append(f"Staging distribution must sum to 100% (current: {total_staging}%)")
            
            # Validate agent_types if present
            if 'agent_types' in config:
                if not isinstance(config['agent_types'], list):
                    errors.append("agent_types must be a list")
                else:
                    for idx, agent in enumerate(config['agent_types']):
                        if 'type' not in agent:
                            errors.append(f"Agent {idx}: missing type")
                        if 'capacity' not in agent or agent['capacity'] <= 0:
                            errors.append(f"Agent {idx}: invalid capacity")
                        if 'discharge_time' not in agent or agent['discharge_time'] <= 0:
                            errors.append(f"Agent {idx}: invalid discharge_time")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                print(f"[CONFIG_MANAGER] Configuration validation: PASSED")
            else:
                print(f"[CONFIG_MANAGER] Configuration validation: FAILED - {len(errors)} errors")
                for error in errors:
                    print(f"  - {error}")
            
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            print(f"[CONFIG_MANAGER ERROR] {error_msg}")
            return False, [error_msg]
    
    def extract_work_areas(self, sequence_file: str) -> List[str]:
        """
        Extract work areas from sequence file (Excel/CSV)
        
        Args:
            sequence_file: Path to sequence file (relative to project root)
            
        Returns:
            List of work area names
        """
        try:
            # Construct absolute path
            if not os.path.isabs(sequence_file):
                sequence_file = os.path.join(self.project_root, sequence_file)
            
            if not os.path.exists(sequence_file):
                print(f"[CONFIG_MANAGER] Sequence file not found: {sequence_file}")
                return []
            
            print(f"[CONFIG_MANAGER] Extracting work areas from: {sequence_file}")
            
            # Read Excel file
            wb = openpyxl.load_workbook(sequence_file, read_only=True, data_only=True)
            
            # Look for PickingLocations or Warehouse_Logic sheet
            sheet_name = None
            if 'PickingLocations' in wb.sheetnames:
                sheet_name = 'PickingLocations'
            elif 'Warehouse_Logic' in wb.sheetnames:
                sheet_name = 'Warehouse_Logic'
            
            if not sheet_name:
                print(f"[CONFIG_MANAGER] No suitable sheet found in {sequence_file}")
                wb.close()
                return []
            
            ws = wb[sheet_name]
            work_areas = set()
            
            # Find WorkArea column
            headers = [cell.value for cell in ws[1]]
            wa_col_idx = None
            for idx, header in enumerate(headers):
                if header and 'WorkArea' in str(header):
                    wa_col_idx = idx
                    break
            
            if wa_col_idx is not None:
                # Extract work areas
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row and len(row) > wa_col_idx:
                        work_area = row[wa_col_idx]
                        if work_area:
                            work_areas.add(str(work_area))
            
            wb.close()
            
            result = sorted(list(work_areas))
            print(f"[CONFIG_MANAGER] Extracted {len(result)} work areas: {result}")
            return result
            
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error extracting work areas: {e}")
            return []
    
    def list_configurations(self) -> List[Dict]:
        """
        List all saved configuration presets
        
        Returns:
            List of configuration metadata dictionaries
        """
        try:
            configs = []
            
            if not os.path.exists(self.presets_dir):
                return configs
            
            for filename in os.listdir(self.presets_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(self.presets_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        preset_data = json.load(f)
                    
                    # Extract metadata
                    metadata = preset_data.get('metadata', {})
                    config_id = metadata.get('id', filename.replace('.json', ''))
                    
                    configs.append({
                        'id': config_id,
                        'name': metadata.get('name', filename),
                        'description': metadata.get('description', ''),
                        'created_at': metadata.get('created_at', ''),
                        'is_default': metadata.get('is_default', False),
                        'filename': filename
                    })
                    
                except Exception as e:
                    print(f"[CONFIG_MANAGER] Error loading preset {filename}: {e}")
                    continue
            
            # Sort by creation date, newest first
            configs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            print(f"[CONFIG_MANAGER] Listed {len(configs)} configurations")
            return configs
            
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error listing configurations: {e}")
            return []
    
    def save_configuration(self, name: str, description: str, config: Dict, 
                          is_default: bool = False) -> Tuple[bool, str, List[str]]:
        """
        Save configuration as a preset
        
        Args:
            name: Configuration name
            description: Configuration description
            config: Configuration dictionary
            is_default: Whether this should be the default configuration
            
        Returns:
            Tuple of (success, config_id, error_messages)
        """
        try:
            # Validate configuration first
            is_valid, errors = self.validate_config(config)
            if not is_valid:
                return False, "", errors
            
            # Generate unique ID
            config_id = str(uuid.uuid4())
            
            # Create preset data structure
            preset_data = {
                'metadata': {
                    'id': config_id,
                    'name': name,
                    'description': description,
                    'created_at': datetime.now().isoformat(),
                    'is_default': is_default
                },
                'configuration': config
            }
            
            # If setting as default, unset other defaults
            if is_default:
                self._unset_all_defaults()
            
            # Save preset file
            filename = f"{config_id}.json"
            filepath = os.path.join(self.presets_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=4, ensure_ascii=False)
            
            print(f"[CONFIG_MANAGER] Saved configuration '{name}' as {filename}")
            return True, config_id, []
            
        except Exception as e:
            error_msg = f"Error saving configuration: {str(e)}"
            print(f"[CONFIG_MANAGER ERROR] {error_msg}")
            return False, "", [error_msg]
    
    def load_configuration(self, config_id: str) -> Optional[Dict]:
        """
        Load a configuration preset by ID
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration dictionary or None if not found
        """
        try:
            filename = f"{config_id}.json"
            filepath = os.path.join(self.presets_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"[CONFIG_MANAGER] Configuration {config_id} not found")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            config = preset_data.get('configuration', {})
            print(f"[CONFIG_MANAGER] Loaded configuration {config_id}")
            return config
            
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error loading configuration {config_id}: {e}")
            return None
    
    def delete_configuration(self, config_id: str) -> Tuple[bool, List[str]]:
        """
        Delete a configuration preset
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Tuple of (success, error_messages)
        """
        try:
            filename = f"{config_id}.json"
            filepath = os.path.join(self.presets_dir, filename)
            
            if not os.path.exists(filepath):
                return False, [f"Configuration {config_id} not found"]
            
            os.remove(filepath)
            print(f"[CONFIG_MANAGER] Deleted configuration {config_id}")
            return True, []
            
        except Exception as e:
            error_msg = f"Error deleting configuration: {str(e)}"
            print(f"[CONFIG_MANAGER ERROR] {error_msg}")
            return False, [error_msg]
    
    def set_default_configuration(self, config_id: str) -> Tuple[bool, List[str]]:
        """
        Set a configuration as the default
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Tuple of (success, error_messages)
        """
        try:
            filename = f"{config_id}.json"
            filepath = os.path.join(self.presets_dir, filename)
            
            if not os.path.exists(filepath):
                return False, [f"Configuration {config_id} not found"]
            
            # Unset all defaults first
            self._unset_all_defaults()
            
            # Load and update this configuration
            with open(filepath, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
            
            preset_data['metadata']['is_default'] = True
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=4, ensure_ascii=False)
            
            print(f"[CONFIG_MANAGER] Set {config_id} as default configuration")
            return True, []
            
        except Exception as e:
            error_msg = f"Error setting default configuration: {str(e)}"
            print(f"[CONFIG_MANAGER ERROR] {error_msg}")
            return False, [error_msg]
    
    def get_default_configuration(self) -> Optional[Dict]:
        """
        Get the default configuration
        
        Returns:
            Configuration dictionary or None if no default is set
        """
        try:
            configs = self.list_configurations()
            
            for config_meta in configs:
                if config_meta.get('is_default', False):
                    return self.load_configuration(config_meta['id'])
            
            print(f"[CONFIG_MANAGER] No default configuration found")
            return None
            
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error getting default configuration: {e}")
            return None
    
    def _unset_all_defaults(self):
        """Unset default flag from all configurations"""
        try:
            if not os.path.exists(self.presets_dir):
                return
            
            for filename in os.listdir(self.presets_dir):
                if not filename.endswith('.json'):
                    continue
                
                filepath = os.path.join(self.presets_dir, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        preset_data = json.load(f)
                    
                    if preset_data.get('metadata', {}).get('is_default', False):
                        preset_data['metadata']['is_default'] = False
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(preset_data, f, indent=4, ensure_ascii=False)
                        
                        print(f"[CONFIG_MANAGER] Unset default flag from {filename}")
                
                except Exception as e:
                    print(f"[CONFIG_MANAGER] Error processing {filename}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[CONFIG_MANAGER ERROR] Error unsetting defaults: {e}")
    
    def _get_default_config(self) -> Dict:
        """Get hardcoded default configuration"""
        return {
            "total_ordenes": 300,
            "distribucion_tipos": {
                "pequeno": {"porcentaje": 60, "volumen": 5},
                "mediano": {"porcentaje": 30, "volumen": 25},
                "grande": {"porcentaje": 10, "volumen": 80}
            },
            "capacidad_carro": 150,
            "dispatch_strategy": "Optimizacion Global",
            "tour_type": "Tour Mixto (Multi-Destino)",
            "layout_file": "layouts/WH1.tmx",
            "sequence_file": "layouts/Warehouse_Logic.xlsx",
            "map_scale": 1.3,
            "num_operarios_terrestres": 2,
            "num_montacargas": 1,
            "num_operarios_total": 3,
            "capacidad_montacargas": 1000,
            "tiempo_descarga_por_tarea": 5,
            "assignment_rules": {
                "GroundOperator": {},
                "Forklift": {}
            },
            "outbound_staging_distribution": {
                "1": 100, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0
            },
            "agent_types": [],
            "tareas_zona_a": 0,
            "tareas_zona_b": 0,
            "num_operarios": 3
        }
