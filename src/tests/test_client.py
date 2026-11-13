import tempfile

import pytest
import requests

from biblissima import EmptyResultError, InvalidResponse, PortalClient, RequestFailed

from conftest import FakeResponse, FakeSession


def make(responses, **kw):
    sleeps = []
    clock = {"t": 0.0}
    session = FakeSession(responses)
    client = PortalClient(
        session=session,
        sleep=lambda s: (sleeps.append(s), clock.__setitem__("t", clock["t"] + s)),
        clock=lambda: clock["t"],
        **kw,
    )
    return client, session, sleeps


def test_rql_returns_rows_and_sends_params_and_user_agent():
    client, session, _ = make([FakeResponse(payload=[[1], [2]])], user_agent="ua-test")
    assert client.rql("Any X WHERE X is Manuscript") == [[1], [2]]
    call = session.calls[0]
    assert call["url"] == "https://portail.biblissima.fr/en/view"
    assert call["params"] == {"rql": "Any X WHERE X is Manuscript", "vid": "jsonexport"}
    assert call["headers"]["User-Agent"] == "ua-test"


def test_empty_result_raises_unless_allowed():
    client, _, _ = make([FakeResponse(payload=[]), FakeResponse(payload=[])])
    with pytest.raises(EmptyResultError):
        client.rql("bad query")
    assert client.rql("ok but empty", allow_empty=True) == []


def test_non_list_payload_is_invalid():
    client, _, _ = make([FakeResponse(payload={"a": 1})])
    with pytest.raises(InvalidResponse):
        client.rql("q")


def test_requests_are_throttled():
    client, _, sleeps = make(
        [FakeResponse(payload=[[1]]), FakeResponse(payload=[[2]])], min_interval=1.0
    )
    client.rql("a")
    client.rql("b")
    assert sleeps == [1.0]


def test_retries_server_errors_then_succeeds():
    client, session, sleeps = make(
        [FakeResponse(status=503), FakeResponse(payload=[[1]])], min_interval=0
    )
    assert client.rql("q") == [[1]]
    assert len(session.calls) == 2
    assert 2.0 in sleeps  # backoff ** 1


def test_retries_truncated_json():
    client, session, _ = make(
        [FakeResponse(bad_json=True), FakeResponse(payload=[[1]])], min_interval=0
    )
    assert client.rql("q") == [[1]]
    assert len(session.calls) == 2


def test_retries_connection_errors_and_gives_up():
    err = requests.ConnectionError("boom")
    client, session, _ = make([err, err], min_interval=0, max_retries=1)
    with pytest.raises(RequestFailed):
        client.rql("q")
    assert len(session.calls) == 2


def test_client_error_is_not_retried():
    client, session, _ = make([FakeResponse(status=404)], min_interval=0)
    with pytest.raises(RequestFailed):
        client.rql("q")
    assert len(session.calls) == 1


def test_retry_after_is_honoured():
    client, _, sleeps = make(
        [FakeResponse(status=429, headers={"Retry-After": "7"}), FakeResponse(payload=[[1]])],
        min_interval=0,
    )
    client.rql("q")
    assert 7.0 in sleeps


def test_cache_avoids_second_request():
    with tempfile.TemporaryDirectory() as d:
        client, session, _ = make([FakeResponse(payload=[[1]])], cache_dir=d, min_interval=0)
        assert client.rql("q") == [[1]]
        assert client.rql("q") == [[1]]
        assert len(session.calls) == 1


def test_check_endpoint_returns_count():
    client, _, _ = make([FakeResponse(payload=[[338731]])])
    assert client.check_endpoint() == 338731


def test_check_endpoint_rejects_nonsense():
    client, _, _ = make([FakeResponse(payload=[["x"]])])
    with pytest.raises(InvalidResponse):
        client.check_endpoint()


def test_wikibase_get_entities_params_and_missing():
    from biblissima import WikibaseClient

    payload = {"entities": {"Q1": {"id": "Q1"}, "Q2": {"id": "Q2", "missing": ""}}}
    session = FakeSession([FakeResponse(payload=payload)])
    wb = WikibaseClient(session=session, min_interval=0)
    got = wb.get_entities(["Q1", "Q2", "Q1"], props="labels|claims")
    assert list(got) == ["Q1"]
    call = session.calls[0]
    assert call["url"] == "https://data.biblissima.fr/w/api.php"
    assert call["params"]["ids"] == "Q1|Q2"
    assert call["params"]["action"] == "wbgetentities"
    assert call["params"]["languages"] == "en|fr"


def test_wikibase_rejects_more_than_50_ids_and_errors():
    from biblissima import WikibaseClient

    wb = WikibaseClient(session=FakeSession([FakeResponse(payload={"error": {"code": "x"}})]), min_interval=0)
    with pytest.raises(ValueError):
        wb.get_entities([f"Q{i}" for i in range(51)])
    with pytest.raises(InvalidResponse):
        wb.get_entities(["Q1"])


def test_shared_throttle_spaces_requests_across_clients():
    from biblissima import Throttle, WikibaseClient

    sleeps = []
    clock = {"t": 0.0}
    throttle = Throttle(1.0, sleep=lambda s: (sleeps.append(s), clock.__setitem__("t", clock["t"] + s)), clock=lambda: clock["t"])
    portal = PortalClient(session=FakeSession([FakeResponse(payload=[[1]])]), throttle=throttle)
    wb = WikibaseClient(session=FakeSession([FakeResponse(payload={"entities": {}})]), throttle=throttle)
    portal.rql("q")
    wb.get_entities(["Q1"])
    assert sleeps == [1.0]
