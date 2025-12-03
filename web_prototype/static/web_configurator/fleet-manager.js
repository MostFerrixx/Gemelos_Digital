/**
 * Fleet Manager
 * Manages dynamic fleet groups (Operarios Terrestres and Montacargas)
 */

class FleetManager {
    constructor(configurator) {
        this.configurator = configurator;
        this.groups = {
            GroundOperator: [],
            Forklift: []
        };
        this.workAreas = [];
        this.init();
    }

    init() {
        // Setup "Add Group" buttons
        const addGroupButtons = document.querySelectorAll('.btn-add-group');
        addGroupButtons.forEach(btn => {
            const agentType = btn.dataset.agentType;
            btn.addEventListener('click', () => this.addGroup(agentType));
        });

        // Setup "Generate Default Fleet" button
        const generateDefaultBtn = document.getElementById('btn-generate-default-fleet');
        if (generateDefaultBtn) {
            generateDefaultBtn.addEventListener('click', () => this.generateDefaultFleet());
        }
    }

    setWorkAreas(workAreas) {
        this.workAreas = workAreas;
        console.log('[FLEET_MANAGER] Work areas updated:', this.workAreas);

        // Update all existing dropdowns
        this.updateAllWorkAreaDropdowns();
    }

    updateAllWorkAreaDropdowns() {
        // Update all work area select elements
        const selects = document.querySelectorAll('.work-area-select');
        selects.forEach(select => {
            const currentValue = select.value;
            select.innerHTML = '';

            // Add empty option
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '-- Seleccionar --';
            select.appendChild(emptyOption);

            // Add work area options
            this.workAreas.forEach(wa => {
                const option = document.createElement('option');
                option.value = wa;
                option.textContent = wa;
                select.appendChild(option);
            });

            // Restore previous value if still valid
            if (currentValue && this.workAreas.includes(currentValue)) {
                select.value = currentValue;
            }
        });
    }

    addGroup(agentType) {
        const container = agentType === 'GroundOperator'
            ? document.getElementById('ground-operators-container')
            : document.getElementById('forklifts-container');

        if (!container) return;

        const groupIndex = this.groups[agentType].length;
        const defaultCapacity = agentType === 'GroundOperator' ? 150 : 1000;

        // Create group data
        const groupData = {
            index: groupIndex,
            agentType: agentType,
            cantidad: 2,
            capacidad: defaultCapacity,
            tiempoDescarga: 5,
            priorities: []
        };

        this.groups[agentType].push(groupData);

        // Create group element
        const groupElement = this.createGroupElement(groupData);
        container.appendChild(groupElement);
    }

    createGroupElement(groupData) {
        const div = document.createElement('div');
        div.className = 'fleet-group';
        div.dataset.agentType = groupData.agentType;
        div.dataset.index = groupData.index;

        div.innerHTML = `
            <div class="fleet-group-header">
                <div class="fleet-group-title">Grupo ${groupData.index + 1}</div>
                <button class="btn-remove-group" data-agent-type="${groupData.agentType}" data-index="${groupData.index}">
                    ✕ Eliminar
                </button>
            </div>
            
            <div class="fleet-group-params">
                <div class="fleet-param">
                    <label>Cantidad:</label>
                    <input type="number" class="input-cantidad" value="${groupData.cantidad}" min="1" max="50">
                </div>
                <div class="fleet-param">
                    <label>Capacidad (L):</label>
                    <input type="number" class="input-capacidad" value="${groupData.capacidad}" min="50" max="2000">
                </div>
                <div class="fleet-param">
                    <label>Tiempo Descarga (s):</label>
                    <input type="number" class="input-tiempo-descarga" value="${groupData.tiempoDescarga}" min="1" max="60">
                </div>
            </div>

            <div class="work-area-priorities-section">
                <div class="work-area-priorities-header">
                    <div class="work-area-priorities-title">Prioridades de Work Area</div>
                    <button class="btn-add-priority">+ Añadir</button>
                </div>
                <div class="work-area-priorities-list"></div>
            </div>
        `;

        // Setup event listeners
        const removeBtn = div.querySelector('.btn-remove-group');
        removeBtn.addEventListener('click', () => {
            this.removeGroup(groupData.agentType, groupData.index);
        });

        const addPriorityBtn = div.querySelector('.btn-add-priority');
        addPriorityBtn.addEventListener('click', () => {
            this.addWorkAreaPriority(groupData.agentType, groupData.index);
        });

        return div;
    }

