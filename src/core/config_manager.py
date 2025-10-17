# -*- coding: utf-8 -*-
"""
ConfigurationManager - Gestion centralizada de configuracion para Simulacion y Replay.
Refactorizado desde SimulationEngine.cargar_configuracion() y ReplayEngine.cargar_configuracion().
Maneja carga de config.json con fallback a defaults y validacion robusta.
"""

import json
import os
from typing import Dict, List, Optional


class ConfigurationError(Exception):
    """Excepcion personalizada para errores de configuracion"""
    pass


class ConfigurationManager:
    """
    Manager centralizado para gestion de configuracion JSON

    Caracteristicas:
    - Carga desde config.json con fallback automatico a defaults
    - Sanitizacion automatica de assignment_rules
    - Validacion de claves esenciales
    - Manejo robusto de excepciones
    - Logging detallado del proceso de carga
    """

    # Claves esenciales que deben existir en la configuracion
    REQUIRED_KEYS = [
        'layout_file',
        'sequence_file',
        'num_operarios_total'
    ]

    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa ConfigurationManager y carga configuracion automaticamente

        Args:
            config_path: Ruta al archivo de configuracion. Si None, usa 'config.json'

        BUGFIX V11: Busca config.json en raiz del proyecto (2 niveles arriba de src/core/)
        """
        if config_path is None:
            # BUGFIX: Usar config.json en raiz del proyecto (2 niveles arriba de src/core/)
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            config_path = os.path.join(project_root, "config.json")

        self.config_path = config_path
        self.configuration = self._load_configuration()

        # Log resumen de configuracion cargada
        self._log_configuration_summary()

    def _load_configuration(self) -> Dict:
        """
        Carga configuracion desde archivo JSON con fallback robusto

        Returns:
            dict: Configuracion cargada y sanitizada

        Raises:
            ConfigurationError: Si falla la carga y no se puede usar fallback
        """
        try:
            # Intentar cargar config.json
            if os.path.exists(self.config_path):
                print(f"[CONFIG] Cargando configuracion desde: {self.config_path}")
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # Sanitizar assignment_rules: convertir claves str a int
                config = self._sanitize_assignment_rules(config)

                print("[CONFIG] Configuracion cargada exitosamente desde archivo JSON")
                return config

            else:
                print("[CONFIG] config.json no encontrado, usando configuracion por defecto")
                config = self._get_default_config()
                print("[CONFIG] Configuracion por defecto cargada")
                return config

        except json.JSONDecodeError as e:
            print(f"[CONFIG ERROR] Error al parsear config.json: {e}")
            print("[CONFIG] Usando configuracion por defecto como fallback")
            return self._get_default_config()

        except Exception as e:
            print(f"[CONFIG ERROR] Error inesperado cargando configuracion: {e}")
            print("[CONFIG] Usando configuracion por defecto como fallback")
            return self._get_default_config()

    def _sanitize_assignment_rules(self, config: Dict) -> Dict:
        """
        Sanitiza assignment_rules convirtiendo claves string a int

        Args:
            config: Configuracion raw cargada desde JSON

        Returns:
            dict: Configuracion con assignment_rules sanitizada
        """
        if 'assignment_rules' in config and config['assignment_rules']:
            sanitized_rules = {}
            for agent_type, rules in config['assignment_rules'].items():
                # BUGFIX: Verificar que rules es un diccionario antes de iterar
                if isinstance(rules, dict) and rules:
                    sanitized_rules[agent_type] = {int(k): v for k, v in rules.items()}
                else:
                    # Si rules es vacío o no es un diccionario, mantenerlo como está
                    sanitized_rules[agent_type] = rules
            config['assignment_rules'] = sanitized_rules
            print("[CONFIG] assignment_rules sanitizada (str -> int)")

        return config

    def _get_default_config(self) -> Dict:
        """
        Importa y retorna configuracion por defecto

        Returns:
            dict: Configuracion por defecto del sistema
        """
        try:
            # Importar get_default_config desde core.config_utils
            from core.config_utils import get_default_config
            return get_default_config()
        except ImportError as e:
            raise ConfigurationError(f"No se pudo importar configuracion por defecto: {e}")

    def _log_configuration_summary(self):
        """
        Log resumen de configuracion cargada usando mostrar_resumen_config
        """
        try:
            from core.config_utils import mostrar_resumen_config
            mostrar_resumen_config(self.configuration)
        except ImportError:
            print("[CONFIG] Aviso: No se pudo mostrar resumen (mostrar_resumen_config no disponible)")

    def validate_configuration(self) -> bool:
        """
        Valida que la configuracion contenga todas las claves esenciales

        Returns:
            bool: True si la configuracion es valida

        Raises:
            ConfigurationError: Si faltan claves esenciales
        """
        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if key not in self.configuration:
                missing_keys.append(key)

        if missing_keys:
            error_msg = f"Configuracion invalida. Claves faltantes: {missing_keys}"
            print(f"[CONFIG ERROR] {error_msg}")
            raise ConfigurationError(error_msg)

        print("[CONFIG] Validacion exitosa: Todas las claves esenciales presentes")
        return True

    def get_configuration(self) -> Dict:
        """
        Retorna configuracion cargada

        Returns:
            dict: Configuracion actual
        """
        return self.configuration

    def get_value(self, key: str, default_value=None):
        """
        Obtiene un valor especifico de la configuracion

        Args:
            key: Clave a buscar
            default_value: Valor por defecto si no existe la clave

        Returns:
            Valor de la configuracion o default_value
        """
        return self.configuration.get(key, default_value)

    def is_loaded(self) -> bool:
        """
        Verifica si la configuracion esta cargada

        Returns:
            bool: True si configuracion esta disponible
        """
        return self.configuration is not None and len(self.configuration) > 0

    def reload_configuration(self):
        """
        Recarga configuracion desde archivo
        """
        print("[CONFIG] Recargando configuracion...")
        self.configuration = self._load_configuration()
        self._log_configuration_summary()

    @staticmethod
    def load_configuration_static(config_path: Optional[str] = None) -> Dict:
        """
        Metodo estatico para carga rapida de configuracion sin instancia

        Args:
            config_path: Ruta al archivo de configuracion

        Returns:
            dict: Configuracion cargada
        """
        manager = ConfigurationManager(config_path)
        return manager.get_configuration()