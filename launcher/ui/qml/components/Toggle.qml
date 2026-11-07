// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// An on/off setting: its name, a hint under it, and the switch on the right. In a game's Controls tab, "own" marks
// the value as that game's own (● with the way back to ALL GAMES: reset()).
import QtQuick
import ".."

Item {
    id: toggle
    property string label
    property string hint
    property bool checked: false
    property bool own: false
    signal toggled(bool checked)
    signal reset()

    width: parent ? parent.width : 600
    height: Math.max(48, texts.implicitHeight + 16)

    Item {
        id: mark
        anchors { right: knob.left; rightMargin: toggle.own ? 16 : 0; verticalCenter: parent.verticalCenter }
        width: toggle.own ? ownMark.implicitWidth : 0
        height: 22
        OwnMark { id: ownMark; visible: toggle.own; onReset: toggle.reset() }
    }
    Column {
        id: texts
        anchors { left: parent.left; right: mark.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 4
        Text { width: parent.width; text: toggle.label; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 15 }
        Text { width: parent.width; text: toggle.hint; visible: text.length > 0; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
    }
    Rectangle {
        id: knob
        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
        width: 48; height: 24; radius: 12
        color: toggle.checked ? Theme.gold : Theme.line
        Rectangle {
            width: 18; height: 18; radius: 9
            y: 3; x: toggle.checked ? parent.width - width - 3 : 3
            color: toggle.checked ? Theme.base : Theme.dim
            Behavior on x { NumberAnimation { duration: 100 } }
        }
    }
    MouseArea {
        anchors { left: parent.left; right: mark.left; top: parent.top; bottom: parent.bottom }
        onClicked: toggle.toggled(!toggle.checked)
    }
    MouseArea { anchors.fill: knob; onClicked: toggle.toggled(!toggle.checked) }
}
