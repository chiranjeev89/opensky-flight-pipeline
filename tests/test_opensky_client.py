"""Client behaviour under success and failure, with HTTP mocked (no credits spent)."""

import pytest
import responses

from flightpipe import opensky_client
from flightpipe.config import Settings
from flightpipe.opensky_client import CreditsExhausted, OpenSkyClient, OpenSkyError

API = "https://opensky.test/api"
TOKEN = "https://auth.test/token"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(opensky_client.time, "sleep", lambda s: None)


def settings(auth=True):
    return Settings(
        opensky_client_id="id" if auth else None,
        opensky_client_secret="secret" if auth else None,
        opensky_api_url=API,
        opensky_token_url=TOKEN,
    )


@responses.activate
def test_fetch_uses_bearer_token_and_bbox():
    responses.post(TOKEN, json={"access_token": "tok", "expires_in": 1800})
    responses.get(
        f"{API}/states/all", json={"time": 1, "states": []}, headers={"X-Rate-Limit-Remaining": "3998"}
    )
    c = OpenSkyClient(settings())
    assert c.fetch_states() == {"time": 1, "states": []}
    call = responses.calls[1].request
    assert call.headers["Authorization"] == "Bearer tok"
    assert "lamin=47.27" in call.url
    assert c.last_credits_remaining == 3998


@responses.activate
def test_token_is_cached_between_calls():
    responses.post(TOKEN, json={"access_token": "tok", "expires_in": 1800})
    responses.get(f"{API}/states/all", json={"time": 1, "states": []})
    c = OpenSkyClient(settings())
    c.fetch_states()
    c.fetch_states()
    assert sum(1 for x in responses.calls if x.request.url == TOKEN) == 1


@responses.activate
def test_429_raises_credits_exhausted_without_retry():
    responses.post(TOKEN, json={"access_token": "tok", "expires_in": 1800})
    responses.get(f"{API}/states/all", status=429)
    with pytest.raises(CreditsExhausted):
        OpenSkyClient(settings()).fetch_states()
    assert sum(1 for x in responses.calls if "states" in x.request.url) == 1


@responses.activate
def test_5xx_is_retried_then_succeeds():
    responses.get(f"{API}/states/all", status=503)
    responses.get(f"{API}/states/all", json={"time": 2, "states": None})
    assert OpenSkyClient(settings(auth=False)).fetch_states()["time"] == 2


@responses.activate
def test_5xx_gives_up_after_max_retries():
    for _ in range(3):
        responses.get(f"{API}/states/all", status=502)
    with pytest.raises(OpenSkyError):
        OpenSkyClient(settings(auth=False)).fetch_states()


@responses.activate
def test_401_refreshes_token_once():
    responses.post(TOKEN, json={"access_token": "old", "expires_in": 1800})
    responses.post(TOKEN, json={"access_token": "new", "expires_in": 1800})
    responses.get(f"{API}/states/all", status=401)
    responses.get(f"{API}/states/all", json={"time": 3, "states": []})
    assert OpenSkyClient(settings()).fetch_states()["time"] == 3
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer new"


@responses.activate
def test_token_failure_does_not_leak_secret():
    responses.post(TOKEN, status=400, body="client_secret=secret invalid")
    with pytest.raises(OpenSkyError) as e:
        OpenSkyClient(settings()).fetch_states()
    assert "secret" not in str(e.value)
