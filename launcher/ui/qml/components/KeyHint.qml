// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A row of key hints ("↑ ↓ CHOOSE", "ENTER PLAY", "TAB SCREENS"): each key cap shows the key for the device in use,
// a keyboard, an Xbox controller or a PlayStation controller (gamepad.device, followed by default).
import QtQuick
import ".."

Row {
    id: hints
    // "keyboard", "xbox" or "playstation"
    property string device: typeof gamepad !== "undefined" ? gamepad.device : "keyboard"
    // [{ action: "choose", text: "CHOOSE" }, ...]: actions are choose, views, accept, back, next, previous, remove, play
    property var entries: []
    spacing: 24

    readonly property var labels: ({
        keyboard: { choose: "↑ ↓", views: "← →", accept: "ENTER", back: "ESC", next: "TAB", previous: "SHIFT TAB", remove: "DEL", play: "ENTER" },
        xbox: { choose: "↑ ↓", views: "← →", accept: "A", back: "B", next: "RB", previous: "LB", remove: "Y", play: "MENU" },
        playstation: { choose: "↑ ↓", views: "← →", accept: "✕", back: "○", next: "R1", previous: "L1", remove: "△", play: "OPTIONS" }
    })

    function label(action) {
        var set = labels[device] || labels.keyboard
        return set[action] || action.toUpperCase()
    }

    Repeater {
        model: hints.entries
        Row {
            spacing: 8
            Rectangle {
                width: Math.max(22, cap.implicitWidth + 12)
                height: 20
                radius: 3
                color: Qt.rgba(0, 0, 0, 0.35)
                border.color: Theme.faint
                Text {
                    id: cap
                    anchors.centerIn: parent
                    text: hints.label(modelData.action)
                    color: Theme.dim
                    font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: 1
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: modelData.text
                color: Theme.faint
                font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: 2
            }
        }
    }
}
