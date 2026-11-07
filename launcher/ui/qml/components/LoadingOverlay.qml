// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// From PLAY until the game's window is up: a dark layer over the home screen with the game's name, what the start
// is doing (launcher.status), a spinner and STOP. The page shows it while launcher.loading is true; stopArmed says
// a key pressed STOP once and a second press ends the start.
import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: overlay
    property string gameNumber
    property string gameTitle
    property string status
    property bool stopArmed: false
    signal stopRequested()

    color: Qt.rgba(0.04, 0.027, 0.016, 0.86)

    // Nothing under the layer takes clicks while it is up.
    MouseArea { anchors.fill: parent }

    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width - 96, 640)
        spacing: 18

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "UNCHARTED " + overlay.gameNumber
            color: Theme.gold
            font.family: Theme.bodyFont; font.pixelSize: 14; font.letterSpacing: 4
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            text: overlay.gameTitle
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: Theme.ink
            font.family: Theme.titleFont; font.pixelSize: 40
        }
        Item { width: 1; height: 8 }
        BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            running: overlay.visible
            palette.dark: Theme.gold
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            text: overlay.status.length > 0 ? overlay.status : "Starting..."
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            color: Theme.dim
            font.family: Theme.bodyFont; font.pixelSize: 14
        }
        Item { width: 1; height: 12 }
        GoldButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "STOP"
            danger: true
            onClicked: overlay.stopRequested()
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: overlay.stopArmed
            text: "Press again to stop."
            color: Theme.dangerText
            font.family: Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: 1
        }
    }
}
