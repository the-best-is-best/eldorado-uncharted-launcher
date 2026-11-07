// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The Saves screen: the player's saves of all three games, the deleted saves and the backups (Left/Right switch).
// Delete (and restoring a backup) wait for a second press; the row shows it. The model is `saves`.
import QtQuick
import "../components"
import ".."

Page {
    id: page
    title: "SAVES"
    subtitle: saves.viewLine

    function up() { saves.up() }
    function down() { saves.down() }
    function accept() { saves.accept() }
    function remove() { saves.remove() }
    function moveLeft() { saves.stepView(-1) }
    function moveRight() { saves.stepView(1) }

    onVisibleChanged: if (visible) saves.refresh(); else saves.disarm()

    Binding { target: saves; property: "gameRunning"; value: launcher.running }

    Row {
        id: tabs
        spacing: 10
        Repeater {
            model: saves.views
            TextButton {
                text: modelData.name
                opacity: modelData.key === saves.view ? 1.0 : 0.55
                onClicked: saves.setView(modelData.key)
            }
        }
    }

    ListView {
        id: list
        anchors { top: tabs.bottom; topMargin: 18; left: parent.left; right: parent.right; bottom: footer.top; bottomMargin: 12 }
        clip: true
        spacing: 6
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
            text: saves.view === "saves" ? "No saves yet." : saves.view === "deleted" ? "No deleted saves." : "No backups of the saves there now."
            color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 15
        }
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
