#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Michelle Raouf
"""Arabic text as the in-game menu draws it: ImGui neither joins letters nor lays text out right to left, so a line
is stored as Arabic presentation forms (the joined shapes, U+FE70..U+FEFF) in display order, left to right, like the
games' own Arabic save titles. tools/make_overlay_i18n.py runs every Arabic translation through visual().

Latin words (key names: Enter, Esc, Delete, (A)...) and numbers keep their own order inside the line. A line too long
for the menu is cut from its right end by bbport_overlay.cpp WrappedText.
"""
import re

# letter: (isolated, final, initial, medial); a letter with two forms joins only the letter before it.
FORMS = {
    'ء': ('ﺀ',),
    'آ': ('ﺁ', 'ﺂ'), 'أ': ('ﺃ', 'ﺄ'), 'ؤ': ('ﺅ', 'ﺆ'), 'إ': ('ﺇ', 'ﺈ'),
    'ئ': ('ﺉ', 'ﺊ', 'ﺋ', 'ﺌ'), 'ا': ('ﺍ', 'ﺎ'),
    'ب': ('ﺏ', 'ﺐ', 'ﺑ', 'ﺒ'), 'ة': ('ﺓ', 'ﺔ'),
    'ت': ('ﺕ', 'ﺖ', 'ﺗ', 'ﺘ'), 'ث': ('ﺙ', 'ﺚ', 'ﺛ', 'ﺜ'),
    'ج': ('ﺝ', 'ﺞ', 'ﺟ', 'ﺠ'), 'ح': ('ﺡ', 'ﺢ', 'ﺣ', 'ﺤ'),
    'خ': ('ﺥ', 'ﺦ', 'ﺧ', 'ﺨ'), 'د': ('ﺩ', 'ﺪ'), 'ذ': ('ﺫ', 'ﺬ'),
    'ر': ('ﺭ', 'ﺮ'), 'ز': ('ﺯ', 'ﺰ'),
    'س': ('ﺱ', 'ﺲ', 'ﺳ', 'ﺴ'), 'ش': ('ﺵ', 'ﺶ', 'ﺷ', 'ﺸ'),
    'ص': ('ﺹ', 'ﺺ', 'ﺻ', 'ﺼ'), 'ض': ('ﺽ', 'ﺾ', 'ﺿ', 'ﻀ'),
    'ط': ('ﻁ', 'ﻂ', 'ﻃ', 'ﻄ'), 'ظ': ('ﻅ', 'ﻆ', 'ﻇ', 'ﻈ'),
    'ع': ('ﻉ', 'ﻊ', 'ﻋ', 'ﻌ'), 'غ': ('ﻍ', 'ﻎ', 'ﻏ', 'ﻐ'),
    'ف': ('ﻑ', 'ﻒ', 'ﻓ', 'ﻔ'), 'ق': ('ﻕ', 'ﻖ', 'ﻗ', 'ﻘ'),
    'ك': ('ﻙ', 'ﻚ', 'ﻛ', 'ﻜ'), 'ل': ('ﻝ', 'ﻞ', 'ﻟ', 'ﻠ'),
    'م': ('ﻡ', 'ﻢ', 'ﻣ', 'ﻤ'), 'ن': ('ﻥ', 'ﻦ', 'ﻧ', 'ﻨ'),
    'ه': ('ﻩ', 'ﻪ', 'ﻫ', 'ﻬ'), 'و': ('ﻭ', 'ﻮ'), 'ى': ('ﻯ', 'ﻰ'),
    'ي': ('ﻱ', 'ﻲ', 'ﻳ', 'ﻴ'),
}
# lam + alef: one shape (isolated, final)
LAM_ALEF = {'آ': ('ﻵ', 'ﻶ'), 'أ': ('ﻷ', 'ﻸ'), 'إ': ('ﻹ', 'ﻺ'), 'ا': ('ﻻ', 'ﻼ')}
MIRROR = {'(': ')', ')': '(', '[': ']', ']': '[', '<': '>', '>': '<'}
# A left-to-right stretch: Latin words and numbers (with brackets, dots, slashes and dashes among them), single
# spaces between them included.
LATIN = re.compile(r"[A-Za-z0-9(][A-Za-z0-9()._/+\-%=]*(?: [A-Za-z0-9(][A-Za-z0-9()._/+\-%=]*)*")


def joins_next(letter):
    return letter in FORMS and len(FORMS[letter]) == 4


def shape(text):
    """The joined shapes, still in reading order."""
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch not in FORMS:
            out.append(ch)
            i += 1
            continue
        before = text[i - 1] if i > 0 else ''
        joined_before = joins_next(before)
        if ch == 'ل' and i + 1 < len(text) and text[i + 1] in LAM_ALEF:
            out.append(LAM_ALEF[text[i + 1]][1 if joined_before else 0])
            i += 2
            continue
        after = text[i + 1] if i + 1 < len(text) else ''
        forms = FORMS[ch]
        joined_after = len(forms) == 4 and after in FORMS
        if len(forms) == 1:  # hamza: joins nothing ("شيء")
            out.append(forms[0])
        elif joined_before and joined_after:
            out.append(forms[3])
        elif joined_before:
            out.append(forms[1])
        elif joined_after:
            out.append(forms[2])
        else:
            out.append(forms[0])
        i += 1
    return ''.join(out)


def visual(text):
    """A right-to-left line in display order: the stretches in reverse order, the Arabic ones reversed (brackets
    mirrored), the Latin ones as they are."""
    if not re.search('[؀-ۿ]', text):
        return text
    if '\n' in text:  # each line on its own (the menu wraps each from its right end: bbport_overlay.cpp WrappedText)
        return '\n'.join(visual(line) for line in text.split('\n'))
    shaped = shape(text)
    runs = []  # (latin, text)
    at = 0
    for match in LATIN.finditer(shaped):
        start, end = match.start(), match.end()
        # A bracket without its pair belongs to the Arabic around it: "(ينتقل إلى savedata-deleted)".
        while shaped[start] == '(' and shaped.count(')', start, end) < shaped.count('(', start, end):
            start += 1
        while shaped[end - 1] == ')' and shaped.count('(', start, end) < shaped.count(')', start, end):
            end -= 1
        if start >= end or start < at:
            continue
        if start > at:
            runs.append((False, shaped[at:start]))
        runs.append((True, shaped[start:end]))
        at = end
    if at < len(shaped):
        runs.append((False, shaped[at:]))
    return ''.join(part if latin else ''.join(MIRROR.get(ch, ch) for ch in reversed(part))
                   for latin, part in reversed(runs))


if __name__ == '__main__':
    import sys
    for line in sys.argv[1:]:
        print(visual(line))
