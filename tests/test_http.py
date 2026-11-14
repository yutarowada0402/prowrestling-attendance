import httpx
import pytest

from prowrestling_data.http import Fetcher, SourceStopped


def client_for(statuses, headers=None):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(statuses[min(len(calls) - 1, len(statuses) - 1)], text="ok", headers=headers)

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def test_403_stops_without_retry():
    client, calls = client_for([403])
    fetcher = Fetcher(client=client, sleep=lambda _: None)
    with pytest.raises(SourceStopped):
        fetcher.get("https://www.noah.co.jp/result/")
    with pytest.raises(SourceStopped):
        fetcher.get("https://www.noah.co.jp/schedule/1/")
    assert len(calls) == 1


def test_429_retry_after_and_shared_limiter():
    client, calls = client_for([429, 200], {"Retry-After": "7"})
    now, sleeps = [0], []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    Fetcher._last.clear()
    f = Fetcher(client=client, sleep=sleep, clock=lambda: now[0])
    f.get("https://www.noah.co.jp/result/")
    f.get("https://www.noah.co.jp/schedule/1/")
    assert len(calls) == 3
    assert 7 in sleeps and sleeps[-1] >= 3
    assert calls[0].headers["User-Agent"].startswith("prowrestling-attendance/")


def test_max_three_retries():
    client, calls = client_for([503])
    with pytest.raises(httpx.HTTPStatusError):
        Fetcher(client=client, sleep=lambda _: None).get("https://www.noah.co.jp/result/")
    assert len(calls) == 4
