// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A secondary button: gold outline, for actions beside the main one (Open folder, Restore, Change...).
import QtQuick
import ".."

Rectangle {
    id: button
    property alias text: label.text
    property bool danger: false
    signal clicked()

    implicitWidth: Math.max(120, label.implicitWidth + 32)
    implicitHeight: 38
    radius: 3
    color: area.containsMouse ? Theme.panel : "transparent"
    border.color: danger ? Theme.danger : Theme.gold
    opacity: enabled ? 1.0 : 0.4

    Text {
        id: label
        anchors.centerIn: parent
        color: button.danger ? Theme.dangerText : Theme.gold
        font.family: Theme.bodyFont
        font.pixelSize: 13
        font.letterSpacing: 2
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        onClicked: if (button.enabled) button.clicked()
    }
}
