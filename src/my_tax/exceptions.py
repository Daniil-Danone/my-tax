"""Исключения для API и ошибок авторизации."""


class MyTaxError(Exception):
    """Базовое исключение для клиента ЛК НПД."""
    pass


class AuthorizationError(MyTaxError):
    """Исключение при ошибке авторизации."""
    pass


class AccessTokenNotFoundError(MyTaxError):
    """Исключение при отсутствии access-токена в ответе на refresh."""
    pass


class SmsChallengeError(MyTaxError):
    """Исключение при ошибке SMS-челленджа."""
    pass
