// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The Gallery screen: one game's F12 screenshots in a grid, newest first.
// Keys (from Main.qml): arrows move in the grid; Up from the first row goes to the game row, where Left/Right change
// game and Enter opens the folder; in the grid Enter opens the picture, Delete twice moves it to the Recycle Bin.
import QtQuick
import ".."
import "../components"

Page {
    id: page
    title: "GALLERY"
    subtitle: grid.count + (grid.count === 1 ? " screenshot" : " screenshots")

    property bool onGames: true               // the focus is on the game row, not on the grid
    property int armed: -1                    // the picture waiting for its second Delete

    readonly property int columns: Math.max(1, Math.floor(grid.width / grid.cellWidth))

    function disarm() { armed = -1 }
    function changeGame(step) {
        gallery.setGame((gallery.gameIndex + gallery.games.length + step) % gallery.games.length)
        grid.currentIndex = 0
        onGames = true
    }
    function up() {
        disarm()
        if (onGames) return
        if (grid.currentIndex < columns) onGames = true
        else grid.currentIndex -= columns
    }
    function down() {
        disarm()
        if (onGames) { if (grid.count > 0) onGames = false; return }
        grid.currentIndex = Math.min(grid.count - 1, grid.currentIndex + columns)
    }
    function moveLeft() {
        disarm()
        if (onGames) changeGame(-1)
        else if (grid.currentIndex > 0) grid.currentIndex -= 1
    }
    function moveRight() {
        disarm()
        if (onGames) changeGame(1)
        else if (grid.currentIndex + 1 < grid.count) grid.currentIndex += 1
    }
    function accept() {
        disarm()
        if (onGames) gallery.openFolder()
        else gallery.open(grid.currentIndex)
    }
    function remove() {
        if (onGames || grid.count === 0) return
        if (armed !== grid.currentIndex) { armed = grid.currentIndex; return }
        disarm()
        var keep = grid.currentIndex
        gallery.remove(keep)
        grid.currentIndex = Math.min(keep, grid.count - 1)
        if (grid.count === 0) onGames = true
    }

    // New F12 shots after a game ran: read again each time the screen is shown.
    onVisibleChanged: if (visible) { disarm(); gallery.reload(); onGames = grid.count === 0 }

    // The three games and the folder.
    GameTabs {
        id: tabs
        games: gallery.games
        current: gallery.gameIndex
        active: page.onGames
        onPicked: (index) => page.changeGame(index - gallery.gameIndex)
        Item { width: 8; height: 1 }
        TextButton { text: "OPEN FOLDER"; implicitHeight: 34; onClicked: gallery.openFolder() }
    }

    // A delete waiting for its second press, or what the last action said; the keys are at the bottom.
    Text {
        id: note
        anchors { top: tabs.bottom; topMargin: 10; left: parent.left; right: parent.right }
        text: page.armed >= 0 ? "Press Delete again to move this screenshot to the Recycle Bin." : gallery.note
        color: page.armed >= 0 ? Theme.dangerText : Theme.faint
        font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: 1
        elide: Text.ElideRight
    }

    Text {
        anchors { top: note.bottom; topMargin: 24; left: parent.left; right: parent.right }
        visible: grid.count === 0
        text: "No screenshots yet: press F12 in the game to take one."
        wrapMode: Text.WordWrap
        color: Theme.dim; font.family: Theme.titleFont; font.pixelSize: 17
    }

    KeyHint {
        id: hints
        anchors { left: parent.left; bottom: parent.bottom }
        entries: page.onGames ? [{ action: "views", text: "GAME" }, { action: "accept", text: "OPEN FOLDER" }]
                              : [{ action: "choose", text: "BROWSE" }, { action: "accept", text: "OPEN" },
                                 { action: "remove", text: "RECYCLE BIN (TWICE)" }]
    }

    GridView {
        id: grid
        anchors { top: note.bottom; topMargin: 14; bottom: hints.top; bottomMargin: 12; left: parent.left; right: parent.right }
        clip: true
        model: gallery.rows
        cellWidth: Math.max(220, Math.floor(width / Math.max(1, Math.floor(width / 270))))
        cellHeight: Math.floor((cellWidth - 16) * 9 / 16) + 44
        keyNavigationEnabled: false
        highlightMoveDuration: 100
        delegate: Item {
            id: cell
            readonly property bool selected: GridView.isCurrentItem && !page.onGames
            readonly property bool armedHere: page.armed === index
            width: grid.cellWidth
            height: grid.cellHeight
            Rectangle {
                id: frame
                x: 0; y: 0
                width: parent.width - 16
                height: Math.floor(width * 9 / 16)
                color: Theme.panel
                border.width: cell.selected ? 2 : 1
                border.color: cell.armedHere ? Theme.danger : cell.selected ? Theme.gold : Theme.line
                Image {
                    anchors { fill: parent; margins: 2 }
                    source: modelData.url
                    sourceSize.width: 480
                    asynchronous: true
                    fillMode: Image.PreserveAspectCrop
                    opacity: cell.armedHere ? 0.5 : 1.0
                }
            }
            Text {
                anchors { top: frame.bottom; topMargin: 6; left: frame.left; right: frame.right }
                text: modelData.label
                color: cell.selected ? Theme.ink : Theme.faint
                font.family: Theme.bodyFont; font.pixelSize: 12
                elide: Text.ElideRight
            }
            MouseArea {
                anchors.fill: frame
                onClicked: { page.disarm(); grid.currentIndex = index; page.onGames = false }
                onDoubleClicked: gallery.open(index)
            }
        }
    }
}
