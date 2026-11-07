// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A setting with a list of values: its name, a hint, and a drop-down on the right. In a game's Controls tab, "own"
// marks the value as that game's own (● with the way back to ALL GAMES: reset()).
// options: [{value: "...", label: "..."}]; current: the chosen value; chosen(value) when the player picks one.
import QtQuick
import ".."

Item {
    id: choice
    property string label
    property string hint
    property var options: []
    property string current
    property bool own: false
    signal chosen(string value)
    signal reset()

    width: parent ? parent.width : 600
    height: Math.max(48, texts.implicitHeight + 16)

    function indexOf(value) {
        for (var i = 0; i < options.length; i++)
            if (options[i].value === value) return i
        return -1
    }

    Item {
        id: mark
        anchors { right: box.left; rightMargin: choice.own ? 16 : 0; verticalCenter: parent.verticalCenter }
        width: choice.own ? ownMark.implicitWidth : 0
        height: 22
        OwnMark { id: ownMark; visible: choice.own; onReset: choice.reset() }
    }
    Column {
        id: texts
        anchors { left: parent.left; right: mark.left; rightMargin: 24; verticalCenter: parent.verticalCenter }
        spacing: 4
        Text { width: parent.width; text: choice.label; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 15 }
        Text { width: parent.width; text: choice.hint; visible: text.length > 0; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
    }
    DropDown {
        id: box
        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
        width: 260
        model: choice.options
        textRole: "label"
        currentIndex: choice.indexOf(choice.current)
        onActivated: (index) => choice.chosen(choice.options[index].value)
    }
}
