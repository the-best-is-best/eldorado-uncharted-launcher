// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A choice between a few values shown side by side (the chosen one filled gold).
// options: [{value: "...", label: "..."}]; current: the chosen value; picked(value) when the player clicks another.
import QtQuick
import ".."

Row {
    id: segmented
    property var options: []
    property string current
    signal picked(string value)
    spacing: 0

    Repeater {
        model: segmented.options
        Rectangle {
            readonly property bool chosen: modelData.value === segmented.current
            width: Math.max(150, label.implicitWidth + 36)
            height: 36
            color: chosen ? Theme.gold : (area.containsMouse ? Theme.panel : "transparent")
            border.color: chosen ? Theme.gold : Theme.line
            border.width: 1
            Text {
                id: label
                anchors.centerIn: parent
                text: modelData.label
                color: parent.chosen ? Theme.base : Theme.dim
                font.family: Theme.bodyFont; font.pixelSize: 12; font.letterSpacing: 2
            }
            MouseArea {
                id: area
                anchors.fill: parent
                hoverEnabled: true
                onClicked: if (!parent.chosen) segmented.picked(modelData.value)
            }
        }
    }
}
