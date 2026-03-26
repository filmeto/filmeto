// Theme.qml - Unified theme configuration for all QML components
// Single source of truth for colors, spacing, and typography

pragma Singleton
import QtQuick 2.15

QtObject {
    // ─────────────────────────────────────────────────────────────
    // Theme State
    // ─────────────────────────────────────────────────────────────
    property string currentTheme: "dark"

    // ─────────────────────────────────────────────────────────────
    // Dark Theme Colors
    // ─────────────────────────────────────────────────────────────
    readonly property var darkTheme: {
        // Background colors
        background: "#1e1e1e",
        backgroundSecondary: "#252525",
        cardBackground: "#2d2d2d",
        inputBackground: "#1e1e1e",
        overlayBackground: "#000000",

        // Text colors
        textPrimary: "#e0e0e0",
        textSecondary: "#b0b0b0",
        textTertiary: "#808080",
        textDisabled: "#606060",
        textOnDark: "#ffffff",

        // Border colors
        border: "#3a3a3a",
        borderSubtle: "#303030",
        borderFocus: "#3498db",
        borderHover: "#505050",

        // Accent colors
        accent: "#3498db",
        accentHover: "#5ba0f2",
        accentPressed: "#2980b9",

        // Semantic colors
        success: "#4CAF50",
        successHover: "#66bb6a",
        successPressed: "#388e3c",

        warning: "#FF9800",
        warningHover: "#ffa726",
        warningPressed: "#f57c00",

        error: "#F44336",
        errorHover: "#ef5350",
        errorPressed: "#d32f2f",

        info: "#2196F3",
        infoHover: "#42a5f5",
        infoPressed: "#1976d2",

        // Scrollbar colors
        scrollbarBackground: "#2b2d30",
        scrollbarHandle: "#505254",
        scrollbarHandleHover: "#606264",

        // Message bubble colors
        messageBubbleUser: "#4a90e2",
        messageBubbleAgent: "#353535",
        messageBubbleThinking: "#2a2a2a",
        messageBubbleError: "#2a1a1a",

        // Code colors
        codeBackground: "#1e1e1e",
        codeHeader: "#2d2d2d",
        codeText: "#d4d4d4",
    }

    // ─────────────────────────────────────────────────────────────
    // Light Theme Colors
    // ─────────────────────────────────────────────────────────────
    readonly property var lightTheme: {
        // Background colors
        background: "#f5f5f5",
        backgroundSecondary: "#ffffff",
        cardBackground: "#ffffff",
        inputBackground: "#ffffff",
        overlayBackground: "#000000",

        // Text colors
        textPrimary: "#202020",
        textSecondary: "#505050",
        textTertiary: "#808080",
        textDisabled: "#a0a0a0",
        textOnDark: "#ffffff",

        // Border colors
        border: "#e0e0e0",
        borderSubtle: "#f0f0f0",
        borderFocus: "#3498db",
        borderHover: "#d0d0d0",

        // Accent colors
        accent: "#3498db",
        accentHover: "#5ba0f2",
        accentPressed: "#2980b9",

        // Semantic colors
        success: "#4CAF50",
        successHover: "#66bb6a",
        successPressed: "#388e3c",

        warning: "#FF9800",
        warningHover: "#ffa726",
        warningPressed: "#f57c00",

        error: "#F44336",
        errorHover: "#ef5350",
        errorPressed: "#d32f2f",

        info: "#2196F3",
        infoHover: "#42a5f5",
        infoPressed: "#1976d2",

        // Scrollbar colors
        scrollbarBackground: "#f0f0f0",
        scrollbarHandle: "#c0c0c0",
        scrollbarHandleHover: "#a0a0a0",

        // Message bubble colors
        messageBubbleUser: "#4a90e2",
        messageBubbleAgent: "#f5f5f5",
        messageBubbleThinking: "#e8e8e8",
        messageBubbleError: "#fff0f0",

        // Code colors
        codeBackground: "#f6f8fa",
        codeHeader: "#e8e8e8",
        codeText: "#24292e",
    }

    // ─────────────────────────────────────────────────────────────
    // Current Theme (computed)
    // ─────────────────────────────────────────────────────────────
    readonly property var colors: currentTheme === "dark" ? darkTheme : lightTheme

    // ─────────────────────────────────────────────────────────────
    // Color Accessors
    // ─────────────────────────────────────────────────────────────

    // Backgrounds
    readonly property color background: colors.background
    readonly property color backgroundSecondary: colors.backgroundSecondary
    readonly property color cardBackground: colors.cardBackground
    readonly property color inputBackground: colors.inputBackground

    // Text
    readonly property color textPrimary: colors.textPrimary
    readonly property color textSecondary: colors.textSecondary
    readonly property color textTertiary: colors.textTertiary
    readonly property color textDisabled: colors.textDisabled
    readonly property color textOnDark: colors.textOnDark

    // Borders
    readonly property color border: colors.border
    readonly property color borderSubtle: colors.borderSubtle
    readonly property color borderFocus: colors.borderFocus
    readonly property color borderHover: colors.borderHover

    // Accent
    readonly property color accent: colors.accent
    readonly property color accentHover: colors.accentHover
    readonly property color accentPressed: colors.accentPressed

    // Semantic
    readonly property color success: colors.success
    readonly property color successHover: colors.successHover
    readonly property color successPressed: colors.successPressed

    readonly property color warning: colors.warning
    readonly property color warningHover: colors.warningHover
    readonly property color warningPressed: colors.warningPressed

    readonly property color error: colors.error
    readonly property color errorHover: colors.errorHover
    readonly property color errorPressed: colors.errorPressed

    readonly property color info: colors.info
    readonly property color infoHover: colors.infoHover
    readonly property color infoPressed: colors.infoPressed

    // Scrollbar
    readonly property color scrollbarBackground: colors.scrollbarBackground
    readonly property color scrollbarHandle: colors.scrollbarHandle
    readonly property color scrollbarHandleHover: colors.scrollbarHandleHover

    // Message bubbles
    readonly property color messageBubbleUser: colors.messageBubbleUser
    readonly property color messageBubbleAgent: colors.messageBubbleAgent
    readonly property color messageBubbleThinking: colors.messageBubbleThinking
    readonly property color messageBubbleError: colors.messageBubbleError

    // Code
    readonly property color codeBackground: colors.codeBackground
    readonly property color codeHeader: colors.codeHeader
    readonly property color codeText: colors.codeText

    // ─────────────────────────────────────────────────────────────
    // Spacing System
    // ─────────────────────────────────────────────────────────────
    readonly property int spacingTiny: 4
    readonly property int spacingSmall: 8
    readonly property int spacingMedium: 12
    readonly property int spacingLarge: 16
    readonly property int spacingXLarge: 24

    // ─────────────────────────────────────────────────────────────
    // Border Radius System
    // ─────────────────────────────────────────────────────────────
    readonly property int radiusTiny: 2
    readonly property int radiusSmall: 3
    readonly property int radiusMedium: 4
    readonly property int radiusLarge: 6
    readonly property int radiusXLarge: 8
    readonly property int radiusRound: 9999

    // ─────────────────────────────────────────────────────────────
    // Typography System
    // ─────────────────────────────────────────────────────────────
    readonly property int fontTiny: 10
    readonly property int fontSmall: 11
    readonly property int fontMedium: 12
    readonly property int fontDefault: 13
    readonly property int fontLarge: 14
    readonly property int fontXLarge: 16
    readonly property int fontTitle: 18
    readonly property int fontHeader: 20

    // ─────────────────────────────────────────────────────────────
    // Component Sizes
    // ─────────────────────────────────────────────────────────────
    readonly property int buttonHeight: 32
    readonly property int buttonHeightSmall: 28
    readonly property int buttonHeightLarge: 40
    readonly property int inputHeight: 32
    readonly property int iconSize: 16
    readonly property int iconSizeLarge: 20

    // ─────────────────────────────────────────────────────────────
    // Animation Durations
    // ─────────────────────────────────────────────────────────────
    readonly property int durationFast: 100
    readonly property int durationNormal: 150
    readonly property int durationSlow: 200

    // ─────────────────────────────────────────────────────────────
    // Theme Functions
    // ─────────────────────────────────────────────────────────────
    function setTheme(theme) {
        if (theme === "dark" || theme === "light") {
            currentTheme = theme
        }
    }

    function toggleTheme() {
        currentTheme = currentTheme === "dark" ? "light" : "dark"
    }

    // Color manipulation helpers
    function alpha(color, opacity) {
        return Qt.rgba(color.r, color.g, color.b, opacity)
    }

    function withAlpha(colorString, opacity) {
        var c = Qt.color(colorString)
        return Qt.rgba(c.r, c.g, c.b, opacity)
    }
}
