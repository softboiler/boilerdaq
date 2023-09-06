"""Test hardware and experimental procedures."""

from boilerdaq.daq import Looper


def test_stages(looper: Looper):
    """Test stages."""
    looper.start()
