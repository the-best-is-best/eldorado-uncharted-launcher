// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The three games as tabs at the top of a screen (Saves, Trophies, Gallery), each in its own game's color.
// Anything placed inside comes after them.
import QtQuick
import ".."

Row {
    id: tabs
    property var games: []
    property int current: 0
    property bool active: true      // the chosen tab shows its full color while the keys move between the tabs
    signal picked(int index)
    default property alias extra: after.data

    spacing: 8
    Repeater {
        model: tabs.games
        Rectangle {
            id: tab
            readonly property bool chosen: index === tabs.current
            readonly property color tone: Theme.accentOf(modelData.key)
            width: 150; height: 36; radius: height / 2
            color: chosen ? Qt.rgba(tone.r, tone.g, tone.b, tabs.active ? 0.2 : 0.12)
                          : tabArea.containsMouse ? Theme.glassHover : "transparent"
            border.color: chosen ? (tabs.active ? tone : Qt.rgba(tone.r, tone.g, tone.b, 0.5)) : Theme.line
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            Row {
                anchors.centerIn: parent
                spacing: 8
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 7; height: 7; radius: 4
                    color: tab.tone
                    opacity: tab.chosen ? 1.0 : 0.6
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "UNCHARTED " + modelData.number
                    color: tab.chosen ? Theme.ink : Theme.dim
                    font.family: tab.chosen ? Theme.strongFont : Theme.bodyFont
                    font.pixelSize: 12; font.letterSpacing: Theme.tracking(2)
                }
            }
            MouseArea { id: tabArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tabs.picked(index) }
        }
    }
    Row {
        id: after
        spacing: 8
        anchors.verticalCenter: parent.verticalCenter
    }
}