    removeGroup(agentType, groupIndex) {
        // Find and remove the group element
        const container = agentType === 'GroundOperator'
            ? document.getElementById('ground-operators-container')
            : document.getElementById('forklifts-container');

        const groupElement = container.querySelector(`[data-agent-type="${agentType}"][data-index="${groupIndex}"]`);
        if (groupElement) {
            groupElement.remove();
        }

        // Remove from data
        this.groups[agentType] = this.groups[agentType].filter(g => g.index !== groupIndex);

        // Renumber remaining groups
        this.renumberGroups(agentType);
    }

    renumberGroups(agentType) {
        const container = agentType === 'GroundOperator'
            ? document.getElementById('ground-operators-container')
            : document.getElementById('forklifts-container');

        const groupElements = container.querySelectorAll('.fleet-group');
        groupElements.forEach((el, newIndex) => {
            el.dataset.index = newIndex;
            el.querySelector('.fleet-group-title').textContent = `Grupo ${newIndex + 1}`;
            el.querySelector('.btn-remove-group').dataset.index = newIndex;

            // Update group data
            if (this.groups[agentType][newIndex]) {
                this.groups[agentType][newIndex].index = newIndex;
            }
        });
    }

    addWorkAreaPriority(agentType, groupIndex) {
        const container = agentType === 'GroundOperator'
            ? document.getElementById('ground-operators-container')
            : document.getElementById('forklifts-container');

        const groupElement = container.querySelector(`[data-agent-type="${agentType}"][data-index="${groupIndex}"]`);
        if (!groupElement) return;

        const prioritiesList = groupElement.querySelector('.work-area-priorities-list');

        const priorityRow = document.createElement('div');
        priorityRow.className = 'work-area-priority-row';
        priorityRow.innerHTML = `
            <label>Work Area:</label>
            <select class="work-area-select">
                <option value="">-- Seleccionar --</option>
                ${this.workAreas.map(wa => `<option value="${wa}">${wa}</option>`).join('')}
            </select>
            <label>Prioridad:</label>
            <input type="number" class="input-priority" value="1" min="1" max="10">
            <button class="btn-remove-priority">✕</button>
        `;

        const removeBtn = priorityRow.querySelector('.btn-remove-priority');
        removeBtn.addEventListener('click', () => {
            priorityRow.remove();
        });

        prioritiesList.appendChild(priorityRow);
    }

    generateDefaultFleet() {
        if (!confirm('¿Desea generar la configuración de flota por defecto? Esto reemplazará la configuración actual.')) {
            return;
        }

        // Clear existing fleet
        this.clearAllGroups();

        // Add default GroundOperator group
        this.addGroup('GroundOperator');
        this.addDefaultPriorities('GroundOperator', 0, ['Area_Ground', 'Area_Piso_L1']);

        // Add default Forklift group
        this.addGroup('Forklift');
        this.addDefaultPriorities('Forklift', 0, ['Area_Rack']);

        this.configurator.showNotification('Flota por defecto generada exitosamente', 'success');
    }

    addDefaultPriorities(agentType, groupIndex, workAreas) {
        const container = agentType === 'GroundOperator'
            ? document.getElementById('ground-operators-container')
            : document.getElementById('forklifts-container');

        const groupElement = container.querySelector(`[data-agent-type="${agentType}"][data-index="${groupIndex}"]`);
        if (!groupElement) return;

        workAreas.forEach(wa => {
            // Add a priority row
            this.addWorkAreaPriority(agentType, groupIndex);

            // Find the last added row and set its value
            const prioritiesList = groupElement.querySelector('.work-area-priorities-list');
            const rows = prioritiesList.querySelectorAll('.work-area-priority-row');
            const lastRow = rows[rows.length - 1];

            if (lastRow) {
                const select = lastRow.querySelector('.work-area-select');
                select.value = wa;
            }
        });
    }

    clearAllGroups() {
        // Clear GroundOperator groups
        const groundContainer = document.getElementById('ground-operators-container');
        if (groundContainer) {
            groundContainer.innerHTML = '';
        }
        this.groups.GroundOperator = [];

        // Clear Forklift groups
        const forkliftContainer = document.getElementById('forklifts-container');
        if (forkliftContainer) {
            forkliftContainer.innerHTML = '';
        }
        this.groups.Forklift = [];
    }

