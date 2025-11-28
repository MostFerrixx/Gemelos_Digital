/**
 * Configuration Storage
 * Handles saving, loading, and managing configuration presets
 */

class ConfigurationStorage {
    constructor(configurator) {
        this.configurator = configurator;
        this.initModals();
    }

    initModals() {
        // Setup modal close buttons
        const closeButtons = document.querySelectorAll('.modal-close');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Close modal on overlay click
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Setup save configuration confirm button
        const saveConfirmBtn = document.getElementById('btn-save-config-confirm');
        if (saveConfirmBtn) {
            saveConfirmBtn.addEventListener('click', () => this.saveConfigurationConfirm());
        }
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    async saveAs() {
        // Reset form
        document.getElementById('config-name').value = '';
        document.getElementById('config-description').value = '';
        document.getElementById('config-is-default').checked = false;

        // Open modal
        this.openModal('modal-save');
    }

    async saveConfigurationConfirm() {
        const name = document.getElementById('config-name').value.trim();
        const description = document.getElementById('config-description').value.trim();
        const isDefault = document.getElementById('config-is-default').checked;

        if (!name) {
            this.configurator.showNotification('Por favor ingrese un nombre para la configuración', 'error');
            return;
        }

        try {
            // Get current configuration from form
            const config = this.configurator.serializeConfig();

            this.configurator.showLoading('Guardando configuración...');

            const response = await fetch('/api/configurator/configurations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    description: description,
                    config: config,
                    is_default: isDefault
                })
            });

            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.configurator.showNotification(result.message, 'success');
                this.closeModal('modal-save');
            } else {
                this.configurator.showNotification('Error: ' + (result.errors || ['Error desconocido']).join(', '), 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error saving configuration:', error);
            this.configurator.showNotification('Error saving configuration: ' + error.message, 'error');
        }
    }

    async loadFrom() {
        try {
            this.configurator.showLoading('Cargando configuraciones...');

            const response = await fetch('/api/configurator/configurations');
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.displayConfigurationsList(result.configurations, 'configs-list', true);
                this.openModal('modal-load');
            } else {
                this.configurator.showNotification('Error loading configurations', 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error loading configurations:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    async manage() {
        try {
            this.configurator.showLoading('Cargando configuraciones...');

            const response = await fetch('/api/configurator/configurations');
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.displayConfigurationsList(result.configurations, 'manage-configs-list', false);
                this.openModal('modal-manage');
            } else {
                this.configurator.showNotification('Error loading configurations', 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error loading configurations:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    displayConfigurationsList(configurations, containerId, isLoadMode) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';

        if (configurations.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: var(--color-text-secondary);">No hay configuraciones guardadas</p>';
            return;
        }

        configurations.forEach(config => {
            const item = document.createElement('div');
            item.className = 'config-item';

            const date = new Date(config.created_at).toLocaleString('es-ES');

            item.innerHTML = `
                <div class="config-item-info">
                    <div class="config-item-name">${config.name}</div>
                    ${config.description ? `<div class="config-item-description">${config.description}</div>` : ''}
                    <div class="config-item-meta">Creado: ${date}</div>
                    ${config.is_default ? '<span class="config-item-badge">DEFAULT</span>' : ''}
                </div>
                <div class="config-item-actions">
                    ${isLoadMode ? `
                        <button class="btn-primary" onclick="configStorage.loadConfiguration('${config.id}')">Cargar</button>
                    ` : `
                        <button class="btn-secondary" onclick="configStorage.setDefault('${config.id}')">Set Default</button>
                        <button class="btn-danger btn-remove-group" onclick="configStorage.deleteConfiguration('${config.id}')">Eliminar</button>
                    `}
                </div>
            `;

            container.appendChild(item);
        });
    }

    async loadConfiguration(configId) {
        try {
            this.configurator.showLoading('Cargando configuración...');

            const response = await fetch(`/api/configurator/configurations/${configId}`);
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                // Load configuration into form
                this.configurator.loadConfigToForm(result.config);
                this.configurator.showNotification('Configuración cargada exitosamente', 'success');
                this.closeModal('modal-load');
            } else {
                this.configurator.showNotification('Error loading configuration', 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error loading configuration:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    async deleteConfiguration(configId) {
        if (!confirm('¿Está seguro de que desea eliminar esta configuración?')) {
            return;
        }

        try {
            this.configurator.showLoading('Eliminando configuración...');

            const response = await fetch(`/api/configurator/configurations/${configId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.configurator.showNotification(result.message, 'success');
                // Refresh the list
                this.manage();
            } else {
                this.configurator.showNotification('Error: ' + (result.errors || ['Error desconocido']).join(', '), 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error deleting configuration:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    async setDefault(configId) {
        try {
            this.configurator.showLoading('Estableciendo configuración por defecto...');

            const response = await fetch(`/api/configurator/configurations/${configId}/set-default`, {
                method: 'PUT'
            });
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.configurator.showNotification(result.message, 'success');
                // Refresh the list
                this.manage();
            } else {
                this.configurator.showNotification('Error: ' + (result.errors || ['Error desconocido']).join(', '), 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error setting default:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    async loadDefault() {
        try {
            this.configurator.showLoading('Cargando configuración por defecto...');

            const response = await fetch('/api/configurator/default');
            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                // Load configuration into form
                this.configurator.loadConfigToForm(result.config);
                this.configurator.showNotification('Configuración por defecto cargada', 'success');
            } else {
                this.configurator.showNotification('Error loading default configuration', 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error loading default:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }

    async useConfiguration() {
        // Apply current form configuration to config.json
        if (!confirm('¿Desea aplicar esta configuración a config.json? El simulador usará esta configuración en la próxima ejecución.')) {
            return;
        }

        try {
            // Get current configuration from form
            const config = this.configurator.serializeConfig();

            this.configurator.showLoading('Aplicando configuración...');

            const response = await fetch('/api/configurator/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ config: config })
            });

            const result = await response.json();

            this.configurator.hideLoading();

            if (result.success) {
                this.configurator.showNotification('✓ Configuración aplicada a config.json exitosamente', 'success');
            } else {
                this.configurator.showNotification('Error: ' + (result.errors || ['Error desconocido']).join(', '), 'error');
            }
        } catch (error) {
            this.configurator.hideLoading();
            console.error('[CONFIG_STORAGE] Error applying configuration:', error);
            this.configurator.showNotification('Error: ' + error.message, 'error');
        }
    }
}

// Global instance will be created by app.js
let configStorage = null;
