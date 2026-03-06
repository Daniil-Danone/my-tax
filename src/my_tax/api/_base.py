"""
Базовые классы для API ЛК НПД.

API принимают клиент и вызывают client.request(method, path) — вся логика
авторизации и 401 (refresh + retry) сосредоточена в клиенте.
"""

from abc import ABC
from typing import Any, Dict, Optional, Protocol

import httpx

from ..exceptions import ApiRequestError, api_error_message


class RequestClient(Protocol):
    """Протокол клиента с методом request (авторизация и 401 внутри)."""

    async def request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response: ...


class BaseApi(ABC):
    """
    Базовый класс для ручек API.

    Принимает клиент; запросы идут через await client.request(), 401 обрабатывается в клиенте.
    """

    def __init__(self, client: RequestClient) -> None:
        self._client = client

    def _raise_for_status(self, response: httpx.Response) -> None:
        """При 4xx/5xx выбрасывает ApiRequestError с телом ответа в сообщении."""
        if not response.is_error:
            return
        
        raise ApiRequestError(
            api_error_message(response),
            response=response,
        )

    async def _request_get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """GET по path с опциональными query-параметрами (с авторизацией и 401 retry)."""
        response = await self._client.request("GET", path, params=params)
        self._raise_for_status(response)
        return response.json()

    async def _request_get_binary(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """GET по path с опциональными query-параметрами (с авторизацией и 401 retry)."""
        response = await self._client.request("GET", path, params=params)
        self._raise_for_status(response)
        return response.content

    async def _request_post(
        self, path: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """POST по path с телом json_data (с авторизацией и 401 retry)."""
        response = await self._client.request("POST", path, json=json_data or {})
        self._raise_for_status(response)
        return response.json()