    serializeFleet() {
        // Serialize fleet groups to agent_types array
        const agentTypes = [];

        // Process GroundOperator groups
        const groundContainer = document.getElementById('ground-operators-container');
        if (groundContainer) {
            const groups = groundContainer.querySelectorAll('.fleet-group');
            groups.forEach(group => {
                const cantidad = parseInt(group.querySelector('.input-cantidad').value);
                const capacidad = parseInt(group.querySelector('.input-capacidad').value);
                const tiempoDescarga = parseInt(group.querySelector('.input-tiempo-descarga').value);

                // Get work area priorities
                const workAreaPriorities = {};
                const priorityRows = group.querySelectorAll('.work-area-priority-row');
                priorityRows.forEach(row => {
                    const wa = row.querySelector('.work-area-select').value;
                    const priority = parseInt(row.querySelector('.input-priority').value);
                    if (wa) {
                        workAreaPriorities[wa] = priority;
                    }
                });

                // Create agent entries (one per cantidad)
                for (let i = 0; i < cantidad; i++) {
                    agentTypes.push({
                        type: 'GroundOperator',
                        capacity: capacidad,
                        discharge_time: tiempoDescarga,
                        work_area_priorities: workAreaPriorities
                    });
                }
            });
        }

        // Process Forklift groups
        const forkliftContainer = document.getElementById('forklifts-container');
        if (forkliftContainer) {
            const groups = forkliftContainer.querySelectorAll('.fleet-group');
            groups.forEach(group => {
                const cantidad = parseInt(group.querySelector('.input-cantidad').value);
                const capacidad = parseInt(group.querySelector('.input-capacidad').value);
                const tiempoDescarga = parseInt(group.querySelector('.input-tiempo-descarga').value);

                // Get work area priorities
                const workAreaPriorities = {};
                const priorityRows = group.querySelectorAll('.work-area-priority-row');
                priorityRows.forEach(row => {
                    const wa = row.querySelector('.work-area-select').value;
                    const priority = parseInt(row.querySelector('.input-priority').value);
                    if (wa) {
                        workAreaPriorities[wa] = priority;
                    }
                });

                // Create agent entries (one per cantidad)
                for (let i = 0; i < cantidad; i++) {
                    agentTypes.push({
                        type: 'Forklift',
                        capacity: capacidad,
                        discharge_time: tiempoDescarga,
                        work_area_priorities: workAreaPriorities
                    });
                }
            });
        }

        return agentTypes;
    }

    loadFleet(agentTypes) {
        // Clear existing fleet
        this.clearAllGroups();

        console.log(`[FLEET_MANAGER] Loading fleet with ${agentTypes.length} agents`);
        console.log('[FLEET_MANAGER] Available work areas:', this.workAreas);

        // Group agents by type and config
        const grouped = {};

        agentTypes.forEach(agent => {
            const key = `${agent.type}_${agent.capacity}_${agent.discharge_time}_${JSON.stringify(agent.work_area_priorities || {})}`;

            if (!grouped[key]) {
                grouped[key] = {
                    type: agent.type,
                    capacity: agent.capacity,
                    discharge_time: agent.discharge_time,
                    work_area_priorities: agent.work_area_priorities || {},
                    count: 0
                };
            }
            grouped[key].count++;
        });

        // Create groups
        Object.values(grouped).forEach(group => {
            const agentType = group.type;
            this.addGroup(agentType);

            // Get the last added group
            const container = agentType === 'GroundOperator'
                ? document.getElementById('ground-operators-container')
                : document.getElementById('forklifts-container');

            const groupElements = container.querySelectorAll('.fleet-group');
            const lastGroup = groupElements[groupElements.length - 1];

            if (lastGroup) {
                // Set values
                lastGroup.querySelector('.input-cantidad').value = group.count;
                lastGroup.querySelector('.input-capacidad').value = group.capacity;
                lastGroup.querySelector('.input-tiempo-descarga').value = group.discharge_time;

                // Add work area priorities
                Object.entries(group.work_area_priorities).forEach(([wa, priority]) => {
                    const groupIndex = parseInt(lastGroup.dataset.index);
                    this.addWorkAreaPriority(agentType, groupIndex);

                    // Get the last added priority row
                    const prioritiesList = lastGroup.querySelector('.work-area-priorities-list');
                    const rows = prioritiesList.querySelectorAll('.work-area-priority-row');
                    const lastRow = rows[rows.length - 1];

                    if (lastRow) {
                        const waSelect = lastRow.querySelector('.work-area-select');

                        // Check if WA exists in available work areas
                        if (this.workAreas.includes(wa)) {
                            waSelect.value = wa;
                            lastRow.querySelector('.input-priority').value = priority;
                        } else {
                            console.warn(`[FLEET_MANAGER] Work Area "${wa}" not found in available work areas. Current WAs:`, this.workAreas);
                            // Still set the value - it will show in the dropdown even if not in the list
                            waSelect.value = wa;
                            lastRow.querySelector('.input-priority').value = priority;
                        }
                    }
                });
            }
        });

        console.log('[FLEET_MANAGER] Fleet loading complete');
    }
}
