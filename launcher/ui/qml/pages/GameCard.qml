// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// One game on the home screen: its number, title and play time on a dark plate over the picture; gold edge when
// chosen, a small mark when it has a save to continue.
import QtQuick
import ".."

Rectangle {
    id: card
    property var game
    property bool selected: false
    signal clicked()
    signal doubleClicked()

    width: 360
    height: 96
    radius: 4
    color: selected ? Qt.rgba(Theme.panel.r, Theme.panel.g, Theme.panel.b, 0.94) : Qt.rgba(0.06, 0.04, 0.025, 0.62)
    border.color: selected ? Theme.gold : Theme.line
    border.width: selected ? 2 : 1
    opacity: enabled || selected ? 1.0 : 0.45
    Behavior on color { ColorAnimation { duration: 120 } }

    Text {
        x: 20
        anchors.verticalCenter: parent.verticalCenter
        text: card.game.number
        color: card.selected ? Theme.gold : Theme.faint
        font.family: Theme.titleFont
        font.pixelSize: 44
    }
    Column {
        x: 72
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
        Text { text: card.game.title; color: card.selected ? Theme.ink : Theme.dim; font.family: Theme.titleFont; font.pixelSize: 19 }
        Text { text: card.game.playTime + "  ·  " + card.game.lastPlayed; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12 }
    }
    // A save to continue from.
    Rectangle {
        anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter }
        width: 8; height: 8; radius: 4
        visible: card.game.hasSave
        color: card.selected ? Theme.gold : Theme.faint
    }
    MouseArea {
        anchors.fill: parent
        onClicked: card.clicked()
        onDoubleClicked: card.doubleClicked()
    }
}
