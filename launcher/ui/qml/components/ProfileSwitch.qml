// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The player playing (a named profile, like a PS4 user) at the top of the rail; a click lists the players, chooses
// one, makes a new one or renames the one playing. Each player has his own saves in all three games.
import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: profileSwitch
    width: 176
    height: 44

    function openMenu() { menu.open() }
    function initial(name) { return name.length > 0 ? name.charAt(0).toUpperCase() : "?" }

    Rectangle {
        id: pill
        anchors.fill: parent
        radius: height / 2
        color: area.containsMouse || menu.visible ? Theme.panelHigh : Theme.panel
        border.color: menu.visible ? Theme.accent : Theme.glassEdge
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Row {
            anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
            spacing: 10
            Rectangle {
                width: 32; height: 32; radius: 16
                color: Theme.accent
                Text {
                    anchors.centerIn: parent
                    text: profileSwitch.initial(profiles.activeName)
                    color: Theme.accentInk; font.family: Theme.strongFont; font.pixelSize: 15
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                width: 104
                text: profiles.activeName
                color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 14
                elide: Text.ElideRight
            }
        }
        Text {
            anchors { right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
            text: "▾"; color: Theme.dim; font.pixelSize: 12
        }
        MouseArea { id: area; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: menu.open() }
    }

    Popup {
        id: menu
        y: profileSwitch.height + 6
        // Right to left the rail is on the right: the menu opens toward the window, not past its edge.
        x: profileSwitch.LayoutMirroring.enabled ? profileSwitch.width - width : 0
        width: 260
        padding: 8
        onClosed: { newName.text = ""; renaming = false }
        property bool renaming: false
        background: Rectangle { color: Theme.panel; radius: Theme.radius; border.color: Theme.accentLine }
        contentItem: Column {
            spacing: 4
            Text {
                leftPadding: 8; bottomPadding: 4
                text: qsTr("PLAYERS"); color: Theme.accent
                font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(2)
            }
            Repeater {
                model: profiles.all
                Rectangle {
                    width: 244; height: 40; radius: Theme.radiusSmall
                    color: modelData.active ? Theme.accentSoft : (rowArea.containsMouse ? Theme.glassHover : "transparent")
                    Row {
                        anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                        spacing: 10
                        Rectangle {
                            width: 26; height: 26; radius: 13
                            color: modelData.active ? Theme.accent : Theme.line
                            Text { anchors.centerIn: parent; text: profileSwitch.initial(modelData.name); color: modelData.active ? Theme.accentInk : Theme.ink; font.pixelSize: 12; font.family: Theme.strongFont }
                        }
                        Text { anchors.verticalCenter: parent.verticalCenter; width: 170; text: modelData.name; color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 14; elide: Text.ElideRight }
                    }
                    MouseArea { id: rowArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { profiles.choose(modelData.id); menu.close() } }
                }
            }
            Rectangle { width: 244; height: 1; color: Theme.line }
            // A name for a new player, or the new name of the one playing.
            TextField {
                id: newName
                width: 244
                maximumLength: 24
                placeholderText: menu.renaming ? qsTr("New name for %1").arg(profiles.activeName) : qsTr("New player's name")
                color: Theme.ink
                placeholderTextColor: Theme.faint
                font.family: Theme.bodyFont; font.pixelSize: 14
                background: Rectangle { radius: Theme.radiusSmall; color: Theme.base; border.color: newName.activeFocus ? Theme.accent : Theme.line }
                onAccepted: done()
                function done() {
                    if (text.trim().length === 0) return
                    if (menu.renaming) profiles.rename(profiles.activeId, text)
                    else profiles.create(text)
                    menu.close()
                }
            }
            Row {
                spacing: 8
                TextButton { text: menu.renaming ? qsTr("RENAME") : qsTr("ADD PLAYER"); implicitWidth: 118; onClicked: newName.done() }
                TextButton {
                    implicitWidth: 118
                    text: menu.renaming ? qsTr("CANCEL") : qsTr("RENAME")
                    onClicked: { menu.renaming = !menu.renaming; newName.text = ""; newName.forceActiveFocus() }
                }
            }
        }
    }
}
