"""Async HTTP fetcher with robots.txt compliance, rate limiting, and retries."""

import asyncio
import logging
import time
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import (
    CONNECT_TIMEOUT,
    MAX_RETRIES,
    READ_TIMEOUT,
    USER_AGENT,
    InstitutionConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    url: str
    status_code: int
    content_type: str
    content: bytes
    final_url: str  # after redirects


class DomainRateLimiter:
    """Enforces minimum interval between requests to the same domain."""

    def __init__(self, min_interval: float = 2.0) -> None:
        self._min_interval = min_interval
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def acquire(self, domain: str) -> None:
        async with self._lock_for(domain):
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            wait = self._min_interval - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request[domain] = time.monotonic()


class RobotsCache:
    """Thread-safe cache for per-domain robots.txt parsers."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, domain: str) -> asyncio.Lock:
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def _fetch_robots(self, robots_url: str) -> urllib.robotparser.RobotFileParser:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            resp = await self._client.get(robots_url, timeout=10.0)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                # If robots.txt is missing, allow everything
                rp.parse([])
        except Exception as exc:
            logger.debug("Could not fetch robots.txt at %s: %s", robots_url, exc)
            rp.parse([])
        return rp

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = urljoin(domain, "/robots.txt")

        async with self._lock_for(domain):
            if domain not in self._parsers:
                self._parsers[domain] = await self._fetch_robots(robots_url)

        return self._parsers[domain].can_fetch(USER_AGENT, url)


class Fetcher:
    """Async HTTP client with rate limiting, robots compliance, and retries."""

    def __init__(self, config: InstitutionConfig) -> None:
        self._config = config
        self._rate_limiter = DomainRateLimiter(
            min_interval=1.0 / config.requests_per_second
        )
        timeout = httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT)
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        self._robots = RobotsCache(self._client)

    async def __aenter__(self) -> "Fetcher":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def fetch(self, url: str) -> Optional[FetchResult]:
        """Fetch a URL, respecting robots.txt and rate limits.

        Returns None if the URL is disallowed or skipped.
        """
        if not await self._robots.can_fetch(url):
            logger.info("robots.txt disallows: %s", url)
            return None

        parsed = urlparse(url)
        domain = parsed.netloc

        await self._rate_limiter.acquire(domain)

        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(
                    (httpx.TimeoutException, httpx.TransportError)
                ),
                stop=stop_after_attempt(MAX_RETRIES),
                wait=wait_exponential(multiplier=2, min=2, max=30),
                reraise=True,
            ):
                with attempt:
                    resp = await self._client.get(url)

            if resp.status_code >= 500:
                logger.warning("5xx from %s: %d", url, resp.status_code)
                return None
            if resp.status_code >= 400:
                logger.debug("4xx from %s: %d", url, resp.status_code)
                return None

            content_type = resp.headers.get("content-type", "").lower().split(";")[0].strip()
            return FetchResult(
                url=url,
                status_code=resp.status_code,
                content_type=content_type,
                content=resp.content,
                final_url=str(resp.url),
            )

        except httpx.TimeoutException:
            logger.warning("Timeout fetching %s", url)
            return None
        except httpx.TransportError as exc:
            logger.warning("Transport error fetching %s: %s", url, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error fetching %s: %s", url, exc)
            return None
