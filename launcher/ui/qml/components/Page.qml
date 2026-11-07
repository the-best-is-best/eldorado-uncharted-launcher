// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// A screen of the launcher: its title, an optional line under it, and the content below.
import QtQuick
import ".."

Item {
    id: page
    property string title
    property string subtitle
    default property alias content: body.data

    Column {
        id: head
        anchors { left: parent.left; leftMargin: 48; top: parent.top; topMargin: 36 }
        spacing: 6
        Text { text: page.title; color: Theme.ink; font.family: Theme.titleFont; font.pixelSize: 32; font.letterSpacing: Theme.tracking(3) }
        Text { text: page.subtitle; visible: text.length > 0; color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 14 }
    }
    Item {
        id: body
        anchors { left: parent.left; right: parent.right; top: head.bottom; bottom: parent.bottom
                  leftMargin: 48; rightMargin: 48; topMargin: 24; bottomMargin: 24 }
    }
}
