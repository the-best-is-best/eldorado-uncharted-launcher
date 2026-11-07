// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The Trophies screen: one game's set (from the player's own trophy pack), its percent and grade counts on the left,
// the list on the right (earned first, newest first; hidden ones stay hidden until earned).
// Keys (from Main.qml): Up/Down move in the list, Left/Right change game.
import QtQuick
import QtQuick.Controls
import ".."
import "../components"

Page {
    id: page
    title: qsTr("TROPHIES")
    subtitle: trophies.available ? qsTr("%1 of %2 earned").arg(trophies.count).arg(trophies.total) : ""

    readonly property var gradeColors: ({ "P": "#b9d7e6", "G": "#e6c25a", "S": "#c9cdd2", "B": "#c08a5a" })

    function up() { list.decrementCurrentIndex() }
    function down() { list.incrementCurrentIndex() }
    function moveLeft() { trophies.setGame((trophies.gameIndex + trophies.games.length - 1) % trophies.games.length) }
    function moveRight() { trophies.setGame((trophies.gameIndex + 1) % trophies.games.length) }
    function accept() {}
    function remove() {}

    // New unlocks after a game ran: read again each time the screen is shown.
    onVisibleChanged: if (visible) trophies.reload()
    Connections {
        target: trophies
        function onChanged() { if (list.currentIndex >= list.count) list.currentIndex = 0 }
    }

    // The three games.
    GameTabs {
        id: tabs
        games: trophies.games
        current: trophies.gameIndex
        onPicked: (index) => { trophies.setGame(index); list.currentIndex = 0 }
    }

    Text {
        anchors { top: tabs.bottom; topMargin: 28; left: parent.left; right: parent.right }
        visible: !trophies.available
        text: trophies.note
        wrapMode: Text.WordWrap
        color: Theme.dim; font.family: Theme.titleFont; font.pixelSize: 17
    }

    // Left: the percent and the count of each grade.
    Column {
        id: summary
        visible: trophies.available
        width: Math.min(250, parent.width * 0.3)
        anchors { top: tabs.bottom; topMargin: 28; left: parent.left }
        spacing: 10
        Text { text: trophies.progress + "%"; color: Theme.ink; font.family: Theme.titleFont; font.pixelSize: 54 }
        Rectangle {
            width: parent.width; height: 8; radius: 4; color: Theme.line
            Rectangle {
                width: Math.max(height, parent.width * trophies.progress / 100); height: parent.height; radius: 4; color: Theme.accent
                Behavior on width { NumberAnimation { duration: Theme.slow; easing.type: Easing.OutCubic } }
            }
        }
        Item { width: 1; height: 6 }
        Repeater {
            model: trophies.grades
            Item {
                width: summary.width; height: 24
                Rectangle {
                    width: 10; height: 10; radius: 5
                    anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                    color: page.gradeColors[modelData.grade]
                }
                Text {
                    anchors { left: parent.left; leftMargin: 20; verticalCenter: parent.verticalCenter }
                    text: modelData.name
                    color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(2)
                }
                Text {
                    anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                    text: modelData.earned + " / " + modelData.total
                    color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 13
                }
            }
        }
    }

    // Right: the list.
    ListView {
        ScrollBar.vertical: listBar
        id: list
        visible: trophies.available
        anchors { top: tabs.bottom; topMargin: 28; bottom: hints.top; bottomMargin: 12; left: summary.right; leftMargin: 36; right: parent.right; rightMargin: 20 }
        clip: true
        spacing: 6
        model: trophies.rows
        highlightMoveDuration: 120
        keyNavigationEnabled: false
        delegate: Rectangle {
            id: row
            readonly property bool selected: ListView.isCurrentItem
            width: ListView.view.width
            height: 68
            radius: Theme.radius
            color: selected ? Theme.accentSoft : trophyArea.containsMouse ? Theme.glassHover : Qt.rgba(1, 1, 1, 0.025)
            border.color: selected ? Theme.accentLine : Qt.rgba(1, 1, 1, 0.05)
            Behavior on color { ColorAnimation { duration: Theme.fast } }

            // The pack's own icon; a locked one dimmed, a hidden one not shown at all.
            Rectangle {
                id: iconBox
                width: 48; height: 48; radius: 6
                anchors { left: parent.left; leftMargin: 10; verticalCenter: parent.verticalCenter }
                color: Theme.line
                Image {
                    anchors { fill: parent; margins: 2 }
                    source: modelData.secret ? "" : modelData.icon
                    sourceSize.width: 96
                    asynchronous: true
                    fillMode: Image.PreserveAspectFit
                    opacity: modelData.earned ? 1.0 : 0.35
                }
                Text {
                    anchors.centerIn: parent
                    visible: modelData.secret || modelData.icon.length === 0
                    text: "?"
                    color: Theme.faint; font.family: Theme.titleFont; font.pixelSize: 22
                }
            }
            Column {
                anchors { left: iconBox.right; leftMargin: 14; right: when.left; rightMargin: 16; verticalCenter: parent.verticalCenter }
                spacing: 4
                Text {
                    width: parent.width
                    text: modelData.name
                    color: modelData.earned ? Theme.ink : Theme.dim
                    font.family: Theme.titleFont; font.pixelSize: 16
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: modelData.gradeName + "  ·  " + modelData.detail
                    color: modelData.earned ? page.gradeColors[modelData.grade] || Theme.dim : Theme.faint
                    font.family: Theme.bodyFont; font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
            Text {
                id: when
                anchors { right: parent.right; rightMargin: 14; top: parent.top; topMargin: 12 }
                text: modelData.when
                color: modelData.earned ? Theme.accent : Theme.faint
                font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(2)
            }
            MouseArea { id: trophyArea; anchors.fill: parent; hoverEnabled: true; onClicked: list.currentIndex = index }
        }
    }
    Scroller {
        id: listBar
        anchors { top: list.top; bottom: list.bottom; left: list.right; leftMargin: 4 }
    }
    KeyHint {
        id: hints
        anchors { left: parent.left; bottom: parent.bottom }
        entries: trophies.available ? [{ action: "views", text: qsTr("GAME") }, { action: "choose", text: qsTr("BROWSE") }]
                                    : [{ action: "views", text: qsTr("GAME") }]
    }
    Text {
        anchors { right: parent.right; verticalCenter: hints.verticalCenter }
        visible: list.visible && list.count > 0
        text: (list.currentIndex + 1) + " / " + list.count
        color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 11
    }
}
