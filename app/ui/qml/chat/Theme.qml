// Theme.qml - Centralized theme configuration for the chat interface
// This file defines all colors and styling for easy theme switching

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
        backgroundColor: "#252525",
        messageBubbleUser: "#4a90e2",
        messageBubbleAgent: "#353535",
        messageBubbleThinking: "#2a2a2a",
        messageBubbleError: "#2a1a1a",

        // Text colors
        textPrimary: "#e0e0e0",
        textSecondary: "#b0b0b0",
        textTertiary: "#808080",
        textOnDark: "#ffffff",
        textOnError: "#d0d0d0",

        // Scrollbar colors
        scrollbarBackground: "#2b2d30",
        scrollbarHandle: "#505254",
        scrollbarHandleHover: "#606264",

        // Border colors
        border: "#404040",
        borderSubtle: "#303030",
        borderError: "#804040",

        // Status colors
        statusSuccess: "#51cf66",
        statusWarning: "#ffd43b",
        statusError: "#ff6b6b",
        statusInfo: "#4a90e2",

        // Syntax highlighting
        codeBackground: "#1e1e1e",
        codeHeader: "#2d2d2d",
        codeText: "#d4d4d4",

        // Accent
        accent: "#4a90e2",
        accentHover: "#5ba0f2",
    }

    // ─────────────────────────────────────────────────────────────
    // Light Theme
    // ─────────────────────────────────────────────────────────────

    readonly property var lightTheme: {
        // Background colors
        backgroundColor: "#ffffff",
        messageBubbleUser: "#4a90e2",
        messageBubbleAgent: "#f5f5f5",
        messageBubbleThinking: "#e8e8e8",
        messageBubbleError: "#fff0f0",

        // Text colors
        textPrimary: "#202020",
        textSecondary: "#505050",
        textTertiary: "#808080",
        textOnDark: "#ffffff",
        textOnError: "#401010",

        // Scrollbar colors
        scrollbarBackground: "#f0f0f0",
        scrollbarHandle: "#c0c0c0",
        scrollbarHandleHover: "#a0a0a0",

        // Border colors
        border: "#e0e0e0",
        borderSubtle: "#f0f0f0",
        borderError: "#ffcccc",

        // Status colors
        statusSuccess: "#37b24d",
        statusWarning: "#fcc419",
        statusError: "#fa5252",
        statusInfo: "#339af0",

        // Syntax highlighting
        codeBackground: "#f6f8fa",
        codeHeader: "#e8e8e8",
        codeText: "#24292e",

        // Accent
        accent: "#4a90e2",
        accentHover: "#3a80d2",
    }

    // ─────────────────────────────────────────────────────────────
    // Current Theme Colors (computed)
    // ─────────────────────────────────────────────────────────────

    readonly property var colors: currentTheme === "dark" ? darkTheme : lightTheme

    // Convenience accessors
    readonly property color backgroundColor: colors.backgroundColor
    readonly property color messageBubbleUser: colors.messageBubbleUser
    readonly property color messageBubbleAgent: colors.messageBubbleAgent
    readonly property color textPrimary: colors.textPrimary
    readonly property color textSecondary: colors.textSecondary
    readonly property color scrollbarHandle: colors.scrollbarHandle
    readonly property color accent: colors.accent

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
