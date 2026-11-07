// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The launcher's scroll bar: always shown while there is more to scroll, wide enough to grab and drag, in the
// game's color while held or under the mouse. Attach it as ScrollBar.vertical: Scroller {}.
import QtQuick
import QtQuick.Controls
import ".."

ScrollBar {
    id: bar
    policy: size < 1.0 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
    interactive: true
    minimumSize: 0.08
    padding: 2
    implicitWidth: 14
    contentItem: Rectangle {
        implicitWidth: 8
        radius: 4
        color: bar.pressed ? Theme.accent : (bar.hovered ? Theme.accentLine : Theme.line)
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    background: Rectangle {
        implicitWidth: 12
        radius: 6
        color: Qt.rgba(1, 1, 1, 0.03)
    }
}
