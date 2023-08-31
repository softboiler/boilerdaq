"""Test hardware and experimental procedures."""

from boilerdaq import Looper


def test_stages(looper: Looper):
    """Test stages."""
    looper.start()
