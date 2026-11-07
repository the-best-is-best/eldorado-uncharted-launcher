// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The top of the Controls tab: whose keys and buttons the list below shows. ALL GAMES is the one set every game
// uses; a game's tab shows what that game uses, and a key changed there is that game's own (marked ●) while the
// rest keeps following ALL GAMES. One plain sentence says what the current tab means.
// row: {scope: "all" | game key, games: [{key, name, ownCount}], ownText: "Melee and Reload" (the game's own
//       items, "" when none), ownNote: "Uncharted 2 has 2 keys of its own." (for ALL GAMES, "" when none)}
// Signals: pick(scope), dropOwn() (the game follows ALL GAMES again), makeShared() (its keys become ALL GAMES').
import QtQuick
import ".."

Column {
    id: scope
    property var row: ({})
    signal pick(string scope)
    signal dropOwn()
    signal makeShared()
    width: parent ? parent.width : 600
    spacing: 10

    readonly property var game: {
        var list = row.games || []
        for (var i = 0; i < list.length; i++) if (list[i].key === row.scope) return list[i]
        return null
    }
    readonly property bool hasOwn: game !== null && (game.ownCount || 0) > 0

    function options() {
        var list = [{ value: "all", label: "ALL GAMES" }]
        var games = row.games || []
        for (var i = 0; i < games.length; i++)
            list.push({ value: games[i].key, label: games[i].name.toUpperCase() + ((games[i].ownCount || 0) > 0 ? "  ●" : "") })
        return list
    }

    function sentence() {
        if (row.scope === "all")
            return "Every game uses these keys." + (row.ownNote ? "  " + row.ownNote : "")
        var name = game ? game.name : "This game"
        if (!hasOwn)
            return name + " uses the ALL GAMES keys. Change a key here and it becomes " + name + "'s own; every other key keeps following ALL GAMES."
        return name + " has its own: " + row.ownText + " (marked ●). Everything else follows ALL GAMES."
    }

    Text {
        text: "THESE KEYS AND BUTTONS ARE FOR"
        color: Theme.gold; font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: 3
    }
    Segmented {
        options: scope.options()
        current: scope.row.scope || "all"
        onPicked: (value) => scope.pick(value)
    }
    Text {
        width: parent.width
        text: scope.sentence()
        color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 13
        wrapMode: Text.WordWrap
    }
    Row {
        visible: scope.hasOwn
        spacing: 10
        TextButton { text: "USE THE ALL GAMES KEYS AGAIN"; onClicked: scope.dropOwn() }
        TextButton { text: "MAKE THESE THE ALL GAMES KEYS"; onClicked: scope.makeShared() }
    }
    Rectangle { width: parent.width; height: 1; color: Theme.line }
}
