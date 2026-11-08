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
        game: qsTr("Select the Uncharted game folder (the one with eboot.bin and sce_sys)"),
        update: qsTr("Choose the extracted game update 1.02 folder"),
        game_destination: qsTr("Choose where to put the game (about 60 GB)")
    })
    readonly property var fileTitles: ({
        pkg: qsTr("Choose the game update (.pkg)"),
        game_pkg: qsTr("Choose the game (.pkg), not the update")
    })

    function show(text) {
        notice.text = text
        notice.open()
    }

    Connections {
        target: app
        function onPickFolder(kind) {
            folderPicker.kind = kind
            folderPicker.title = dialogs.folderTitles[kind] || qsTr("Choose a folder")
            // The game goes next to its package unless the player picks elsewhere.
            if (kind === "game_destination" && app.pendingPkgFolder !== "")
                folderPicker.currentFolder = app.pendingPkgFolder
            folderPicker.open()
        }
        function onPickFile(kind) {
            filePicker.kind = kind
            filePicker.title = dialogs.fileTitles[kind] || qsTr("Choose a file")
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
        function onAdvise(text) {
            advice.text = text
            advice.open()
        }
        function onCrashed(text) {
            crash.text = text
            crash.open()
        }
    }
    Connections {
        target: typeof settings !== "undefined" ? settings : null
        function onNotice(text) { dialogs.show(text) }
    }
    Connections {
        target: typeof profiles !== "undefined" ? profiles : null
        function onMessage(text) { dialogs.show(text) }
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
        nameFilters: [qsTr("PS4 package (*.pkg)"), qsTr("All files (*)")]
        onAccepted: app.fileChosen(kind, selectedFile)
    }

    component Box: Dialog {
        id: box
        property alias text: boxText.text
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        background: Rectangle { color: Theme.panel; border.color: Theme.glassEdge; radius: Theme.radius }
        palette.button: Theme.panelHigh
        palette.buttonText: Theme.ink
        palette.highlight: Theme.accent
        palette.mid: Theme.panelHigh
        palette.dark: Theme.accentLine
        palette.window: Theme.panel
        palette.windowText: Theme.ink
        padding: 24
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

    // After a slow session (launcher.advise): one step lower quality, only on APPLY (Enter); NOT NOW or Escape
    // leaves the settings as they are.
    Dialog {
        id: advice
        property string text
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        padding: 28
        background: Rectangle { color: Theme.panel; border.color: Theme.accentLine; radius: Theme.radius }
        onOpened: adviceBody.forceActiveFocus()
        function take() { close(); launcher.takeAdvice() }
        Column {
            id: adviceBody
            width: 520
            spacing: 18
            focus: true
            Keys.onReturnPressed: advice.take()
            Keys.onEnterPressed: advice.take()
            Keys.onEscapePressed: advice.close()
            Text {
                width: parent.width
                text: qsTr("Smoother play")
                color: Theme.accent
                font.family: Theme.titleFont
                font.pixelSize: 26
            }
            Rectangle { width: parent.width; height: 1; color: Theme.accentLine }
            Text {
                width: parent.width
                text: advice.text
                color: Theme.ink
                font.family: Theme.bodyFont
                font.pixelSize: 15
                wrapMode: Text.WordWrap
            }
            Row {
                spacing: 14
                layoutDirection: i18n.rtl ? Qt.RightToLeft : Qt.LeftToRight
                GoldButton {
                    width: 180; height: 48
                    text: qsTr("APPLY")
                    onClicked: advice.take()
                }
                TextButton {
                    anchors.verticalCenter: parent.verticalCenter
                    height: 44
                    text: qsTr("NOT NOW")
                    onClicked: advice.close()
                }
            }
        }
    }

    // The game crashed or froze (launcher.crashed): why, then the same game again (it starts from the last save) or
    // the problem report (the logs of this crash in a zip on the Desktop).
    // Enter (or the pad's OK) plays again, Escape closes.
    Dialog {
        id: crash
        property string text
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        padding: 28
        background: Rectangle { color: Theme.panel; border.color: Theme.accentLine; radius: Theme.radius }
        onOpened: crashBody.forceActiveFocus()
        function playAgain() { close(); launcher.play() }
        function report() { close(); app.problemReport() }
        Column {
            id: crashBody
            width: 520
            spacing: 18
            focus: true
            Keys.onReturnPressed: crash.playAgain()
            Keys.onEnterPressed: crash.playAgain()
            Keys.onEscapePressed: crash.close()
            Text {
                width: parent.width
                text: qsTr("The game stopped")
                color: Theme.accent
                font.family: Theme.titleFont
                font.pixelSize: 26
            }
            Rectangle { width: parent.width; height: 1; color: Theme.accentLine }
            Text {
                width: parent.width
                text: crash.text
                color: Theme.ink
                font.family: Theme.bodyFont
                font.pixelSize: 15
                wrapMode: Text.WordWrap
            }
            Row {
                spacing: 14
                layoutDirection: i18n.rtl ? Qt.RightToLeft : Qt.LeftToRight
                GoldButton {
                    width: 210; height: 48
                    text: qsTr("PLAY AGAIN")
                    onClicked: crash.playAgain()
                }
                TextButton {
                    anchors.verticalCenter: parent.verticalCenter
                    height: 44
                    text: qsTr("PROBLEM REPORT")
                    onClicked: crash.report()
                }
                TextButton {
                    anchors.verticalCenter: parent.verticalCenter
                    height: 44
                    text: qsTr("CLOSE")
                    onClicked: crash.close()
                }
            }
        }
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
        background: Rectangle { color: Theme.panel; border.color: Theme.glassEdge; radius: Theme.radius }
        padding: 24
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
                // Arabic: the bar fills from the right.
                transform: Scale { origin.x: bar.width / 2; xScale: i18n.rtl ? -1 : 1 }
                Rectangle {
                    id: fill
                    height: parent.height; radius: 3
                    color: Theme.accent
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
                text: qsTr("CANCEL")
                onClicked: app.cancel()
            }
        }
    }
}
