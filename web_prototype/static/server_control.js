// ========================================================================
// SHARED SERVER CONTROL MODULE
// Handles server restart functionality for both Configurator and Simulator
// ========================================================================

(function () {
    /**
     * Initialize the restart server button and overlay functionality
     */
    function initServerControl() {
        // Check if already initialized
        if (document.getElementById('restartServerBtn')) return;

        console.log('[ServerControl] Initializing...');

        // Determine where to inject the button
        let targetContainer = null;
        let insertBefore = false;

        // Priority 1: Configurator (.config-actions)
        const configActions = document.querySelector('.config-actions');
        if (configActions) {
            targetContainer = configActions;
            insertBefore = true; // Insert at beginning
        }
        // Priority 2: Simulator (.controls-left)
        else {
            const simControls = document.querySelector('.controls-left');
            if (simControls) {
                targetContainer = simControls;
                insertBefore = false; // Append to end
            }
        }

        if (!targetContainer) {
            console.warn('[ServerControl] No suitable container found for restart button');
            // Fallback: Create a floating container? For now, just log warning.
            return;
        }

        // Create restart button
        const restartBtn = document.createElement('button');
        restartBtn.id = 'restartServerBtn';
        restartBtn.className = 'restart-server-btn';
        restartBtn.title = 'Reiniciar Servidor';
        restartBtn.innerHTML = '<span class="restart-icon">\u21BB</span> Restart';

        // Inject button
        if (insertBefore) {
            // For configurator, we also want a divider
            const divider = document.createElement('div');
            divider.className = 'divider';
            targetContainer.insertBefore(divider, targetContainer.firstChild);
            targetContainer.insertBefore(restartBtn, targetContainer.firstChild);
        } else {
            targetContainer.appendChild(restartBtn);
        }

        // Create restart overlay
        const overlay = document.createElement('div');
        overlay.id = 'restartOverlay';
        overlay.className = 'restart-overlay';
        overlay.style.display = 'none';
        overlay.innerHTML = `
            <div class="restart-content">
                <div class="restart-spinner"></div>
                <h2>Reiniciando Sistema...</h2>
                <p>Por favor espere. La p\u00e1gina se recargar\u00e1 autom\u00e1ticamente.</p>
                <div class="restart-progress">
                    <div class="restart-progress-bar"></div>
                </div>
                <p class="restart-status" id="restartStatus">Enviando comando de reinicio...</p>
            </div>
        `;
        document.body.appendChild(overlay);

        const statusEl = document.getElementById('restartStatus');

        // Add click event listener
        restartBtn.addEventListener('click', async () => {
            // Confirm with the user
            const confirmed = confirm(
                '\u00bfEst\u00e1s seguro de que deseas reiniciar el servidor?\n\n' +
                'Esto interrumpir\u00e1 cualquier operaci\u00f3n en curso y recargar\u00e1 la p\u00e1gina.'
            );

            if (!confirmed) return;

            // Show overlay
            overlay.style.display = 'flex';
            updateStatus('Enviando comando de reinicio...');

            try {
                // 1. Call restart endpoint
                const response = await fetch('/api/system/restart', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error('Failed to trigger restart');
                }

                const data = await response.json();
                updateStatus('Servidor reiniciando...');

                // 2. Wait estimated time
                await sleep(data.estimated_time * 1000 || 3000);

                // 3. Poll health check
                updateStatus('Esperando que el servidor vuelva...');
                await waitForServerReady();

                // 4. Reload page
                updateStatus('Servidor listo. Recargando p\u00e1gina...');
                await sleep(500);
                window.location.reload();

            } catch (error) {
                console.error('Restart error:', error);
                updateStatus('Error al reiniciar. Recargando p\u00e1gina de todos modos...');
                await sleep(2000);
                window.location.reload();
            }
        });

        function updateStatus(message) {
            if (statusEl) statusEl.textContent = message;
        }

        function sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        async function waitForServerReady() {
            const maxAttempts = 20;  // 20 attempts
            const delayMs = 500;      // 500ms between attempts = 10 seconds max

            for (let i = 0; i < maxAttempts; i++) {
                try {
                    const response = await fetch('/api/system/health', {
                        method: 'GET',
                        cache: 'no-cache'
                    });

                    if (response.ok) {
                        updateStatus('Servidor respondiendo correctamente');
                        return true;
                    }
                } catch (error) {
                    // Server not ready yet
                    updateStatus(`Esperando respuesta del servidor (intento ${i + 1}/${maxAttempts})...`);
                }

                await sleep(delayMs);
            }

            throw new Error('Server did not respond after restart');
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initServerControl);
    } else {
        // DOM already loaded
        initServerControl();
    }

})();
