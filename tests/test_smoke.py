"""Minimal import smoke test for the scanner package."""

from src import __version__


def test_package_version_present() -> None:
    assert isinstance(__version__, str)
    assert __version__
