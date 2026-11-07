// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// One game on the home screen: its number (in the game's own color), title and play time on a glass plate over the
// picture. The chosen one is raised, brighter, edged in its color with a glowing bar; a small mark says it has a
// save to continue.
import QtQuick
import ".."

Item {
    id: card
    property var game
    property bool selected: false
    signal clicked()
    signal doubleClicked()

    width: 360
    height: 96
    readonly property color tone: Theme.accentOf(game ? game.key : "")
    readonly property bool hot: area.containsMouse && enabled
    opacity: enabled || selected ? 1.0 : 0.45

    // The soft shadow of a raised card.
    Rectangle {
        x: plate.x + 2; y: plate.y + 6
        width: plate.width - 4; height: plate.height
        radius: Theme.radius
        color: Theme.shadow
        opacity: card.selected ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: Theme.fast } }
    }
    // The glow of the game's color around the chosen card.
    Rectangle {
        anchors.fill: plate
        anchors.margins: -4
        radius: Theme.radius + 4
        color: "transparent"
        border.width: 4
        border.color: Qt.rgba(card.tone.r, card.tone.g, card.tone.b, 0.16)
        visible: card.selected
    }
    Rectangle {
        id: plate
        width: parent.width
        height: parent.height
        // Raised: the chosen card stands out of the row; the mouse lifts the others a little.
        x: card.selected ? (LayoutMirroring.enabled ? -10 : 10) : 0
        radius: Theme.radius
        color: card.selected ? Theme.glassStrong : card.hot ? Qt.rgba(0.09, 0.1, 0.13, 0.72) : Theme.glass
        border.color: card.selected ? card.tone : card.hot ? Qt.rgba(1, 1, 1, 0.16) : Theme.glassEdge
        border.width: card.selected ? 1.5 : 1
        scale: card.hot && !card.selected ? 1.015 : 1.0
        Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
        Behavior on scale { NumberAnimation { duration: Theme.fast } }

        // The chosen card's bar in the game's color at its start edge.
        Rectangle {
            anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
            width: 4; radius: 2
            height: card.selected ? parent.height - 36 : 0
            color: card.tone
            Behavior on height { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
        }
        Text {
            id: number
            anchors { left: parent.left; leftMargin: 26; verticalCenter: parent.verticalCenter }
            text: card.game.number
            color: card.tone
            opacity: card.selected ? 1.0 : 0.55
            font.family: Theme.titleFont
            font.pixelSize: 44
            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
        }
        Column {
            anchors { left: parent.left; leftMargin: 78; right: parent.right; rightMargin: 36; verticalCenter: parent.verticalCenter }
            spacing: 6
            Text {
                width: parent.width
                text: card.game.title
                color: card.selected ? Theme.ink : Theme.dim
                font.family: Theme.titleFont; font.pixelSize: 19
                elide: Text.ElideRight
            }
            Text {
                width: parent.width
                text: card.game.playTime + "  ·  " + card.game.lastPlayed
                color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
        // A save to continue from.
        Rectangle {
            anchors { right: parent.right; rightMargin: 18; verticalCenter: parent.verticalCenter }
            width: 8; height: 8; radius: 4
            visible: card.game.hasSave
            color: card.selected ? card.tone : Theme.faint
        }
    }
    MouseArea {
        id: area
        anchors.fill: plate
        hoverEnabled: true
        cursorShape: card.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: card.clicked()
        onDoubleClicked: card.doubleClicked()
    }
}
