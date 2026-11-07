// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The screen of a rail action (update, logs, quit): what it does and one button, so the keys and a controller run
// it like any screen (Enter = accept()). Main.qml's rail also calls run(name) for a click on the action itself.
import QtQuick
import ".."
import "../components"

Page {
    id: page
    property string action: ""

    readonly property var texts: ({
        update: { title: qsTr("UPDATE"), line: app.updateText,
                  body: qsTr("Saves, settings and the shader cache are kept. The launcher closes, installs the update and starts again."),
                  button: qsTr("INSTALL") },
        logs: { title: qsTr("LOGS"), line: qsTr("The engine's log of each start (boot.log), for a problem report."),
                body: qsTr("Opens the folder of the newest boot.log."), button: qsTr("OPEN LOG FOLDER") },
        quit: { title: qsTr("QUIT"),
                line: launcher.running ? qsTr("The game is still running: it closes with the launcher.")
                                       : qsTr("Close El Dorado."),
                body: "", button: qsTr("QUIT") }
    })
    readonly property var shown: texts[action] || { title: "", line: "", body: "", button: "" }
    title: shown.title
    subtitle: shown.line

    function accept() { run(action) }
    function run(name) {
        if (name === "update") app.installUpdate()
        else if (name === "logs") app.openFolder("logs")
        else if (name === "quit") app.quit()
    }

    Column {
        width: Math.min(parent.width, 640)
        spacing: 24
        Text {
            width: parent.width
            visible: text.length > 0
            text: page.shown.body
            color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 15
            wrapMode: Text.WordWrap
        }
        TextButton {
            text: page.shown.button
            danger: page.action === "quit"
            onClicked: page.run(page.action)
        }
        KeyHint { entries: [{ action: "accept", text: page.shown.button }] }
    }
}
