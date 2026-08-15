"""The clock's four styles, and the settings that drive them."""
import pytest

import desktop_timer as dt


def test_every_template_is_known():
    assert dt.TEMPLATES == ("flip", "digital", "minimal", "terminal")


@pytest.mark.parametrize("template,expected", [
    ("flip", dt.FlipTimeDisplay),
    ("digital", dt.DigitalTimeDisplay),
    ("minimal", dt.MinimalTimeDisplay),
    ("terminal", dt.TerminalTimeDisplay),
])
def test_template_builds_the_right_display(app, template, expected):
    """Choosing a style must produce that style's widget."""
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        clock.template = template
        clock.rebuild_clock()
        assert isinstance(clock.display, expected)
    finally:
        clock.timer.stop()


def test_unknown_template_falls_back_to_flip(app, monkeypatch):
    """A corrupted setting must not crash the app on startup."""
    monkeypatch.setattr(
        dt.QSettings, "value",
        lambda self, key, default=None, type=None: (
            "nonsense" if key == "template" else default
        ),
    )
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        assert clock.template == "flip"
    finally:
        clock.timer.stop()