// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The big action button (PLAY, STOP): gold, or red for a stop.
import QtQuick
import ".."

Rectangle {
    id: button
    property alias text: label.text
    property bool danger: false
    signal clicked()

    width: 240
    height: 60
    radius: 4
    color: danger ? Theme.danger : (area.containsMouse ? Qt.lighter(Theme.gold, 1.1) : Theme.gold)

    Text {
        id: label
        anchors.centerIn: parent
        color: button.danger ? Theme.ink : Theme.base
        font.family: Theme.titleFont
        font.pixelSize: 24
        font.letterSpacing: 6
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: button.clicked()
    }
}
