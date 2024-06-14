"""Test hardware and experimental procedures."""

import pytest

from boilerdaq.daq import Looper


@pytest.mark.slow()
def test_stages(looper: Looper):
    """Test stages."""
    looper.start()
