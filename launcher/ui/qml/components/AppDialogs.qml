// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The pickers and questions `app` (ui/app_model.py) asks for: a folder (game, update, game_destination: where an
// installed game goes), a file (pkg: the update's .pkg, game_pkg: the game's), a yes/no question; the one message
// box of every model (app, launcher, settings); and the panel of a long action (its step, its progress, CANCEL
// when the action can stop). Windows shows its own folder and file dialogs.
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import ".."

Item {
    id: dialogs

    readonly property var folderTitles: ({
        game: "Select the Uncharted game folder (the one with eboot.bin and sce_sys)",
        update: "Choose the extracted game update 1.02 folder",
        game_destination: "Choose where to put the game (about 60 GB)"
    })
    readonly property var fileTitles: ({
        pkg: "Choose the game update (.pkg)",
        game_pkg: "Choose the game (.pkg), not the update"
    })

    function show(text) {
        notice.text = text
        notice.open()
    }

    Connections {
        target: app
        function onPickFolder(kind) {
            folderPicker.kind = kind
            folderPicker.title = dialogs.folderTitles[kind] || "Choose a folder"
            // The game goes next to its package unless the player picks elsewhere.
            if (kind === "game_destination" && app.pendingPkgFolder !== "")
                folderPicker.currentFolder = app.pendingPkgFolder
            folderPicker.open()
        }
        function onPickFile(kind) {
            filePicker.kind = kind
            filePicker.title = dialogs.fileTitles[kind] || "Choose a file"
            filePicker.open()
        }
        function onConfirm(kind, text) {
            question.kind = kind
            question.text = text
            question.open()
        }
        function onMessage(text) { dialogs.show(text) }
    }
    Connections {
        target: typeof launcher !== "undefined" ? launcher : null
        function onMessage(text) { dialogs.show(text) }
    }
    Connections {
        target: typeof settings !== "undefined" ? settings : null
        function onNotice(text) { dialogs.show(text) }
    }

    FolderDialog {
        id: folderPicker
        property string kind
        onAccepted: app.folderChosen(kind, selectedFolder)
    }

    FileDialog {
        id: filePicker
        property string kind
        fileMode: FileDialog.OpenFile
        nameFilters: ["PS4 package (*.pkg)", "All files (*)"]
        onAccepted: app.fileChosen(kind, selectedFile)
    }

    component Box: Dialog {
        id: box
        property alias text: boxText.text
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        background: Rectangle { color: Theme.panel; border.color: Theme.line }
        Text {
            id: boxText
            width: 460
            color: Theme.ink
            font.family: Theme.bodyFont
            font.pixelSize: 15
            wrapMode: Text.WordWrap
        }
    }

    Box {
        id: question
        property string kind
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: app.confirmed(kind)
    }

    Box {
        id: notice
        standardButtons: Dialog.Ok
    }

    // A long action under way (a game .pkg unpacked, the update downloaded, the files checked...): its step and
    // how far it is. The quiet update check at start has no step text and shows nothing.
    Dialog {
        id: busy
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        closePolicy: Popup.NoAutoClose
        visible: app.busy && app.statusText.length > 0
        background: Rectangle { color: Theme.panel; border.color: Theme.line }
        Column {
            width: 460
            spacing: 16
            Text {
                width: parent.width
                text: app.statusText
                color: Theme.ink; font.family: Theme.bodyFont; font.pixelSize: 15
                wrapMode: Text.WordWrap
            }
            Rectangle {
                id: bar
                width: parent.width; height: 6; radius: 3
                color: Theme.line
                Rectangle {
                    id: fill
                    height: parent.height; radius: 3
                    color: Theme.gold
                    // A known length fills from the left; an unknown one sweeps.
                    width: app.progress >= 0 ? bar.width * Math.min(1, app.progress) : bar.width * 0.25
                    SequentialAnimation on x {
                        running: busy.visible && app.progress < 0
                        loops: Animation.Infinite
                        NumberAnimation { from: 0; to: bar.width * 0.75; duration: 900; easing.type: Easing.InOutSine }
                        NumberAnimation { from: bar.width * 0.75; to: 0; duration: 900; easing.type: Easing.InOutSine }
                        onRunningChanged: if (!running) fill.x = 0
                    }
                }
            }
            TextButton {
                visible: app.cancellable
                text: "CANCEL"
                onClicked: app.cancel()
            }
        }
    }
}
