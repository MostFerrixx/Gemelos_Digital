// ============================================
//  RIGHT DASHBOARD MODULE (Large Metrics Cards)
//  Separate file for dashboard functionality
// ============================================
const RightDashboardModule = {
    init() {
        console.log('[RightDashboardModule] Initializing...');

        // Subscribe to AppState changes
        if (typeof AppState !== 'undefined') {
            AppState.subscribe(state => this.update(state));
            console.log('[RightDashboardModule] Subscribed to AppState');
        } else {
            console.error('[RightDashboardModule] AppState not found! Ensure app.js loads first.');
        }

        console.log('[RightDashboardModule] Ready');
    },

    update(state) {
        if (!state.workOrders || state.workOrders.size === 0) return;

        const metrics = this.calculateMetrics(state.workOrders);

        this.setMetricValue('metric-total-lg', metrics.total);
        this.setMetricValue('metric-released-lg', metrics.released);
        this.setMetricValue('metric-assigned-lg', metrics.assigned);
        this.setMetricValue('metric-in-progress-lg', metrics.in_progress);
        this.setMetricValue('metric-staged-lg', metrics.staged);
    },

    calculateMetrics(workOrders) {
        const metrics = {
            total: workOrders.size,
            released: 0,
            assigned: 0,
            in_progress: 0,
            staged: 0
        };

        for (const [_, wo] of workOrders) {
            const status = wo.status || 'released';
            if (metrics.hasOwnProperty(status)) {
                metrics[status]++;
            }
        }

        return metrics;
    },

    setMetricValue(elementId, value) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = value;
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('[right-dashboard.js] DOM ready, initializing module...');
    RightDashboardModule.init();
});
