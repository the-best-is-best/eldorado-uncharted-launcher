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
        width: 48; height: 26; radius: 13
        color: toggle.checked ? Theme.accent : Theme.line
        border.color: toggle.checked ? "transparent" : Qt.rgba(1, 1, 1, 0.08)
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Rectangle {
            width: 20; height: 20; radius: 10
            // Right to left the switch is on at its left end.
            y: 3; x: toggle.checked !== LayoutMirroring.enabled ? parent.width - width - 3 : 3
            color: toggle.checked ? Theme.accentInk : Theme.dim
            Behavior on x { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
    }
    MouseArea {
        anchors { left: parent.left; right: mark.left; top: parent.top; bottom: parent.bottom }
        onClicked: toggle.toggled(!toggle.checked)
    }
    MouseArea { anchors.fill: knob; onClicked: toggle.toggled(!toggle.checked) }
}
