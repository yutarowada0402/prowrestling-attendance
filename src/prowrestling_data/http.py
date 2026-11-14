"""Shared host locks cover listings, details, robots, redirects and retries."""

import threading
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "prowrestling-attendance/0.1 (+https://github.com/yutarowada0402/prowrestling-attendance)"


class SourceStopped(RuntimeError):
    pass


class Fetcher:
    _locks = {}
    _last = {}

    def __init__(self, interval=3, client=None, sleep=time.sleep, clock=time.monotonic, allowed_hosts=None):
        self.interval = max(3, interval)
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
        self.sleep, self.clock = sleep, clock
        self.robots = None
        self.robots_by_host = {}
        self.allowed_hosts = set(allowed_hosts or ["www.noah.co.jp"])
        self.stopped = False

    def get(self, url, headers=None):
        host = urlsplit(url).netloc
        if self.stopped:
            raise SourceStopped("source already stopped")
        if host not in self.allowed_hosts:
            raise SourceStopped("unexpected host")
        robot = self.robots_by_host.get(host)
        if robot and not robot.can_fetch(USER_AGENT, url):
            self.stopped = True
            raise SourceStopped("robots disallow")
        lock = self._locks.setdefault(host, threading.Lock())
        with lock:
            for attempt in range(4):  # initial request plus at most three retries
                delay = max(0, self.interval - (self.clock() - self._last.get(host, -1e9)))
                self.sleep(delay)
                self._last[host] = self.clock()
                try:
                    r = self.client.get(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
                    if r.status_code == 403 or "captcha" in r.text.lower():
                        self.stopped = True
                        raise SourceStopped(f"HTTP {r.status_code} / CAPTCHA: {url}")
                    if r.is_redirect:
                        # Treat redirects as diagnostic failures: no unthrottled or cross-host requests.
                        raise SourceStopped(
                            f"redirect requires review: {urljoin(url, r.headers.get('location', ''))}"
                        )
                    if r.status_code != 429 and r.status_code < 500:
                        r.raise_for_status()
                        return r
                    r.raise_for_status()
                except (httpx.TransportError, httpx.HTTPStatusError) as e:
                    retryable = isinstance(e, httpx.TransportError) or e.response.status_code in (
                        429,
                        500,
                        502,
                        503,
                        504,
                    )
                    if not retryable or attempt == 3:
                        raise
                    delay = 2**attempt
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                        raw = e.response.headers.get("Retry-After", "")
                        try:
                            delay = max(delay, float(raw))
                        except ValueError:
                            try:
                                delay = max(
                                    delay, (parsedate_to_datetime(raw) - datetime.now(UTC)).total_seconds()
                                )
                            except (ValueError, TypeError):
                                pass
                    self.sleep(delay)

    def check_robots(self, base):
        try:
            r = self.get(base + "/robots.txt")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return "404: no robots directives; not a reuse permission"
            raise
        robot = RobotFileParser()
        robot.parse(r.text.splitlines())
        self.robots = robot
        self.robots_by_host[urlsplit(base).netloc] = robot
        self.interval = max(self.interval, robot.crawl_delay(USER_AGENT) or robot.crawl_delay("*") or 0)
        rate = robot.request_rate(USER_AGENT) or robot.request_rate("*")
        if rate:
            self.interval = max(self.interval, rate.seconds / rate.requests)
        return "200: robots directives applied"
