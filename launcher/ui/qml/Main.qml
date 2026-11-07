// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The launcher's window: the rail on the left (Home, Saves, Trophies, Gallery, Settings; at its foot Update when a
// release is ready, Logs and Quit) and the chosen screen. An action of the rail's foot is also a screen with one
// button, so Tab and a controller reach it; a click on it runs the action at once.
// Keys: Up/Down/Enter go to the screen (its up(), down(), accept(), and optional moveLeft(), moveRight(), remove()),
// Tab / Shift+Tab change screen, Escape goes back home (and asks to quit from there).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    width: 1280
    height: 720
    minimumWidth: 960
    minimumHeight: 540
    // Started from a game's shortcut (--play): no window, the launcher ends with the game.
    visible: !launcher.direct
    color: Theme.base

    // A screen has a page in the stack; an action is shown by the one action page (its name says which).
    readonly property var screens: [
        { name: "HOME", page: 0 }, { name: "SAVES", page: 1 }, { name: "TROPHIES", page: 2 },
        { name: "GALLERY", page: 3 }, { name: "SETTINGS", page: 4 },
        { name: "UPDATE", action: "update" }, { name: "LOGS", action: "logs" }, { name: "QUIT", action: "quit" }
    ]
    readonly property int firstAction: 5
    property int screen: 0

    // While a game's window is up the launcher steps aside, and comes back when the game ends.
    Connections {
        target: launcher
        function onChanged() {
            if (launcher.gameWindowOpen && window.visible)
                window.hide()
            else if (!launcher.gameWindowOpen && !window.visible && !launcher.direct) {
                window.show()
                window.raise()
                window.requestActivate()
            }
        }
    }
    // The update's screen goes with the update.
    Connections {
        target: app
        function onChanged() { if (!window.available(window.screen)) window.screen = 0 }
    }

    // The controller: the same moves as the keys. Off while a game runs (no polling then).
    Connections {
        target: typeof gamepad !== "undefined" ? gamepad : null
        function onAction(name) {
            if (name === "back") window.back()
            else if (name === "next") window.nextScreen(1)
            else if (name === "previous") window.nextScreen(-1)
            else if (name === "play") { window.screen = 0; homePage.accept() }
            else window.call({left: "moveLeft", right: "moveRight"}[name] || name)
        }
    }
    onVisibleChanged: if (typeof gamepad !== "undefined") gamepad.setActive(visible)

    function available(index) { return window.screens[index].action !== "update" || app.updateAvailable }
    function nextScreen(step) {
        if (launcher.running) return
        var count = window.screens.length
        var next = window.screen
        do next = (next + count + step) % count; while (!window.available(next))
        window.screen = next
    }
    function back() {
        if (window.screen === 0) app.quit(true)
        else window.screen = 0
    }
    function current() { return stack.children[stack.currentIndex] }
    function call(name) { var page = current(); if (page && typeof page[name] === "function") page[name]() }

    Item {
        anchors.fill: parent
        focus: true
        Keys.onUpPressed: window.call("up")
        Keys.onDownPressed: window.call("down")
        Keys.onLeftPressed: window.call("moveLeft")
        Keys.onRightPressed: window.call("moveRight")
        Keys.onReturnPressed: window.call("accept")
        Keys.onEnterPressed: window.call("accept")
        Keys.onDeletePressed: window.call("remove")
        Keys.onPressed: if (typeof gamepad !== "undefined") gamepad.keyboardUsed()
        Keys.onTabPressed: window.nextScreen(1)
        Keys.onBacktabPressed: window.nextScreen(-1)
        Keys.onEscapePressed: window.back()

        // One item of the rail: a screen's name, or an action's (UPDATE in its own color while a release waits).
        component RailItem: Rectangle {
            property int at: 0
            readonly property var item: window.screens[at]
            readonly property bool chosen: at === window.screen
            visible: window.available(at)
            width: 160; height: 40; radius: 3
            color: chosen ? Theme.panel : "transparent"
            Rectangle { width: 3; height: parent.height; color: Theme.gold; visible: parent.chosen }
            Text {
                x: 16; anchors.verticalCenter: parent.verticalCenter
                text: parent.item.name
                color: parent.chosen ? Theme.ink : parent.item.action === "update" ? Theme.update : Theme.dim
                font.family: Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: 3
            }
            MouseArea {
                anchors.fill: parent
                enabled: parent.item.action === "quit" || !launcher.running || parent.at === 0
                onClicked: {
                    if (parent.item.action !== undefined) actionPage.run(parent.item.action)
                    else window.screen = parent.at
                }
            }
        }

        // The rail.
        Rectangle {
            id: rail
            width: 200
            anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
            color: Qt.darker(Theme.base, 1.3)
            Column {
                x: 24; y: 32
                spacing: 4
                Text { text: "EL DORADO"; color: Theme.gold; font.family: Theme.titleFont; font.pixelSize: 22; font.letterSpacing: 4 }
                Text { text: "UNCHARTED COLLECTION"; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 10; font.letterSpacing: 2 }
                Item { width: 1; height: 36 }
                Repeater {
                    model: window.firstAction
                    RailItem { at: index }
                }
            }
            Column {
                anchors { left: parent.left; leftMargin: 24; bottom: railHints.top; bottomMargin: 24 }
                spacing: 4
                Repeater {
                    model: window.screens.length - window.firstAction
                    RailItem { at: window.firstAction + index }
                }
            }
            // The keys of the device in use (KeyHint follows it).
            Column {
                id: railHints
                anchors { left: parent.left; leftMargin: 24; bottom: parent.bottom; bottomMargin: 20 }
                spacing: 6
                KeyHint { entries: [{ action: "next", text: "SCREENS" }] }
                KeyHint { entries: [{ action: "back", text: "HOME" }] }
            }
        }

        StackLayout {
            id: stack
            anchors { top: parent.top; bottom: parent.bottom; left: rail.right; right: parent.right }
            currentIndex: window.screens[window.screen].page !== undefined ? window.screens[window.screen].page
                                                                           : window.firstAction
            HomePage { id: homePage }
            SavesPage {}
            TrophiesPage {}
            GalleryPage {}
            SettingsPage {}
            ActionPage { id: actionPage; action: window.screens[window.screen].action || "" }
        }
    }

    // The first start (no game folder yet, or the settings never set up): over everything until START.
    Loader {
        anchors.fill: parent
        active: app.firstStart
        sourceComponent: Rectangle {
            color: Theme.base
            FirstStartPage { anchors.fill: parent }
        }
    }

    // Folder and file pickers, questions, every model's messages, and the long actions' progress.
    AppDialogs {}
}
