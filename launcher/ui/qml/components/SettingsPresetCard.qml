// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A Quick setup card: the preset's name, its summary and what it does. preset: {title, summary, detail, selected,
// yourPc}; "focused" is the keyboard's place.
import QtQuick
import ".."

Rectangle {
    id: card
    property var preset: ({})
    property bool focused: false
    signal clicked()

    height: 170
    radius: 4
    color: preset.selected || area.containsMouse || focused ? Theme.panel : Qt.darker(Theme.panel, 1.25)
    border.color: preset.selected ? Theme.gold : focused ? Theme.dim : Theme.line
    border.width: preset.selected ? 2 : 1

    Column {
        anchors { fill: parent; margins: 18 }
        spacing: 8
        Item {
            width: parent.width; height: name.implicitHeight
            Text { id: name; text: card.preset.title || ""; color: card.preset.selected ? Theme.gold : Theme.ink; font.family: Theme.titleFont; font.pixelSize: 20; font.letterSpacing: 2 }
            Rectangle {
                visible: card.preset.yourPc === true
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: badge.implicitWidth + 14; height: badge.implicitHeight + 6; radius: 2
                color: Theme.gold
                Text { id: badge; anchors.centerIn: parent; text: "YOUR PC"; color: Theme.base; font.family: Theme.bodyFont; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
            }
        }
        Text { width: parent.width; text: card.preset.summary || ""; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight }
        Text { width: parent.width; height: parent.height - y; text: card.preset.detail || ""; color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideRight }
    }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; onClicked: card.clicked() }
}
