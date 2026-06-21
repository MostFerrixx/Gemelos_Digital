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

        // C (BK-04): recalcular la cobertura de areas ante CUALQUIER cambio de la flota
        // (agregar/quitar grupo, agregar/quitar prioridad, cambiar el area de un select).
        // MutationObserver = cambios estructurales; change delegado = cambio de valor de
        // un work-area-select. Asi C no depende de hookear cada metodo individual.
        ['ground-operators-container', 'forklifts-container'].forEach((id) => {
            const cont = document.getElementById(id);
            if (!cont) return;
            cont.addEventListener('change', (e) => {
                if (e.target && e.target.classList && e.target.classList.contains('work-area-select')) {
                    this.updateAreaCoverage();
                }
            });
            const mo = new MutationObserver(() => this.updateAreaCoverage());
            mo.observe(cont, { childList: true, subtree: true });
        });
    }

    setWorkAreas(workAreas) {
        this.workAreas = workAreas;
        console.log('[FLEET_MANAGER] Work areas updated:', this.workAreas);

        // Update all existing dropdowns
        this.updateAllWorkAreaDropdowns();
        this.updateAreaCoverage();
    }

    // QA-3 (BK-04): tipo capaz de un area por CONVENCION DE NOMBRES (el dato no lo codifica).
    // Debe coincidir con config_manager._expected_equipment_for_area y event_generator.
    _expectedEquipmentForArea(area) {
        return /ground|piso|floor|suelo|terrestre|level[_-]?0|l0/i.test(String(area))
            ? 'GroundOperator' : 'Forklift';
    }

    // C (BK-04 hardening): pinta el panel de cobertura.
    //  verde  = area cubierta por un agente del TIPO correcto.
    //  naranja= cubierta solo por el tipo INCORRECTO (QA-3).
    //  rojo   = sin agente (QA-1).  Flota vacia (0 grupos) => rojo: no hay agentes (QA-2).
    // Devuelve la lista de areas problematicas (sin cubrir o con tipo incorrecto).
    updateAreaCoverage() {
        const panel = document.getElementById('area-coverage-panel');
        const areas = this.workAreas || [];
        const groups = document.querySelectorAll('.fleet-group');

        // area -> conjunto de tipos de agente que la cubren (segun el grupo del select)
        const coveringTypes = {};
        groups.forEach((g) => {
            const type = g.getAttribute('data-agent-type');
            g.querySelectorAll('.work-area-select').forEach((s) => {
                if (s.value) (coveringTypes[s.value] = coveringTypes[s.value] || new Set()).add(type);
            });
        });

        let html, problems = [];
        if (!areas.length) {
            html = '<span class="coverage-label">Cobertura de areas:</span> '
                + '<span class="coverage-warn">sin areas cargadas</span>';
        } else if (groups.length === 0) {
            // QA-2: flota vacia = 0 agentes => invalido (ya NO se asume el fallback).
            problems = areas.slice();
            html = '<span class="coverage-label">Cobertura de areas:</span> '
                + '<span class="coverage-warn">⚠ Flota vacia: no hay agentes — no se podra '
                + 'guardar/correr. Genera o agrega una flota.</span>';
        } else {
            let nUnc = 0, nWrong = 0;
            const chips = areas.map((a) => {
                const types = coveringTypes[a];
                const exp = this._expectedEquipmentForArea(a);
                if (!types || types.size === 0) {
                    problems.push(a); nUnc++;
                    return '<span class="coverage-chip uncovered">✗ ' + a + '</span>';
                }
                if (!types.has(exp)) {
                    problems.push(a); nWrong++;
                    return '<span class="coverage-chip wrongtype" title="Requiere ' + exp
                        + '">⚠ ' + a + '</span>';
                }
                return '<span class="coverage-chip covered">✓ ' + a + '</span>';
            }).join(' ');
            let summary;
            if (!problems.length) {
                summary = '<span class="coverage-ok">✓ Todas las areas cubiertas</span>';
            } else {
                const parts = [];
                if (nUnc) parts.push(nUnc + ' sin agente');
                if (nWrong) parts.push(nWrong + ' con tipo incorrecto');
                summary = '<span class="coverage-warn">⚠ ' + parts.join(' y ')
                    + ' — no se podra guardar/correr</span>';
            }
            html = '<span class="coverage-label">Cobertura de areas:</span> ' + chips + ' ' + summary;
        }
        if (panel) panel.innerHTML = html;
        return problems;
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

        // D-10: Validacion inline — work area select
        const waSelect = priorityRow.querySelector('.work-area-select');
        waSelect.addEventListener('change', () => {
            const errEl = priorityRow.querySelector('.wa-error');
            if (!waSelect.value) {
                waSelect.classList.add('input-field-error');
                if (!errEl) {
                    const e = document.createElement('span');
                    e.className = 'input-inline-error wa-error';
                    e.textContent = 'Selecciona un Work Area';
                    waSelect.insertAdjacentElement('afterend', e);
                }
            } else {
                waSelect.classList.remove('input-field-error');
                if (errEl) errEl.remove();
            }
        });

        // D-10: Validacion inline — prioridad (1-10)
        const priInput = priorityRow.querySelector('.input-priority');
        priInput.addEventListener('input', () => {
            const val = parseInt(priInput.value);
            const errEl = priorityRow.querySelector('.pri-error');
            if (isNaN(val) || val < 1 || val > 10) {
                priInput.classList.add('input-field-error');
                if (!errEl) {
                    const e = document.createElement('span');
                    e.className = 'input-inline-error pri-error';
                    e.textContent = 'Valor entre 1 y 10';
                    priInput.insertAdjacentElement('afterend', e);
                }
            } else {
                priInput.classList.remove('input-field-error');
                if (errEl) errEl.remove();
            }
        });

        prioritiesList.appendChild(priorityRow);
    }

    generateDefaultFleet() {
        const modal = document.getElementById('modal-confirm-fleet');
        if (!modal) {
            // Fallback: modal not found, execute directly
            this._executeDefaultFleet();
            return;
        }

        modal.classList.remove('hidden');

        const okBtn = document.getElementById('btn-confirm-fleet-ok');
        const cancelBtn = document.getElementById('btn-confirm-fleet-cancel');

        const cleanup = () => {
            modal.classList.add('hidden');
            okBtn.removeEventListener('click', onOk);
            cancelBtn.removeEventListener('click', onCancel);
        };

        const onOk = () => { cleanup(); this._executeDefaultFleet(); };
        const onCancel = () => { cleanup(); };

        okBtn.addEventListener('click', onOk);
        cancelBtn.addEventListener('click', onCancel);
    }

    _executeDefaultFleet() {
        // Clear existing fleet
        this.clearAllGroups();

        // Fix 1 (BK-04): repartir las areas REALES del layout (this.workAreas), no
        // nombres hardcodeados. Heuristica: areas "de piso" -> GroundOperator; el resto
        // (racks altos / especiales) -> Forklift. Cada area cae en exactamente un grupo,
        // asi la flota por defecto cubre TODAS por construccion (valida sola).
        const areas = (this.workAreas || []).slice();
        const isGround = (a) => /ground|piso|floor|suelo|terrestre|level[_-]?0|l0/i.test(a);
        const groundAreas = areas.filter(isGround);
        const forkAreas = areas.filter(a => !isGround(a));

        if (!areas.length) {
            this.configurator.showNotification(
                'No hay areas de trabajo cargadas. Carga el layout/Excel antes de generar la flota.',
                'warning');
        }

        // Operarios terrestres: cubren las areas de piso (todas, si no hay de forklift)
        this.addGroup('GroundOperator');
        this.addDefaultPriorities('GroundOperator', 0, groundAreas);

        // Montacargas: cubren el resto (racks / especiales)
        this.addGroup('Forklift');
        this.addDefaultPriorities('Forklift', 0, forkAreas);

        this.updateAreaCoverage();
        this.configurator.showNotification(
            'Flota por defecto generada (cubre todas las areas del layout)', 'success');
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
