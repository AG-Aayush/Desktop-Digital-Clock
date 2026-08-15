"""Shared test setup.

Qt needs exactly one QApplication per process, and it must exist before any
widget is constructed. Creating it once here and sharing it across all tests
avoids both the "no QApplication" crash and the subtler one from making two.
"""
import os
import sys

# Must be set before Qt loads, so it renders into memory instead of a screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])