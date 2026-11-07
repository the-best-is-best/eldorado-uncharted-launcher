// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// One row of a list (a save, a trophy, a backup): an optional picture, a title, a detail line, a note on the right.
// "armed" shows the row red (a delete waiting for its second press). "backwards": the lines run from their
// sentence's end to its start (Arabic shown as the game stored it), so a long one is cut at the left and keeps
// the chapter's name.
import QtQuick
import ".."

Rectangle {
    id: row
    property string title
    property string detail
    property string note
    property url picture
    property bool selected: false
    property bool armed: false
    property bool backwards: false
    readonly property int cut: backwards ? Text.ElideLeft : Text.ElideRight
    property int pictureWidth: picture.toString().length > 0 ? 128 : 0
    signal clicked()
    signal doubleClicked()

    width: ListView.view ? ListView.view.width : 600
    height: 80
    radius: 3
    color: armed ? Qt.darker(Theme.danger, 2.2) : selected ? Theme.panel : "transparent"
    border.color: armed ? Theme.danger : selected ? Theme.gold : "transparent"
    border.width: 1

    Image {
        id: image
        x: 10
        anchors.verticalCenter: parent.verticalCenter
        width: row.pictureWidth
        height: width * 9 / 16
        source: row.picture
        visible: row.pictureWidth > 0
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: 256
    }
    Column {
        anchors { left: image.right; leftMargin: 16; right: noteText.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
        spacing: 5
        Text { width: parent.width; text: row.title; color: row.selected ? Theme.ink : Theme.dim; font.family: Theme.titleFont; font.pixelSize: 17; elide: row.cut }
        Text { width: parent.width; text: row.detail; visible: text.length > 0; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12; elide: row.cut }
    }
    Text {
        id: noteText
        anchors { right: parent.right; rightMargin: 16; verticalCenter: parent.verticalCenter }
        text: row.note
        color: row.armed ? Theme.dangerText : Theme.faint
        font.family: Theme.bodyFont
        font.pixelSize: 12
    }
    MouseArea {
        anchors.fill: parent
        onClicked: row.clicked()
        onDoubleClicked: row.doubleClicked()
    }
}
