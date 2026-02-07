"""
Ручки API для ресурса «пользователь» (GET /user и др.).
"""

from .base import BaseAsyncApi, BaseSyncApi
from ..domain.entites import User


class UserSyncApi(BaseSyncApi):
    """Синхронные ручки для ресурса пользователя (GET /user)."""

    def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        data = self._request_get("/user")
        return User.model_validate(data)


class UserAsyncApi(BaseAsyncApi):
    """Асинхронные ручки для ресурса пользователя (GET /user)."""

    async def get_user(self) -> User:
        """Получение профиля текущего пользователя (GET /user)."""
        data = await self._request_get("/user")
        return User.model_validate(data)
