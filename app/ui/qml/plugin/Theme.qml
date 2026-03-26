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

    // Background colors
    readonly property color backgroundColor: currentTheme === "dark" ? darkTheme.backgroundColor : lightTheme.backgroundColor
    readonly property color cardBackground: currentTheme === "dark" ? darkTheme.cardBackground : lightTheme.cardBackground
    readonly property color inputBackground: currentTheme === "dark" ? darkTheme.inputBackground : lightTheme.inputBackground

    // Text colors
    readonly property color textPrimary: currentTheme === "dark" ? darkTheme.textPrimary : lightTheme.textPrimary
    readonly property color textSecondary: currentTheme === "dark" ? darkTheme.textSecondary : lightTheme.textSecondary
    readonly property color textTertiary: currentTheme === "dark" ? darkTheme.textTertiary : lightTheme.textTertiary
    readonly property color textLabel: currentTheme === "dark" ? darkTheme.textLabel : lightTheme.textLabel

    // Border colors
    readonly property color border: currentTheme === "dark" ? darkTheme.border : lightTheme.border
    readonly property color borderFocus: currentTheme === "dark" ? darkTheme.borderFocus : lightTheme.borderFocus
    readonly property color borderError: currentTheme === "dark" ? darkTheme.borderError : lightTheme.borderError

    // Accent colors
    readonly property color accent: currentTheme === "dark" ? darkTheme.accent : lightTheme.accent
    readonly property color accentHover: currentTheme === "dark" ? darkTheme.accentHover : lightTheme.accentHover

    // Status colors
    readonly property color statusSuccess: currentTheme === "dark" ? darkTheme.statusSuccess : lightTheme.statusSuccess
    readonly property color statusWarning: currentTheme === "dark" ? darkTheme.statusWarning : lightTheme.statusWarning
    readonly property color statusError: currentTheme === "dark" ? darkTheme.statusError : lightTheme.statusError
    readonly property color statusInfo: currentTheme === "dark" ? darkTheme.statusInfo : lightTheme.statusInfo

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