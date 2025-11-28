/**
 * Theme Manager
 * Handles light/dark theme switching with persistent storage
 */

class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('configurator-theme') || 'light';
        this.toggleButton = null;
        this.init();
    }

    init() {
        // Apply saved theme on load
        this.apply();

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupToggleButton());
        } else {
            this.setupToggleButton();
        }
    }

    setupToggleButton() {
        this.toggleButton = document.getElementById('theme-toggle');

        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => this.toggle());
            this.updateToggleButton();
        }
    }

    toggle() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.apply();
        this.save();
    }

    apply() {
        document.documentElement.setAttribute('data-theme', this.currentTheme);
        this.updateToggleButton();
    }

    save() {
        localStorage.setItem('configurator-theme', this.currentTheme);
    }

    updateToggleButton() {
        if (!this.toggleButton) return;

        const icon = this.currentTheme === 'light' ? '🌙' : '☀️';
        this.toggleButton.textContent = icon;
        this.toggleButton.title = this.currentTheme === 'light'
            ? 'Cambiar a tema oscuro'
            : 'Cambiar a tema claro';
    }
}

// Initialize theme manager on script load
const themeManager = new ThemeManager();
