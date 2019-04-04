import pytest  # type: ignore

from snooworld.models._base import _unwrap_listing


def test_listing_unwrapper():
    with pytest.raises(ValueError):
        _unwrap_listing(["a", "b"])
    with pytest.raises(ValueError):
        _unwrap_listing(["a"])

    assert isinstance(_unwrap_listing([]), list)
