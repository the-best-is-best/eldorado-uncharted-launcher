// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The Saves screen: the player's saves of all three games, the deleted saves and the backups (Left/Right switch).
// Delete (and restoring a backup) wait for a second press; the row shows it. The model is `saves`.
import QtQuick
import QtQuick.Controls
import "../components"
import ".."

Page {
    id: page
    title: qsTr("SAVES")
    subtitle: saves.viewLine

    function up() { saves.up() }
    function down() { saves.down() }
    function accept() { saves.accept() }
    function remove() { saves.remove() }
    function moveLeft() { saves.stepView(-1) }
    function moveRight() { saves.stepView(1) }

    onVisibleChanged: if (visible) saves.refresh(); else saves.disarm()

    Binding { target: saves; property: "gameRunning"; value: launcher.running }

    // The views as one segmented switch: the shown one filled in the game's color.
    Rectangle {
        id: tabs
        width: views.width + 8; height: 42
        radius: height / 2
        color: Qt.rgba(1, 1, 1, 0.04)
        border.color: Theme.glassEdge
        Row {
            id: views
            anchors.centerIn: parent
            spacing: 4
            Repeater {
                model: saves.views
                Rectangle {
                    readonly property bool chosen: modelData.key === saves.view
                    width: Math.max(110, viewName.implicitWidth + 36); height: 34
                    radius: height / 2
                    color: chosen ? Theme.accent : viewArea.containsMouse ? Theme.glassHover : "transparent"
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                    Text {
                        id: viewName
                        anchors.centerIn: parent
                        text: modelData.name
                        color: parent.chosen ? Theme.accentInk : viewArea.containsMouse ? Theme.ink : Theme.dim
                        font.family: Theme.strongFont; font.pixelSize: 12; font.letterSpacing: Theme.tracking(2)
                    }
                    MouseArea { id: viewArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: saves.setView(modelData.key) }
                }
            }
        }
    }

    ListView {
        ScrollBar.vertical: listBar
        id: list
        anchors { top: tabs.bottom; topMargin: 18; left: parent.left; right: parent.right; rightMargin: 20; bottom: footer.top; bottomMargin: 12 }
        clip: true
        spacing: 8
        model: saves.rows
        currentIndex: saves.selectedIndex
        highlightFollowsCurrentItem: false
        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
        delegate: ListRow {
            title: modelData.title
            detail: modelData.detail
            note: modelData.note
            picture: modelData.picture
            backwards: modelData.backwards
            selected: index === saves.selectedIndex
            armed: selected && saves.armed
            onClicked: saves.select(index)
            onDoubleClicked: { saves.select(index); saves.accept() }
        }

        Text {
            anchors.centerIn: parent
            visible: list.count === 0
            text: saves.view === "saves" ? qsTr("No saves yet.") : saves.view === "deleted" ? qsTr("No deleted saves.") : qsTr("No backups of the saves there now.")
            color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 15
        }
    }
    Scroller {
        id: listBar
        anchors { top: list.top; bottom: list.bottom; left: list.right; leftMargin: 4 }
    }

    Column {
        id: footer
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        spacing: 6
        Text {
            width: parent.width
            text: saves.status
            visible: text.length > 0
            color: saves.statusIsError ? Theme.dangerText : Theme.dim
            font.family: Theme.bodyFont; font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
        KeyHint { entries: saves.hints }
    }
}
