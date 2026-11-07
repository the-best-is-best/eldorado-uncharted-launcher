// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The three games as tabs at the top of a screen (Saves, Trophies, Gallery). Anything placed inside comes after them.
import QtQuick
import ".."

Row {
    id: tabs
    property var games: []
    property int current: 0
    property bool active: true      // the chosen tab's edge is gold while the keys move between the tabs
    signal picked(int index)
    default property alias extra: after.data

    spacing: 8
    Repeater {
        model: tabs.games
        Rectangle {
            readonly property bool chosen: index === tabs.current
            width: 150; height: 34; radius: 3
            color: chosen ? Theme.panel : "transparent"
            border.color: chosen ? (tabs.active ? Theme.gold : Theme.dim) : Theme.line
            Text {
                anchors.centerIn: parent
                text: "UNCHARTED " + modelData.number
                color: parent.chosen ? Theme.ink : Theme.dim
                font.family: Theme.bodyFont; font.pixelSize: 12; font.letterSpacing: 2
            }
            MouseArea { anchors.fill: parent; onClicked: tabs.picked(index) }
        }
    }
    Row {
        id: after
        spacing: 8
        anchors.verticalCenter: parent.verticalCenter
    }
}
