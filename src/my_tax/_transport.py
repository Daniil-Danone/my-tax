"""HTTP-транспорт на базе httpx.AsyncClient."""

from typing import Optional, Union

import httpx
from httpx import Timeout

from .constants import BASE_URL_V1, DEFAULT_HEADERS


# Тип прокси совместим с httpx.AsyncClient(proxy=...):
# - str: "http://user:pass@host:port" или "socks5://host:port"
# - httpx.Proxy: для тонкой настройки (auth, headers)
# - None: без прокси
ProxyType = Optional[Union[str, httpx.Proxy]]


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
        proxy: ProxyType = None,
        verify: Union[bool, str] = True,
    ) -> None:
        """
        Args:
            base_url: базовый URL API (по умолчанию lknpd.nalog.ru).
            headers: дополнительные заголовки (мерджатся поверх DEFAULT_HEADERS).
            timeout/connect_timeout/read_timeout/write_timeout: таймауты в секундах.
            proxy: прокси для всех запросов. Принимает URL-строку
                (`"http://user:pass@host:port"`, `"socks5://host:port"`) или
                `httpx.Proxy`. Актуально для деплоя вне РФ —
                lknpd.nalog.ru доступен только с российских IP.
            verify: параметр httpx для проверки SSL (True/False/путь к ca-bundle).
        """
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
            proxy=proxy,
            verify=verify,
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
