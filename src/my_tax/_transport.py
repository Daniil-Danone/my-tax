"""HTTP-транспорт на базе httpx.AsyncClient."""

from typing import Optional

import httpx
from httpx import Timeout

from .constants import BASE_URL_V1, DEFAULT_HEADERS


class Transport:
    """HTTP-транспорт для запросов к API."""

    def __init__(
        self,
        base_url: str = BASE_URL_V1,
        headers: Optional[dict] = None,
        timeout: float = 5.0,
        connect_timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers,
            timeout=Timeout(
                timeout=timeout,
                connect=connect_timeout,
                read=read_timeout,
                write=write_timeout,
            ),
        )

    async def post(
        self,
        path: str,
        json: Optional[dict] = None,
        *,
        base_url: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ) -> httpx.Response:
        """Отправка POST-запроса."""
        url = (base_url or self._base_url).rstrip("/") + "/" + path.lstrip("/")
        merged_headers = {**(extra_headers or {})}
        return await self._client.post(
            url=url,
            json=json,
            headers=merged_headers or None
        )

    @property
    def raw_client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        """Закрытие HTTP-клиента."""
        await self._client.aclose()
