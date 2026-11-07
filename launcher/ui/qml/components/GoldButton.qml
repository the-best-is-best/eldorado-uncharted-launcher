// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The big action button (PLAY, START, STOP): a bold pill in the chosen game's color, or red for a stop. It lifts
// a little under the mouse and its soft shadow grows.
import QtQuick
import ".."

Item {
    id: button
    property alias text: label.text
    property bool danger: false
    signal clicked()

    width: 240
    height: 60
    readonly property bool hot: area.containsMouse
    readonly property color fill: danger ? Theme.danger : (hot ? Theme.accentHover : Theme.accent)

    // The shadow: a darker pill a few pixels under the face, plus a faint glow of the button's own color.
    Rectangle {
        anchors.fill: face
        anchors.margins: -6
        anchors.topMargin: button.hot ? 2 : -2
        radius: height / 2
        color: Qt.rgba(button.fill.r, button.fill.g, button.fill.b, button.hot ? 0.2 : 0.0)
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on anchors.topMargin { NumberAnimation { duration: Theme.fast } }
    }
    Rectangle {
        x: face.x + 4; y: face.y + (button.hot ? 7 : 4)
        width: face.width - 8; height: face.height
        radius: height / 2
        color: Theme.shadow
        Behavior on y { NumberAnimation { duration: Theme.fast } }
    }
    Rectangle {
        id: face
        width: parent.width
        height: parent.height
        y: button.hot ? -2 : 0
        radius: height / 2
        color: button.fill
        scale: area.pressed ? 0.98 : 1.0
        Behavior on y { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: 90 } }
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        // A light edge at the top: the pill catches the light.
        Rectangle {
            anchors { fill: parent; margins: 1 }
            radius: height / 2
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.22)
        }
        Text {
            id: label
            anchors.centerIn: parent
            color: button.danger ? Theme.ink : Theme.accentInk
            font.family: Theme.strongFont
            font.pixelSize: 20
            font.letterSpacing: Theme.tracking(6)
        }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: button.clicked()
    }
}
