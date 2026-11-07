// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A settings row that does something (Change game folder, Clear shader cache...): its name, a hint, a button.
import QtQuick
import ".."

Item {
    id: action
    property string label
    property string hint
    property string buttonText
    property bool danger: false
    signal clicked()

    width: parent ? parent.width : 600
    height: Math.max(48, texts.implicitHeight + 16)

    Column {
        id: texts
        anchors { left: parent.left; right: button.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 4
        Text { width: parent.width; text: action.label; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 15 }
        Text { width: parent.width; text: action.hint; visible: text.length > 0; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
    }
    TextButton {
        id: button
        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
        text: action.buttonText
        danger: action.danger
        onClicked: action.clicked()
    }
}
