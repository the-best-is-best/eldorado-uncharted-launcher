// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The home screen: the three games over the selected one's picture (its latest save, its own art or El Dorado's
// map, drawn by ui/background.py), where the player left off (CONTINUE), PLAY/STOP, the expedition log (the latest
// saves of all three games) and the key hints. Keyboard: Up/Down choose, Enter plays (Main.qml routes keys).
import QtQuick
import QtQuick.Window
import ".."
import "../components"

Item {
    id: home
    readonly property var game: launcher.games[launcher.selectedIndex]
    // The log needs room under the games; a short window shows the games alone, and a small one draws them tighter.
    readonly property bool roomForLog: height >= 640 && launcher.logRows.length > 0
    readonly property bool compact: height < 640 || width < 900
    // STOP by key takes two presses: one press right after PLAY (Enter twice, A twice) must not end the start.
    property bool stopArmed: false
    Timer { id: stopArming; interval: 3000; onTriggered: home.stopArmed = false }

    function up() { launcher.select(Math.max(0, launcher.selectedIndex - 1)) }
    function down() { launcher.select(Math.min(launcher.games.length - 1, launcher.selectedIndex + 1)) }
    function accept() {
        if (!launcher.running) { stopArmed = false; launcher.play(); return }
        if (stopArmed) { stopArmed = false; launcher.stop(); return }
        stopArmed = true
        stopArming.restart()
    }

    // A save deleted or restored on the Saves screen changes the picture and the log.
    onVisibleChanged: if (visible) launcher.refresh()

    // The background: two pictures, the new one fades in over the old (the address changes with the game and
    // with its latest save; the size follows the window).
    Item {
        id: backdrop
        anchors.fill: parent
        readonly property string wanted: width > 0 && height > 0 ? launcher.backgroundSource : ""
        property Item shown: first

        onWantedChanged: {
            if (wanted === "")
                return
            var next = shown === first ? second : first
            next.source = wanted
            if (next.status === Image.Ready)
                arrived(next)
        }
        function arrived(image) {
            if (image.source.toString() !== wanted)
                return  // an older request
            shown = image
            image.opacity = 1
            if (image === first) second.opacity = 0; else first.opacity = 0
        }

        component Backdrop: Image {
            anchors.fill: parent
            sourceSize: Qt.size(Math.round(width * Screen.devicePixelRatio), Math.round(height * Screen.devicePixelRatio))
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            opacity: 0
            Behavior on opacity { NumberAnimation { duration: 320 } }
            onStatusChanged: if (status === Image.Ready) backdrop.arrived(this)
        }
        Backdrop { id: first }
        Backdrop { id: second }
    }

    // A shade over the picture, deepest behind the games and at the foot, so every line reads on any picture.
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: Qt.rgba(0.03, 0.035, 0.045, i18n.rtl ? 0.2 : 0.72) }
            GradientStop { position: 0.5; color: Qt.rgba(0.03, 0.035, 0.045, 0.3) }
            GradientStop { position: 1.0; color: Qt.rgba(0.03, 0.035, 0.045, i18n.rtl ? 0.72 : 0.2) }
        }
    }
    Rectangle {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
        height: parent.height * 0.5
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: Qt.rgba(0.03, 0.035, 0.045, 0.85) }
        }
    }

    // The games and the selected one, above the log.
    Item {
        id: stage
        anchors { top: parent.top; left: parent.left; right: parent.right; bottom: home.roomForLog ? log.top : hints.top }

        Column {
            id: cards
            anchors { left: parent.left; leftMargin: 48; verticalCenter: parent.verticalCenter }
            spacing: 14
            Repeater {
                model: launcher.games
                GameCard {
                    game: modelData
                    width: home.compact ? 300 : 360
                    height: home.compact ? 84 : 96
                    selected: index === launcher.selectedIndex
                    enabled: !launcher.running
                    onClicked: launcher.select(index)
                    onDoubleClicked: { launcher.select(index); launcher.play() }
                }
            }
        }

        // The chosen game on a glass panel.
        Rectangle {
            id: infoPanel
            anchors { left: cards.right; leftMargin: home.compact ? 36 : 48; right: parent.right; rightMargin: 40; verticalCenter: parent.verticalCenter }
            height: info.implicitHeight + 2 * info.anchors.margins
            radius: Theme.radius + 4
            color: Theme.glass
            border.color: Theme.glassEdge
        }
        Column {
            id: info
            anchors { fill: infoPanel; margins: home.compact ? 22 : 30 }
            spacing: home.compact ? 6 : 10

            // The game's number on a chip of its color.
            Rectangle {
                width: chip.implicitWidth + 24; height: 26; radius: 13
                color: Theme.accentSoft
                border.color: Theme.accentLine
                Text {
                    id: chip
                    anchors.centerIn: parent
                    text: "UNCHARTED " + home.game.number
                    color: Theme.accent; font.family: Theme.strongFont; font.pixelSize: 12; font.letterSpacing: Theme.tracking(3)
                }
            }
            Text {
                width: parent.width
                text: home.game.title
                color: Theme.ink; font.family: Theme.titleFont; font.pixelSize: home.compact ? 32 : 44
                wrapMode: Text.WordWrap
                style: Text.Raised; styleColor: Qt.rgba(0, 0, 0, 0.65)
            }
            Row {
                spacing: 12
                Rectangle { anchors.verticalCenter: parent.verticalCenter; width: 28; height: 2; radius: 1; color: Theme.accent }
                Text { anchors.verticalCenter: parent.verticalCenter; text: home.game.place; color: Theme.accent; font.family: Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(3) }
            }
            Text {
                width: parent.width
                text: qsTr("%1 played").arg(home.game.playTime) + "   ·   " + home.game.lastPlayed
                      + (home.game.fps > 0 ? "   ·   " + qsTr("%1 FPS average").arg(home.game.fps) : "")
                      + (trophies.percents[home.game.key] >= 0 ? "   ·   " + qsTr("trophies %1%").arg(trophies.percents[home.game.key]) : "")
                color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 14
                style: Text.Raised; styleColor: Qt.rgba(0, 0, 0, 0.6)
                elide: Text.ElideRight
            }
            Item { width: 1; height: home.compact ? 4 : 10 }

            // Where the player left off. Arabic shown as the game stored it runs from the sentence's end to its
            // start: it is cut at the left (the chapter's name is at the right) and kept on one line (a second
            // line would hold the start).
            Text {
                visible: home.game.hasSave
                text: qsTr("CONTINUE")
                color: Theme.faint; font.family: Theme.strongFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(3)
            }
            Text {
                width: parent.width * 0.85
                visible: home.game.hasSave
                text: launcher.continueTitle
                color: Theme.ink; font.family: Theme.titleFont; font.pixelSize: home.compact ? 18 : 22
                horizontalAlignment: Text.AlignLeft
                // Arabic shown as stored is one line cut at its left end (Qt cuts the left only on an unwrapped line;
                // wrapped, the sentence's start would drop off unseen).
                wrapMode: launcher.continueBackwards ? Text.NoWrap : Text.WordWrap
                maximumLineCount: home.compact || launcher.continueBackwards ? 1 : 2
                elide: launcher.continueBackwards ? Text.ElideLeft : Text.ElideRight
                style: Text.Raised; styleColor: Qt.rgba(0, 0, 0, 0.65)
            }
            Text {
                width: parent.width * 0.9
                text: launcher.continueText
                color: home.game.hasSave ? Theme.dim : Theme.faint
                font.family: home.game.hasSave ? Theme.bodyFont : Theme.titleFont; font.pixelSize: home.game.hasSave ? 14 : 17
                horizontalAlignment: Text.AlignLeft
                wrapMode: Text.WordWrap
                maximumLineCount: 2  // the save's own detail, then when it was made
                elide: Text.ElideRight
                style: Text.Raised; styleColor: Qt.rgba(0, 0, 0, 0.6)
            }
            Item { width: 1; height: home.compact ? 6 : 14 }

            GoldButton {
                text: launcher.running ? qsTr("STOP") : qsTr("PLAY")
                danger: launcher.running
                onClicked: home.accept()
            }
            Text {
                width: parent.width
                text: launcher.status
                visible: text.length > 0
                color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 13
                elide: Text.ElideRight
            }
        }
    }

    // The expedition log: the latest saves of all three games, newest first; one opens its game.
    Column {
        id: log
        anchors { left: parent.left; leftMargin: 48; right: parent.right; rightMargin: 48; bottom: hints.top; bottomMargin: 22 }
        visible: home.roomForLog
        spacing: 10
        readonly property int tile: Math.max(100, Math.min(176, Math.floor((width - 4 * 14) / 5)))

        Text { text: qsTr("EXPEDITION LOG"); color: Theme.dim; font.family: Theme.strongFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(3) }
        Row {
            spacing: 14
            Repeater {
                model: launcher.logRows
                Item {
                    id: tile
                    readonly property color tone: Theme.accentOf(modelData.game)
                    readonly property bool current: modelData.game === home.game.key
                    width: log.tile
                    height: plate.height + 42
                    Rectangle {
                        id: plate
                        width: log.tile
                        height: Math.round(log.tile * 9 / 16)
                        y: tileArea.containsMouse && tileArea.enabled ? -3 : 0
                        radius: Theme.radiusSmall
                        color: Theme.panel
                        border.width: tile.current ? 2 : 1
                        border.color: tile.current ? tile.tone : Theme.glassEdge
                        Behavior on y { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
                        Behavior on border.color { ColorAnimation { duration: Theme.slow } }
                        Image {
                            anchors { fill: parent; margins: 3 }
                            source: modelData.picture
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            sourceSize.width: 352
                            clip: true
                        }
                        Rectangle {
                            x: 8; y: 8; width: 22; height: 22; radius: 11
                            color: tile.tone
                            Text { anchors.centerIn: parent; text: modelData.number; color: Theme.accentInk; font.family: Theme.strongFont; font.pixelSize: 12 }
                        }
                    }
                    Text {
                        anchors { top: plate.bottom; topMargin: 6 }
                        width: parent.width
                        text: modelData.title
                        color: Theme.dim; font.family: Theme.titleFont; font.pixelSize: 13
                        horizontalAlignment: Text.AlignLeft
                        elide: modelData.backwards ? Text.ElideLeft : Text.ElideRight
                    }
                    Text {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        text: modelData.when
                        color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(1)
                        elide: Text.ElideRight
                    }
                    MouseArea {
                        id: tileArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !launcher.running
                        cursorShape: Qt.PointingHandCursor
                        onClicked: launcher.selectGame(modelData.game)
                    }
                }
            }
        }
    }

    // The screens' keys are on the rail.
    KeyHint {
        id: hints
        anchors { left: parent.left; leftMargin: 48; bottom: parent.bottom; bottomMargin: 22 }
        entries: [
            { action: "choose", text: qsTr("CHOOSE") },
            { action: "accept", text: launcher.running ? qsTr("STOP (TWICE)") : qsTr("PLAY") }
        ]
    }

    // From PLAY until the game's window is up (the launcher hides itself then).
    LoadingOverlay {
        anchors.fill: parent
        visible: launcher.loading
        gameNumber: home.game.number
        gameTitle: home.game.title
        status: launcher.status
        stopArmed: home.stopArmed
        onStopRequested: { home.stopArmed = false; launcher.stop() }
    }
}
