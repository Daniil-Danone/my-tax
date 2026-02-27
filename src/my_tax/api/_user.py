"""
API для пользователя (User).
"""

from ._base import BaseApi
from ..types.user import User


class UserApi(BaseApi):
    """Методы для пользователя."""

    async def get_user(self) -> User:
        """Получение профиля текущего пользователя."""
        data = await self._request_get("/user")
        return User.model_validate(data)

    async def get_avatar(self) -> bytes:
        """Получение аватара текущего пользователя."""
        data = await self._request_get_binary("/taxpayer/avatar")
        return data
