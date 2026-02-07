"""Ручки API ЛК НПД: базовый класс и ресурсы (user, ...)."""

from .base import BaseAsyncApi, BaseSyncApi
from .user import UserAsyncApi, UserSyncApi

__all__ = [
    "BaseSyncApi",
    "BaseAsyncApi",
    "UserSyncApi",
    "UserAsyncApi",
]
