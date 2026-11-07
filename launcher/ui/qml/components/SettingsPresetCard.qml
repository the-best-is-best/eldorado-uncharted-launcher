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
    radius: Theme.radius
    color: preset.selected ? Qt.tint(Theme.panel, Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.08))
         : area.containsMouse || focused ? Theme.panelHigh : Theme.panel
    border.color: preset.selected ? Theme.accent : focused ? Theme.accentLine : Theme.line
    border.width: preset.selected ? 2 : 1
    Behavior on color { ColorAnimation { duration: Theme.fast } }
    Behavior on border.color { ColorAnimation { duration: Theme.fast } }

    Column {
        anchors { fill: parent; margins: 18 }
        spacing: 8
        Item {
            width: parent.width; height: name.implicitHeight
            Text { id: name; anchors.left: parent.left; text: card.preset.title || ""; color: card.preset.selected ? Theme.accent : Theme.ink; font.family: Theme.titleFont; font.pixelSize: 20; font.letterSpacing: Theme.tracking(2) }
            Rectangle {
                visible: card.preset.yourPc === true
                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                width: badge.implicitWidth + 16; height: badge.implicitHeight + 6; radius: height / 2
                color: Theme.accent
                Text { id: badge; anchors.centerIn: parent; text: qsTr("YOUR PC"); color: Theme.accentInk; font.family: Theme.bodyFont; font.pixelSize: 10; font.bold: true; font.letterSpacing: Theme.tracking(1) }
            }
        }
        Text { width: parent.width; text: card.preset.summary || ""; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight }
        Text { width: parent.width; height: parent.height - y; text: card.preset.detail || ""; color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 12; wrapMode: Text.WordWrap; elide: Text.ElideRight }
    }
    MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: card.clicked() }
}
