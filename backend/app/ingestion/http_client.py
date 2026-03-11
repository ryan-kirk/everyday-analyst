from __future__ import annotations

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


def _build_session(max_retries: int, backoff_factor: float) -> requests.Session:
    retry_strategy = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        status=max_retries,
        allowed_methods=frozenset({"GET", "POST"}),
        status_forcelist=RETRYABLE_STATUS_CODES,
        backoff_factor=backoff_factor,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def request_json_with_retry(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    max_retries: int = 4,
    backoff_factor: float = 0.8,
) -> dict[str, Any]:
    """Request JSON from an HTTP API with retry behavior for transient failures."""
    session = _build_session(max_retries=max_retries, backoff_factor=backoff_factor)

    try:
        response = session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=timeout,
        )
        if response.status_code >= 400:
            logger.error(
                "API request failed: method=%s url=%s status=%s body=%s",
                method.upper(),
                url,
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
        return response.json()
    except requests.RequestException:
        logger.exception("Request failed after retries: method=%s url=%s", method.upper(), url)
        raise
    finally:
        session.close()


def request_text_with_retry(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    max_retries: int = 4,
    backoff_factor: float = 0.8,
) -> str:
    """Request text (HTML/CSV/etc.) with retry behavior for transient failures."""
    session = _build_session(max_retries=max_retries, backoff_factor=backoff_factor)
    try:
        response = session.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        if response.status_code >= 400:
            logger.error(
                "API request failed: method=%s url=%s status=%s body=%s",
                method.upper(),
                url,
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
        return response.text
    except requests.RequestException:
        logger.exception("Request failed after retries: method=%s url=%s", method.upper(), url)
        raise
    finally:
        session.close()
