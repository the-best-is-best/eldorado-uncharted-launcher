// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The mark of a game's own control item (●) with the way back: a click returns the item to ALL GAMES.
import QtQuick
import ".."

Row {
    id: mark
    signal reset()
    spacing: 6
    height: 22

    Text {
        anchors.verticalCenter: parent.verticalCenter
        text: "●"
        color: Theme.gold; font.pixelSize: 11
    }
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        width: back.implicitWidth + 16; height: 22; radius: 3
        color: area.containsMouse ? Theme.panel : "transparent"
        border.color: Theme.line
        Text {
            id: back
            anchors.centerIn: parent
            text: "↺ ALL GAMES"
            color: area.containsMouse ? Theme.ink : Theme.faint
            font.family: Theme.bodyFont; font.pixelSize: 10; font.letterSpacing: 1
        }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: mark.reset() }
    }
}
