// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The launcher's drop-down list, drawn in El Dorado's colors (the Basic style's grey box and arrows replaced).
// Use it as a ComboBox: model, textRole, currentIndex, onActivated.
import QtQuick
import QtQuick.Controls
import ".."

ComboBox {
    id: box
    height: 40
    font.family: Theme.bodyFont
    font.pixelSize: 14

    background: Rectangle {
        radius: Theme.radiusSmall
        color: box.hovered && !box.popup.visible ? Theme.panelHigh : Theme.panel
        border.color: box.popup.visible || box.activeFocus ? Theme.accent : (box.hovered ? Theme.accentLine : Theme.line)
        border.width: 1
        Behavior on color { ColorAnimation { duration: Theme.fast } }
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    }
    contentItem: Text {
        leftPadding: box.mirrored ? 36 : 14
        rightPadding: box.mirrored ? 14 : 36
        text: box.displayText
        color: Theme.ink
        font: box.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    // A chevron in the game's color that turns while the list is open.
    indicator: Canvas {
        id: chevron
        property color stroke: Theme.accent
        onStrokeChanged: requestPaint()
        x: box.mirrored ? 12 : box.width - width - 12
        y: (box.height - height) / 2
        width: 12; height: 8
        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.strokeStyle = chevron.stroke
            c.lineWidth = 1.6
            c.lineCap = "square"
            c.beginPath(); c.moveTo(1, 1); c.lineTo(width / 2, height - 1); c.lineTo(width - 1, 1); c.stroke()
        }
        rotation: box.popup.visible ? 180 : 0
        Behavior on rotation { NumberAnimation { duration: 120 } }
    }
    delegate: ItemDelegate {
        id: row
        required property var model
        required property int index
        width: box.width
        height: 36
        highlighted: box.highlightedIndex === index
        contentItem: Text {
            leftPadding: 14
            rightPadding: 14
            text: box.textRole ? row.model[box.textRole] : row.model.modelData
            // The chosen value in the game's color; the one under the mouse or the keys in ink on a lighter panel.
            color: row.index === box.currentIndex ? Theme.accent : Theme.ink
            font: box.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            anchors { fill: parent; leftMargin: 4; rightMargin: 4; topMargin: 1; bottomMargin: 1 }
            radius: 6
            color: row.highlighted ? Theme.accentSoft : "transparent"
        }
    }
    popup: Popup {
        y: box.height + 4
        width: box.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 360)
        padding: 4
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: box.popup.visible ? box.delegateModel : null
            currentIndex: box.highlightedIndex
            ScrollBar.vertical: Scroller {}
        }
        background: Rectangle {
            color: Theme.panel
            border.color: Theme.accentLine
            border.width: 1
            radius: Theme.radiusSmall
        }
    }
}
