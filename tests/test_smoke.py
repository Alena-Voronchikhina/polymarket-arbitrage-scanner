"""Package smoke tests."""

from src import __version__


def test_package_version_present() -> None:
    assert __version__
