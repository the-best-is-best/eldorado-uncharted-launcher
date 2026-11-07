// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The first start: choose the game folder, every game takes the Recommended settings for this PC, and an offer of
// desktop shortcuts. START finishes it (app.finishFirstStart) and emits finished().
import QtQuick
import ".."
import "../components"

Page {
    id: first
    title: qsTr("WELCOME TO EL DORADO")
    subtitle: qsTr("Three quick steps, then the games are ready to play.")
    signal finished()

    property bool shortcuts: true
    readonly property bool ready: app.gameDir.length > 0

    function accept() { if (ready) finish() }

    function finish() {
        var applied = false
        if (typeof settings !== "undefined" && settings && typeof settings.applyRecommendedToAll === "function") {
            settings.applyRecommendedToAll()
            applied = true
        }
        if (shortcuts)
            app.createShortcuts()
        app.finishFirstStart(applied)
        first.finished()
    }

    Column {
        width: Math.min(parent.width, 760)
        spacing: 28

        Column {
            width: parent.width
            spacing: 10
            Text { text: "1   " + qsTr("YOUR GAME"); color: Theme.accent; font.family: Theme.strongFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(3) }
            Text {
                width: parent.width
                text: first.ready ? app.gameDir
                                  : qsTr("Choose your Uncharted: The Nathan Drake Collection folder: the one with eboot.bin and sce_sys.")
                color: first.ready ? Theme.ink : Theme.dim
                font.family: Theme.bodyFont; font.pixelSize: 15
                wrapMode: Text.WrapAnywhere
            }
            TextButton {
                text: first.ready ? qsTr("CHANGE GAME FOLDER") : qsTr("CHOOSE GAME FOLDER")
                onClicked: app.chooseGameFolder()
            }
        }

        Column {
            width: parent.width
            spacing: 10
            Text { text: "2   " + qsTr("SETTINGS"); color: Theme.accent; font.family: Theme.strongFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(3) }
            Text {
                width: parent.width
                text: qsTr("Every game starts with the Recommended settings for your graphics card. Change them any time in Settings.")
                color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 15; wrapMode: Text.WordWrap
            }
        }

        Column {
            width: parent.width
            spacing: 10
            Text { text: "3   " + qsTr("SHORTCUTS"); color: Theme.accent; font.family: Theme.strongFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(3) }
            Toggle {
                width: parent.width
                label: qsTr("Desktop shortcuts")
                hint: qsTr("One for the launcher and one per game (each starts its game directly).")
                checked: first.shortcuts
                onToggled: function(value) { first.shortcuts = value }
            }
        }

        GoldButton {
            text: qsTr("START")
            opacity: first.ready ? 1.0 : 0.4
            onClicked: first.accept()
        }
    }
}
