"""
Базовые классы для ручек API.

Ручки принимают клиент и вызывают client.request(method, path) — вся логика
авторизации и 401 (refresh + retry) сосредоточена в клиенте.
"""

from abc import ABC
from typing import Any, Dict, Protocol

import httpx


class SyncRequestClient(Protocol):
    """Протокол синхронного клиента с методом request (авторизация и 401 внутри)."""

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response: ...


class AsyncRequestClient(Protocol):
    """Протокол асинхронного клиента с методом request (авторизация и 401 внутри)."""

    async def request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response: ...


class BaseSyncApi(ABC):
    """
    Базовый класс для синхронных ручек API.

    Принимает клиент; запросы идут через client.request(), 401 обрабатывается в клиенте.
    """

    def __init__(self, client: SyncRequestClient) -> None:
        self._client = client

    def _request_get(self, path: str) -> Dict[str, Any]:
        """GET по path через клиент (с авторизацией и 401 retry)."""
        response = self._client.request("GET", path)
        response.raise_for_status()
        return response.json()


class BaseAsyncApi(ABC):
    """
    Базовый класс для асинхронных ручек API.

    Принимает клиент; запросы идут через await client.request(), 401 обрабатывается в клиенте.
    """

    def __init__(self, client: AsyncRequestClient) -> None:
        self._client = client

    async def _request_get(self, path: str) -> Dict[str, Any]:
        """GET по path через клиент (с авторизацией и 401 retry)."""
        response = await self._client.request("GET", path)
        response.raise_for_status()
        return response.json()
