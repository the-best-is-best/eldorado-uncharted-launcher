// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// El Dorado's colors and fonts: dark leather, parchment and treasure gold. Every screen takes them from here.
pragma Singleton
import QtQuick

// ui/theme.py reads the colors from this file for the drawn background (one place for every color).
QtObject {
    readonly property color base: "#140e09"
    readonly property color baseTop: "#1c130c"      // the lighter leather at the top of the drawn map
    readonly property color panel: "#2b2016"
    readonly property color line: "#3d3022"
    readonly property color ink: "#f1e6cf"
    readonly property color dim: "#c2b08e"
    readonly property color faint: "#8a7a5c"
    readonly property color gold: "#deb058"
    readonly property color parchment: "#d9b98a"   // the glow and the sepia of the drawn background
    readonly property color danger: "#c8463c"
    readonly property color dangerText: "#ff8a7a"  // red text on the dark ground (a delete waiting, an error line)
    readonly property color update: "#5fc48a"      // the rail's UPDATE item when a release is ready

    readonly property string titleFont: "Georgia"
    readonly property string bodyFont: "Segoe UI"
}
