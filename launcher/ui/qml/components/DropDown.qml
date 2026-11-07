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
        radius: 3
        color: box.hovered && !box.popup.visible ? Qt.lighter(Theme.panel, 1.15) : Theme.panel
        border.color: box.popup.visible || box.activeFocus ? Theme.gold : (box.hovered ? Theme.dim : Theme.line)
        border.width: 1
    }
    contentItem: Text {
        leftPadding: 14
        rightPadding: 36
        text: box.displayText
        color: Theme.ink
        font: box.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    // A gold chevron that turns while the list is open.
    indicator: Canvas {
        x: box.width - width - 12
        y: (box.height - height) / 2
        width: 12; height: 8
        onPaint: {
            var c = getContext("2d")
            c.reset()
            c.strokeStyle = Theme.gold
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
            text: box.textRole ? row.model[box.textRole] : row.model.modelData
            // The chosen value in gold; the one under the mouse or the keys in ink on a lighter panel.
            color: row.index === box.currentIndex ? Theme.gold : Theme.ink
            font: box.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle { color: row.highlighted ? Qt.lighter(Theme.panel, 1.35) : "transparent" }
    }
    popup: Popup {
        y: box.height + 4
        width: box.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 360)
        padding: 1
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: box.popup.visible ? box.delegateModel : null
            currentIndex: box.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            color: Theme.panel
            border.color: Theme.gold
            border.width: 1
            radius: 3
        }
    }
}
