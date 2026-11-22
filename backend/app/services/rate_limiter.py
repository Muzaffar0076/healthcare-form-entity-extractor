"""
Rate limiting service for authentication, extraction, and sensitive endpoints.

Provides:
- In-memory thread-safe sliding window rate limiting for single-process deployments.
- IP-based rate limiting for public entity extraction (computation DoS protection).
- IP-based rate limiting for registration and login endpoints.
- Account-based temporary cooldowns (avoiding permanent lockouts or lockout DoS abuse).
- Automatic event history clearance on cooldown trigger/expiry.
- Strict client IP resolution with TRUSTED_PROXY_IPS validation.
- Clean HTTP 429 exceptions with Retry-After headers.
"""

from collections import defaultdict
from datetime import datetime, timezone
import ipaddress
import os
import threading
from typing import Optional

from fastapi import HTTPException, Request, status

# Configuration defaults
DEFAULT_REGISTRATION_LIMIT = int(os.getenv("RATE_LIMIT_REGISTER_PER_MIN", "10"))
DEFAULT_LOGIN_IP_LIMIT = int(os.getenv("RATE_LIMIT_LOGIN_IP_PER_MIN", "15"))
DEFAULT_ACCOUNT_FAIL_LIMIT = int(os.getenv("RATE_LIMIT_ACCOUNT_FAIL_LIMIT", "5"))
DEFAULT_ACCOUNT_COOLDOWN_SECS = int(os.getenv("RATE_LIMIT_ACCOUNT_COOLDOWN_SECS", "60"))  # 60s cooldown
DEFAULT_EXTRACT_LIMIT = int(os.getenv("RATE_LIMIT_EXTRACT_PER_MIN", "30"))
DEFAULT_EXTRACT_WINDOW_SECS = int(os.getenv("RATE_LIMIT_EXTRACT_WINDOW_SECS", "60"))


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # key -> list of UTC POSIX timestamps
        self._events: dict[str, list[float]] = defaultdict(list)
        # key -> cooldown end timestamp (POSIX float)
        self._cooldowns: dict[str, float] = {}

    def _now(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    def check_and_record(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if an event is allowed under sliding window. Records the event if allowed.
        Returns:
            (is_allowed, retry_after_seconds)
        """
        now = self._now()
        cutoff = now - window_seconds

        with self._lock:
            # Check active cooldown
            if key in self._cooldowns:
                cooldown_until = self._cooldowns[key]
                if now < cooldown_until:
                    retry_after = max(1, int(cooldown_until - now))
                    return False, retry_after
                else:
                    del self._cooldowns[key]

            # Prune old timestamps
            timestamps = [t for t in self._events[key] if t > cutoff]
            self._events[key] = timestamps

            if len(timestamps) >= max_requests:
                earliest = timestamps[0]
                retry_after = max(1, int(earliest + window_seconds - now))
                return False, retry_after

            # Record this event
            self._events[key].append(now)
            return True, 0

    def record_failure(
        self,
        account_key: str,
        max_failures: int = DEFAULT_ACCOUNT_FAIL_LIMIT,
        cooldown_seconds: int = DEFAULT_ACCOUNT_COOLDOWN_SECS,
    ) -> None:
        """
        Record a failed attempt for an account. Triggers a temporary cooldown if threshold reached.
        Clears the attempt history so the account starts with a fresh failure quota after cooldown.
        """
        now = self._now()
        with self._lock:
            timestamps = [t for t in self._events[account_key] if t > (now - cooldown_seconds)]
            timestamps.append(now)
            self._events[account_key] = timestamps

            if len(timestamps) >= max_failures:
                self._cooldowns[account_key] = now + cooldown_seconds
                self._events[account_key] = []

    def reset_account(self, account_key: str) -> None:
        """
        Reset failures and cooldowns for an account upon successful login.
        """
        with self._lock:
            self._events.pop(account_key, None)
            self._cooldowns.pop(account_key, None)

    def is_account_in_cooldown(self, account_key: str) -> tuple[bool, int]:
        """
        Check whether an account is currently in cooldown.
        Cleans up expired cooldowns safely.
        """
        now = self._now()
        with self._lock:
            if account_key in self._cooldowns:
                cooldown_until = self._cooldowns[account_key]
                if now < cooldown_until:
                    retry_after = max(1, int(cooldown_until - now))
                    return True, retry_after
                else:
                    del self._cooldowns[account_key]
                    self._events[account_key] = []
            return False, 0

    def reset_all(self) -> None:
        """Reset all tracked rate limit events and cooldowns (for test isolation)."""
        with self._lock:
            self._events.clear()
            self._cooldowns.clear()


# Singleton rate limiter instance
_rate_limiter = InMemoryRateLimiter()


def reset_rate_limiter() -> None:
    """Reset the global rate limiter state."""
    _rate_limiter.reset_all()


def is_trusted_proxy(ip_str: str) -> bool:
    """
    Check if a connecting IP matches configured trusted reverse proxies.
    TRUSTED_PROXY_IPS supports comma-separated hostnames, IPv4/IPv6 addresses, and CIDR networks.
    """
    raw_proxies = os.getenv("TRUSTED_PROXY_IPS", "").strip()
    if not raw_proxies:
        return False

    trusted_entries = [entry.strip() for entry in raw_proxies.split(",") if entry.strip()]

    # Fast path: exact string match (supports hostnames like "localhost", "testclient")
    if ip_str in trusted_entries:
        return True

    try:
        candidate = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for entry in trusted_entries:
        try:
            if "/" in entry:
                network = ipaddress.ip_network(entry, strict=False)
                if candidate in network:
                    return True
            else:
                if candidate == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue

    return False


def get_client_ip(request: Request) -> str:
    """
    Extract and validate client IP address.

    Security controls:
    - Never trusts X-Forwarded-For unless direct client IP is a configured trusted proxy.
    - Validates forwarded IP using Python's ipaddress module.
    - Safely falls back to request.client.host if untrusted, missing, or malformed.
    """
    direct_ip = request.client.host if (request.client and request.client.host) else "127.0.0.1"

    # Only inspect X-Forwarded-For if the direct connection originates from a trusted proxy
    if not is_trusted_proxy(direct_ip):
        return direct_ip

    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if not forwarded:
        return direct_ip

    # In standard proxy setups, the original client is the leftmost IP
    raw_ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    if not raw_ips:
        return direct_ip

    candidate = raw_ips[0]
    try:
        validated = ipaddress.ip_address(candidate)
        return str(validated)
    except ValueError:
        # Malformed IP address: safely fallback to direct peer IP
        return direct_ip


def check_extraction_rate_limit(request: Request) -> None:
    """
    Enforce rate limits on public entity extraction per validated client IP.
    Protects against computational denial of service from unthrottled ML inference.
    Does NOT require authentication or store healthcare text.
    """
    ip = get_client_ip(request)
    key = f"rate:extract:ip:{ip}"
    allowed, retry_after = _rate_limiter.check_and_record(
        key=key,
        max_requests=DEFAULT_EXTRACT_LIMIT,
        window_seconds=DEFAULT_EXTRACT_WINDOW_SECS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many extraction requests. Please try again after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def check_registration_rate_limit(request: Request) -> None:
    """
    Enforce rate limits on user registration per IP.
    """
    ip = get_client_ip(request)
    key = f"rate:reg:ip:{ip}"
    allowed, retry_after = _rate_limiter.check_and_record(
        key=key,
        max_requests=DEFAULT_REGISTRATION_LIMIT,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration requests. Please try again after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


def check_login_rate_limit(request: Request, email: str) -> None:
    """
    Enforce rate limits on login:
    1. IP-level limit to prevent brute-force attacks across accounts.
    2. Account-level temporary cooldown to prevent single-account targeted attacks.
    """
    ip = get_client_ip(request)
    ip_key = f"rate:login:ip:{ip}"

    # 1. IP rate check
    allowed, retry_after = _rate_limiter.check_and_record(
        key=ip_key,
        max_requests=DEFAULT_LOGIN_IP_LIMIT,
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts from this network. Please try again after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # 2. Account cooldown check
    account_key = f"rate:login:account:{email.strip().lower()}"
    in_cooldown, cooldown_retry = _rate_limiter.is_account_in_cooldown(account_key)
    if in_cooldown:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many failed login attempts for this account. "
                f"Please wait {cooldown_retry} seconds before trying again."
            ),
            headers={"Retry-After": str(cooldown_retry)},
        )


def record_failed_login(request: Request, email: str) -> None:
    """
    Track a failed login attempt for both IP and Account cooldown.
    """
    account_key = f"rate:login:account:{email.strip().lower()}"
    _rate_limiter.record_failure(account_key)


def record_successful_login(request: Request, email: str) -> None:
    """
    Reset failed login count upon successful credentials verification.
    """
    account_key = f"rate:login:account:{email.strip().lower()}"
    _rate_limiter.reset_account(account_key)

