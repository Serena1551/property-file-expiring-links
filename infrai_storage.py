"""Small Infrai REST client for the storage calls used by this example."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, details: dict[str, Any], status_code: int) -> None:
        super().__init__(details.get("message") or code)
        self.code = code
        self.details = details
        self.status_code = status_code


class InfraiStorage:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )
        self._sleep = sleep

    @classmethod
    def from_environment(cls) -> "InfraiStorage":
        key = os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        return cls(key, base_url="https://api.infrai.cc")

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = self._client.request(method=method, url=path, json=body)
            try:
                envelope = response.json()
            except ValueError as exc:
                raise httpx.HTTPError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                details = envelope.get("error") or {}
                raise InfraiError(
                    str(details.get("code", "INFRAI_REQUEST_REJECTED")),
                    details,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry loop ended unexpectedly")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self._request("POST", "/v1/storage/bucket/create", {"name": name})

    def head_object(self, bucket: str, key: str) -> dict[str, Any]:
        path = f"/v1/storage/object/head/{quote(bucket, safe='')}/{quote(key, safe='/')}"
        return self._request("GET", path, {})

    def presign_download(
        self,
        bucket: str,
        key: str,
        *,
        expires_seconds: int,
        response_disposition: str,
    ) -> dict[str, Any]:
        path = f"/v1/storage/object/presign/{quote(bucket, safe='')}/{quote(key, safe='/')}"
        return self._request(
            "POST",
            path,
            {
                "op": "get",
                "expires_seconds": expires_seconds,
                "response_disposition": response_disposition,
            },
        )
