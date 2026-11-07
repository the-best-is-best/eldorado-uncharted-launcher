// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A secondary button: an outline in the chosen game's color, for actions beside the main one (Open folder,
// Restore, Change...). It fills softly under the mouse.
import QtQuick
import ".."

Rectangle {
    id: button
    property alias text: label.text
    property bool danger: false
    signal clicked()

    readonly property color tone: danger ? Theme.danger : Theme.accent
    implicitWidth: Math.max(120, label.implicitWidth + 36)
    implicitHeight: 38
    radius: Theme.radiusSmall
    color: area.containsMouse && button.enabled ? Qt.rgba(tone.r, tone.g, tone.b, area.pressed ? 0.26 : 0.16)
                                                : Qt.rgba(1, 1, 1, 0.02)
    border.color: area.containsMouse ? tone : Qt.rgba(tone.r, tone.g, tone.b, 0.6)
    border.width: 1
    opacity: enabled ? 1.0 : 0.4
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.fast } }

    Text {
        id: label
        anchors.centerIn: parent
        color: button.danger ? Theme.dangerText : (area.containsMouse ? Theme.accentHover : Theme.accent)
        font.family: Theme.strongFont
        font.pixelSize: 13
        font.letterSpacing: Theme.tracking(2)
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (button.enabled) button.clicked()
    }
}
