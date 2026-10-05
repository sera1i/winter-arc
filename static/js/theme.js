/**
 * Winter Arc — Centralized Theme Controller
 * Manages Light / Dark theme state, persistence, DOM updates, and keyboard/mouse interactions.
 * Default theme: Light (as mandated by Winter Arc requirements).
 */
(function() {
    'use strict';

    var STORAGE_KEY = 'winter_arc_theme';
    var THEME_LIGHT = 'light';
    var THEME_DARK = 'dark';

    /**
     * Reads saved theme from localStorage, defaulting to 'light'.
     * Never automatically forces dark mode based on OS preference.
     */
    function getSavedTheme() {
        try {
            var saved = localStorage.getItem(STORAGE_KEY);
            if (saved === THEME_DARK || saved === THEME_LIGHT) {
                return saved;
            }
        } catch (e) {}
        return THEME_LIGHT;
    }

    /**
     * Applies theme to the document element and updates persistence & UI controls.
     */
    function applyTheme(theme) {
        if (theme !== THEME_DARK && theme !== THEME_LIGHT) {
            theme = THEME_LIGHT;
        }

        document.documentElement.setAttribute('data-theme', theme);

        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {}

        updateToggleButtons(theme);

        // Dispatch custom event for any listeners
        try {
            window.dispatchEvent(new CustomEvent('winter-arc-theme-change', { detail: { theme: theme } }));
        } catch (e) {}
    }

    /**
     * Toggles between light and dark themes.
     */
    function toggleTheme() {
        var current = document.documentElement.getAttribute('data-theme') || getSavedTheme();
        var next = (current === THEME_DARK) ? THEME_LIGHT : THEME_DARK;
        applyTheme(next);
    }

    /**
     * Updates visual state, icons, and accessible attributes on all toggle buttons in DOM.
     */
    function updateToggleButtons(theme) {
        var isDark = (theme === THEME_DARK);
        var buttons = document.querySelectorAll('.theme-toggle-btn');

        buttons.forEach(function(btn) {
            var iconLight = btn.querySelector('.theme-icon-light');
            var iconDark = btn.querySelector('.theme-icon-dark');

            if (iconLight) {
                iconLight.style.display = isDark ? 'none' : 'inline-flex';
                if (isDark) {
                    iconLight.classList.add('hidden');
                } else {
                    iconLight.classList.remove('hidden');
                }
            }
            if (iconDark) {
                iconDark.style.display = isDark ? 'inline-flex' : 'none';
                if (isDark) {
                    iconDark.classList.remove('hidden');
                } else {
                    iconDark.classList.add('hidden');
                }
            }

            if (isDark) {
                btn.setAttribute('aria-label', 'Current theme: Dark. Switch to Light theme');
                btn.setAttribute('title', 'Switch to Light theme');
            } else {
                btn.setAttribute('aria-label', 'Current theme: Light. Switch to Dark theme');
                btn.setAttribute('title', 'Switch to Dark theme');
            }
        });
    }

    function init() {
        var current = document.documentElement.getAttribute('data-theme') || getSavedTheme();
        // Ensure root has data-theme
        document.documentElement.setAttribute('data-theme', current);
        updateToggleButtons(current);

        // Event delegation for toggle buttons
        document.addEventListener('click', function(e) {
            var btn = e.target.closest('.theme-toggle-btn');
            if (btn) {
                e.preventDefault();
                toggleTheme();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose programmatic API on window for testing and external access
    window.WinterArcTheme = {
        getTheme: function() {
            return document.documentElement.getAttribute('data-theme') || getSavedTheme();
        },
        setTheme: applyTheme,
        toggle: toggleTheme,
        STORAGE_KEY: STORAGE_KEY
    };
})();
