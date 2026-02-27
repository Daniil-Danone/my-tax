"""
Базовые сущности для ЛК НПД
"""

from decimal import Decimal
from typing import Annotated, Any
from datetime import datetime, timezone
from pydantic import BeforeValidator, PlainSerializer


# ---------------------------------------------------------------------------
# AtomDateTime — Annotated-тип для datetime в формате ISO 8601 с Z суффиксом
# ---------------------------------------------------------------------------


def _parse_atom_datetime(v: Any) -> datetime:
    """Принимает datetime или ISO-строку, возвращает aware datetime (UTC)."""
    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)
    if isinstance(v, str):
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise ValueError(f"Cannot parse {type(v).__name__} as datetime")


def _serialize_atom_datetime(dt: datetime) -> str:
    """Сериализация datetime в ATOM формат с Z суффиксом."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


AtomDateTime = Annotated[
    datetime,
    BeforeValidator(_parse_atom_datetime),
    PlainSerializer(_serialize_atom_datetime, return_type=str),
]


def atom_datetime_now() -> datetime:
    """Текущее UTC время (для default_factory)."""
    return datetime.now(timezone.utc)


def _positive_decimal(v: Any) -> Decimal:
    """Десятичное число должно быть положительным. Принимает str/int/float/Decimal."""
    d = Decimal(str(v)) if not isinstance(v, Decimal) else v
    if d <= 0:
        raise ValueError("Значение должно быть положительным")
    return d


def _non_empty_str(v: str) -> str:
    """Строка не может быть пустой."""
    v = v.strip()
    if not v:
        raise ValueError("Значение не может быть пустой строкой")
    return v


def _optional_str_non_empty(v: str | None) -> str | None:
    """None допустим; строка — после strip не должна быть пустой."""
    if v is None:
        return None
    return _non_empty_str(v)


StrStripNone = Annotated[str | None, BeforeValidator(_optional_str_non_empty)]
StrNonEmpty = Annotated[str, BeforeValidator(_non_empty_str)]
PositiveDecimal = Annotated[Decimal, BeforeValidator(_positive_decimal)]