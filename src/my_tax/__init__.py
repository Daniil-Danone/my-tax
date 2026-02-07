"""My Tax — HTTP client for lknpd.nalog.ru API."""

from .clients import (
    AsyncMyTaxClient, 
    SyncMyTaxClient
)

from .domain.exceptions import (
    AccessTokenNotFoundError,
    AuthorizationError,
    BaseDomainException,
    SmsChallengeError,
)

from .domain.entites import (
    AuthData, 
    Credentials, 
    DeviceInfo, 
    Token, 
    User
)

__all__ = [
    # Clients
    "AsyncMyTaxClient",
    "SyncMyTaxClient",
    # Entities
    "AuthData",
    "Credentials",
    "DeviceInfo",
    "Token",
    "User",
    # Exceptions
    "BaseDomainException",
    "AuthorizationError",
    "AccessTokenNotFoundError",
    "SmsChallengeError",
]
