// Theme.qml - Centralized theme configuration for plugin configuration UI
// Reuses the same theme pattern as chat/Theme.qml for consistency

pragma Singleton
import QtQuick 2.15

QtObject {
    // Current theme: "dark" or "light"
    property string currentTheme: "dark"

    // ─────────────────────────────────────────────────────────────
    // Dark Theme (default)
    // ─────────────────────────────────────────────────────────────

    readonly property var darkTheme: {
        // Background colors
        backgroundColor: "#1e1e1e",
        cardBackground: "#2d2d2d",
        inputBackground: "#1e1e1e",

        // Text colors
        textPrimary: "#e0e0e0",
        textSecondary: "#b0b0b0",
        textTertiary: "#808080",
        textLabel: "#cccccc",

        // Border colors
        border: "#3a3a3a",
        borderFocus: "#3498db",
        borderError: "#ff6b6b",

        // Accent colors
        accent: "#3498db",
        accentHover: "#5ba0f2",

        // Status colors
        statusSuccess: "#51cf66",
        statusWarning: "#ffd43b",
        statusError: "#ff6b6b",
        statusInfo: "#4a90e2",
    }

    // ─────────────────────────────────────────────────────────────
    // Light Theme
    // ─────────────────────────────────────────────────────────────

    readonly property var lightTheme: {
        // Background colors
        backgroundColor: "#f5f5f5",
        cardBackground: "#ffffff",
        inputBackground: "#ffffff",

        // Text colors
        textPrimary: "#202020",
        textSecondary: "#505050",
        textTertiary: "#808080",
        textLabel: "#404040",

        // Border colors
        border: "#e0e0e0",
        borderFocus: "#3498db",
        borderError: "#fa5252",

        // Accent colors
        accent: "#3498db",
        accentHover: "#2980b9",

        // Status colors
        statusSuccess: "#37b24d",
        statusWarning: "#fcc419",
        statusError: "#fa5252",
        statusInfo: "#339af0",
    }

    // ─────────────────────────────────────────────────────────────
    // Current Theme Colors (computed)
    // ─────────────────────────────────────────────────────────────

    readonly property var colors: currentTheme === "dark" ? darkTheme : lightTheme

    // Convenience accessors
    readonly property color backgroundColor: colors.backgroundColor
    readonly property color cardBackground: colors.cardBackground
    readonly property color inputBackground: colors.inputBackground
    readonly property color textPrimary: colors.textPrimary
    readonly property color textSecondary: colors.textSecondary
    readonly property color textTertiary: colors.textTertiary
    readonly property color textLabel: colors.textLabel
    readonly property color border: colors.border
    readonly property color borderFocus: colors.borderFocus
    readonly property color borderError: colors.borderError
    readonly property color accent: colors.accent
    readonly property color accentHover: colors.accentHover
    readonly property color statusSuccess: colors.statusSuccess
    readonly property color statusWarning: colors.statusWarning
    readonly property color statusError: colors.statusError
    readonly property color statusInfo: colors.statusInfo

    // Function to switch theme
    function setTheme(theme) {
        if (theme === "dark" || theme === "light") {
            currentTheme = theme
        }
    }

    // Function to toggle theme
    function toggleTheme() {
        currentTheme = currentTheme === "dark" ? "light" : "dark"
    }
}