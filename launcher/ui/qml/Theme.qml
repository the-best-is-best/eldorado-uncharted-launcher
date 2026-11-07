// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado's colors, shapes and fonts. A dark ground, glass panels over the pictures, and one accent color: the
// chosen game's own (Uncharted 1 jungle green, Uncharted 2 ice blue, Uncharted 3 desert orange). Main.qml moves
// `accent` to the chosen game's color; every button, selection and focus mark takes it from here. The El Dorado
// name keeps its treasure gold.
pragma Singleton
import QtQuick

// ui/theme.py reads the colors from this file for the drawn background (one place for every color).
QtObject {
    id: theme
    readonly property color base: "#0c0e12"
    readonly property color baseTop: "#151920"      // the lighter ground at the top of the drawn map
    readonly property color rail: "#090b0e"         // the side rail, a step below the ground
    readonly property color panel: "#1a1e26"
    readonly property color panelHigh: "#232833"    // a panel under the mouse or the keys
    readonly property color line: "#2c323d"
    readonly property color ink: "#eef1f6"
    readonly property color dim: "#aeb6c3"
    readonly property color faint: "#717b8a"
    readonly property color gold: "#deb058"
    readonly property color parchment: "#d9b98a"   // the glow and the sepia of the drawn background
    readonly property color danger: "#e0524a"
    readonly property color dangerText: "#ff8a7a"  // red text on the dark ground (a delete waiting, an error line)
    readonly property color update: "#5fc48a"      // the rail's UPDATE item when a release is ready

    // Each game's own color: bright on the dark ground, with dark text on top of it.
    readonly property color accentU1: "#34c98a"     // Drake's Fortune: the jungle
    readonly property color accentU2: "#5aaeff"     // Among Thieves: the Himalayan ice
    readonly property color accentU3: "#ff9447"     // Drake's Deception: the desert sunset
    readonly property var accents: ({ u1: accentU1, u2: accentU2, u3: accentU3 })
    function accentOf(key) { return accents[key] !== undefined ? accents[key] : gold }
    function soft(color, alpha) { return Qt.rgba(color.r, color.g, color.b, alpha) }

    // The chosen game's color (Main.qml animates it on a game change) and its shades.
    property color accent: accentU1
    // Set by Main.qml from the launcher's language: Arabic letters join, so they take no letter spacing.
    property bool joinedScript: false
    function tracking(spacing) { return joinedScript ? 0 : spacing }
    readonly property color accentHover: Qt.lighter(accent, 1.12)
    readonly property color accentDark: Qt.darker(accent, 1.9)
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.14)   // a selected row's fill
    readonly property color accentLine: Qt.rgba(accent.r, accent.g, accent.b, 0.55)   // a quieter accent edge
    readonly property color accentInk: "#0a0c10"     // text on an accent fill

    // Glass: the panels over the home screen's picture.
    readonly property color glass: Qt.rgba(0.05, 0.06, 0.08, 0.62)
    readonly property color glassStrong: Qt.rgba(0.06, 0.07, 0.09, 0.84)
    readonly property color glassEdge: Qt.rgba(1, 1, 1, 0.09)
    readonly property color glassHover: Qt.rgba(1, 1, 1, 0.05)
    readonly property color shadow: Qt.rgba(0, 0, 0, 0.38)

    readonly property int radius: 12        // cards, panels, dialogs
    readonly property int radiusSmall: 8    // buttons, fields, rows
    readonly property int fast: 140         // hover and press
    readonly property int slow: 250         // the accent's change

    readonly property string titleFont: "Georgia"
    readonly property string bodyFont: "Segoe UI"
    readonly property string strongFont: "Segoe UI Semibold"
}
