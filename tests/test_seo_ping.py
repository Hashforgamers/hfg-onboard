from unittest import mock

import pytest
import requests

from services import seo_ping


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(seo_ping, "_disabled_logged", False)


def test_missing_secret_makes_no_call(monkeypatch):
    monkeypatch.delenv("SEO_PING_SECRET", raising=False)
    with mock.patch.object(seo_ping.requests, "post") as post:
        assert seo_ping.ping_vendors([1, 2]) is None
    post.assert_not_called()


def test_request_exception_does_not_propagate(monkeypatch):
    monkeypatch.setenv("SEO_PING_SECRET", "s" * 32)
    monkeypatch.delenv("SEO_PING_URL", raising=False)
    with mock.patch.object(seo_ping.requests, "post", side_effect=requests.ConnectionError("down")) as post:
        thread = seo_ping.ping_vendors([3, 3, "4"])
        assert thread is not None
        thread.join(timeout=5)
    post.assert_called_once()
    _, kwargs = post.call_args
    assert post.call_args.args[0] == seo_ping.DEFAULT_SEO_PING_URL
    assert kwargs["json"] == {"vendorIds": [3, 4]}
    assert kwargs["timeout"] == 5
    assert kwargs["headers"]["Authorization"] == "Bearer " + "s" * 32


def test_empty_ids_make_no_call(monkeypatch):
    monkeypatch.setenv("SEO_PING_SECRET", "s" * 32)
    with mock.patch.object(seo_ping.requests, "post") as post:
        assert seo_ping.ping_vendors([]) is None
    post.assert_not_called()
