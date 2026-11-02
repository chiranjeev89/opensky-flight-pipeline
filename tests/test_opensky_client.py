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


# ---- FEATURE-004: airport flights -------------------------------------------

FLIGHT = {
    "icao24": "3c6444",
    "firstSeen": 1761890000,
    "estDepartureAirport": "EDDF",
    "lastSeen": 1761893600,
    "estArrivalAirport": "EGLL",
    "callsign": "DLH900  ",
}


@responses.activate
def test_airport_flights_returns_list_and_sends_params():
    responses.get(f"{API}/flights/departure", json=[FLIGHT])
    out = OpenSkyClient(settings(auth=False)).fetch_airport_flights("EDDF", "departure", 100, 86499)
    assert out == [FLIGHT]
    url = responses.calls[0].request.url
    assert "airport=EDDF" in url and "begin=100" in url and "end=86499" in url


@responses.activate
def test_airport_flights_404_means_no_flights():
    responses.get(f"{API}/flights/arrival", status=404)
    assert OpenSkyClient(settings(auth=False)).fetch_airport_flights("EDDM", "arrival", 0, 86399) == []


@responses.activate
def test_airport_flights_429_raises_credits_exhausted():
    responses.get(f"{API}/flights/arrival", status=429)
    with pytest.raises(CreditsExhausted):
        OpenSkyClient(settings(auth=False)).fetch_airport_flights("EDDM", "arrival", 0, 86399)


def test_airport_flights_rejects_bad_direction_and_long_interval():
    c = OpenSkyClient(settings(auth=False))
    with pytest.raises(ValueError):
        c.fetch_airport_flights("EDDF", "landing", 0, 100)
    with pytest.raises(ValueError):
        c.fetch_airport_flights("EDDF", "arrival", 0, 8 * 86400)  # OpenSky limit is < 7 days


@responses.activate
def test_states_404_is_still_an_error():
    # 404 is only "empty" for airport flights; for /states/all it means a broken URL.
    responses.get(f"{API}/states/all", status=404)
    with pytest.raises(OpenSkyError):
        OpenSkyClient(settings(auth=False)).fetch_states()
