// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// One action of the Controls tab: its name, two key/mouse slots and the controller button.
// row: {action, title, keys: [two labels], capture: [two bools], pad, padValue, padFixed, padOptions,
//       own (bool: in a game's tab, this action's keys or button are the game's own)}.
// A left click on a slot starts the capture, a right click clears it; the controller button is picked from a list;
// the ● mark's "↺ ALL GAMES" returns the action to the shared keys (reset()).
import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: binding
    property var row: ({})
    signal capture(int slot)
    signal clear(int slot)
    signal padChosen(string button)
    signal reset()

    width: parent ? parent.width : 600
    height: 40

    function padIndex() {
        var options = row.padOptions || []
        for (var i = 0; i < options.length; i++)
            if (options[i].value === row.padValue) return i
        return 0
    }

    Text {
        anchors { left: parent.left; verticalCenter: parent.verticalCenter; right: mark.left; rightMargin: 16 }
        text: binding.row.title || ""
        color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 14; elide: Text.ElideRight
    }
    Item {
        id: mark
        anchors { right: slots.left; rightMargin: binding.row.own === true ? 16 : 0; verticalCenter: parent.verticalCenter }
        width: binding.row.own === true ? ownMark.implicitWidth : 0
        height: 22
        OwnMark { id: ownMark; visible: binding.row.own === true; onReset: binding.reset() }
    }
    Row {
        id: slots
        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
        spacing: 8
        Repeater {
            model: 2
            Rectangle {
                readonly property bool capturing: binding.row.capture ? binding.row.capture[index] : false
                width: 150; height: 32; radius: 3
                color: capturing ? Theme.line : Theme.panel
                border.color: capturing ? Theme.gold : Theme.line
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 12; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                    text: parent.capturing ? "Press a key…" : (binding.row.keys ? binding.row.keys[index] : "")
                    color: parent.capturing ? Theme.gold : Theme.ink
                    font.family: Theme.bodyFont; font.pixelSize: 13
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton | Qt.RightButton
                    onClicked: (mouse) => mouse.button === Qt.RightButton ? binding.clear(index) : binding.capture(index)
                }
            }
        }
        Rectangle {
            width: 170; height: 32; radius: 3
            visible: binding.row.padFixed === true
            color: "transparent"; border.color: Theme.line
            Text {
                anchors.centerIn: parent
                text: binding.row.pad || ""
                color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 13
            }
        }
        DropDown {
            width: 170; height: 32
            visible: binding.row.padFixed !== true
            model: binding.row.padOptions || []
            textRole: "label"
            currentIndex: binding.padIndex()
            onActivated: (index) => binding.padChosen(binding.row.padOptions[index].value)
            font.pixelSize: 13
        }
    }
}
