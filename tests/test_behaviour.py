"""Behaviour that has broken before, so it stays fixed."""
from PyQt6.QtCore import QPoint

import desktop_timer as dt


def test_clamp_keeps_an_onscreen_position(app):
    """A sane position should be returned untouched."""
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        wanted = QPoint(120, 120)
        assert clock.clamp_to_screen(wanted) == wanted
    finally:
        clock.timer.stop()


def test_clamp_rescues_an_offscreen_position(app):
    """A position on a monitor that no longer exists must come back.

    This is a real bug that happened: unplug the second monitor and the
    clock reappeared somewhere unreachable.
    """
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        lost = QPoint(-20000, -20000)
        assert clock.clamp_to_screen(lost) != lost
    finally:
        clock.timer.stop()


def test_am_pm_marker_can_be_cleared(app):
    """Switching 12h -> 24h must not leave 'PM' stuck on the first digit.

    Another real bug: set_am_pm only ever set the flag true.
    """
    digit = dt.FlipDigit()
    digit.set_am_pm("PM")
    assert digit.show_am_pm is True

    digit.clear_am_pm()
    assert digit.show_am_pm is False
    assert digit.am_pm_text == ""


def test_font_selection_always_returns_a_known_family(app):
    """The font picker must always yield a usable name.

    Deliberately not asserting the font is *installed*: under the offscreen
    platform Qt reports an empty font database, so that check passes on a
    desktop and fails in CI. Assert the contract instead -- we always return
    one of our listed preferences, falling back to Arial.
    """
    family = dt.clock_font_family()
    assert family
    assert family in dt.FONT_PREFERENCES