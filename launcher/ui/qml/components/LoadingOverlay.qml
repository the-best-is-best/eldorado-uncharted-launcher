// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// From PLAY until the game's window is up: the same screen the engine draws in the game's window until its first
// picture (engine/gpu/shim/bbport_overlay.cpp LoadingScreen), so the start reads as one screen: the dark ground
// with the game's color glowing at the top, EL DORADO in gold, the game's number in its color, its name, a run of
// its color sliding along a track, what the start is doing (launcher.status) and STOP. The page shows it while
// launcher.loading is true; stopArmed says a key pressed STOP once and a second press ends the start.
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

    gradient: Gradient {
        GradientStop { position: 0.0; color: Theme.baseTop }
        GradientStop { position: 1.0; color: Theme.base }
    }

    // Nothing under the layer takes clicks while it is up.
    MouseArea { anchors.fill: parent }

    // The game's color glowing above the middle (the engine draws the same glow).
    Canvas {
        id: glow
        anchors.fill: parent
        property color tint: Theme.accent
        onTintChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const cx = width / 2, cy = height * 0.30, r = 760 * height / 1080
            const fill = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
            fill.addColorStop(0, Theme.soft(tint, 0.26))
            fill.addColorStop(0.45, Theme.soft(tint, 0.10))
            fill.addColorStop(1, Theme.soft(tint, 0))
            ctx.fillStyle = fill
            ctx.fillRect(0, 0, width, height)
        }
    }

    Column {
        id: middle
        readonly property real s: overlay.height / 1080
        anchors.horizontalCenter: parent.horizontalCenter
        y: overlay.height * 0.40 - 132 * s
        width: Math.min(parent.width - 96, 900)
        spacing: 0

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "EL DORADO"
            color: Theme.gold
            font.family: Theme.strongFont; font.pixelSize: Math.max(13, 20 * middle.s)
            font.letterSpacing: 7 * middle.s
        }
        Item { width: 1; height: 58 * middle.s }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "UNCHARTED " + overlay.gameNumber
            color: Theme.accent
            font.family: Theme.strongFont; font.pixelSize: Math.max(15, 24 * middle.s)
            font.letterSpacing: 6 * middle.s
        }
        Item { width: 1; height: 8 * middle.s }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            text: overlay.gameTitle.toUpperCase()
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: Theme.ink
            font.family: Theme.titleFont; font.pixelSize: Math.max(34, 66 * middle.s)
        }
        Item { width: 1; height: 18 * middle.s }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 56 * middle.s; height: Math.max(2, 3 * middle.s); radius: height / 2
            color: Theme.accent
        }
        Item { width: 1; height: 64 * middle.s }
        // The bar: a rounded run of the game's color sliding along a rounded track, slow at the ends.
        Rectangle {
            id: track
            anchors.horizontalCenter: parent.horizontalCenter
            width: 440 * middle.s; height: Math.max(4, 6 * middle.s); radius: height / 2
            color: Theme.line
            clip: true
            Rectangle {
                id: run
                width: track.width * 0.28; height: track.height; radius: height / 2
                color: Theme.accent
                NumberAnimation on x {
                    running: overlay.visible
                    loops: Animation.Infinite
                    from: -run.width; to: track.width
                    duration: 1667
                    easing.type: Easing.InOutCubic
                }
            }
        }
        Item { width: 1; height: 22 * middle.s }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            width: parent.width
            text: overlay.status.length > 0 ? overlay.status : qsTr("Starting...")
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
            color: Theme.dim
            font.family: Theme.bodyFont; font.pixelSize: Math.max(13, 20 * middle.s)
        }
    }

    // STOP at the bottom, out of the way of the screen the engine takes over.
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 56
        spacing: 10
        GoldButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: qsTr("STOP")
            danger: true
            onClicked: overlay.stopRequested()
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            visible: overlay.stopArmed
            text: qsTr("Press again to stop.")
            color: Theme.dangerText
            font.family: Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(1)
        }
    }
}
