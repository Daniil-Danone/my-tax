"""Tests for types/_base.py: AtomDateTime, PositiveDecimal, StrNonEmpty, StrStripNone."""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from pydantic import BaseModel, ValidationError

from my_tax.types._base import (
    AtomDateTime,
    atom_datetime_now,
    PositiveDecimal,
    StrNonEmpty,
    StrStripNone,
)


# ---------------------------------------------------------------------------
# Helper model for AtomDateTime tests
# ---------------------------------------------------------------------------

class _DtModel(BaseModel):
    ts: AtomDateTime


class _OptDtModel(BaseModel):
    ts: AtomDateTime | None = None


# ---------------------------------------------------------------------------
# AtomDateTime — parsing
# ---------------------------------------------------------------------------

class TestAtomDateTimeParsing:
    def test_from_iso_string_with_z(self):
        m = _DtModel.model_validate({"ts": "2024-06-15T10:30:00Z"})
        assert isinstance(m.ts, datetime)
        assert m.ts.tzinfo is not None
        assert m.ts.year == 2024
        assert m.ts.month == 6
        assert m.ts.hour == 10

    def test_from_iso_string_with_offset(self):
        m = _DtModel.model_validate({"ts": "2024-06-15T13:30:00+03:00"})
        assert m.ts.hour == 10  # converted to UTC

    def test_from_aware_datetime(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        m = _DtModel(ts=dt)
        assert m.ts == dt

    def test_from_naive_datetime_assumes_utc(self):
        dt = datetime(2024, 1, 1, 12, 0)
        m = _DtModel(ts=dt)
        assert m.ts.tzinfo == timezone.utc
        assert m.ts.hour == 12

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            _DtModel(ts=12345)

    def test_optional_none(self):
        m = _OptDtModel(ts=None)
        assert m.ts is None

    def test_optional_with_value(self):
        m = _OptDtModel.model_validate({"ts": "2024-01-01T00:00:00Z"})
        assert m.ts is not None
        assert m.ts.year == 2024


# ---------------------------------------------------------------------------
# AtomDateTime — serialization
# ---------------------------------------------------------------------------

class TestAtomDateTimeSerialization:
    def test_serializes_flat_string(self):
        m = _DtModel(ts=datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc))
        dumped = m.model_dump()
        assert isinstance(dumped["ts"], str)
        assert dumped["ts"] == "2024-06-15T10:30:00Z"

    def test_serializes_with_z_suffix(self):
        m = _DtModel(ts=datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert m.model_dump()["ts"].endswith("Z")

    def test_not_nested_dict(self):
        """Key regression: must NOT produce {"value": "..."} nested structure."""
        m = _DtModel(ts=datetime(2024, 1, 1, tzinfo=timezone.utc))
        dumped = m.model_dump()
        assert not isinstance(dumped["ts"], dict)

    def test_model_dump_json(self):
        m = _DtModel(ts=datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc))
        json_str = m.model_dump_json()
        assert '"2024-06-15T10:30:00Z"' in json_str


# ---------------------------------------------------------------------------
# atom_datetime_now
# ---------------------------------------------------------------------------

class TestAtomDateTimeNow:
    def test_returns_utc_datetime(self):
        now = atom_datetime_now()
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_is_recent(self):
        now = atom_datetime_now()
        diff = abs(datetime.now(timezone.utc) - now)
        assert diff < timedelta(seconds=2)


# ---------------------------------------------------------------------------
# PositiveDecimal
# ---------------------------------------------------------------------------

class _DecModel(BaseModel):
    val: PositiveDecimal


class TestPositiveDecimal:
    def test_accepts_positive(self):
        m = _DecModel(val=Decimal("10.5"))
        assert m.val == Decimal("10.5")

    def test_accepts_string(self):
        m = _DecModel.model_validate({"val": "99.99"})
        assert m.val == Decimal("99.99")

    def test_accepts_int(self):
        m = _DecModel.model_validate({"val": 42})
        assert m.val == Decimal("42")

    def test_rejects_zero(self):
        with pytest.raises(ValidationError):
            _DecModel(val=Decimal("0"))

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _DecModel(val=Decimal("-1"))


# ---------------------------------------------------------------------------
# StrNonEmpty
# ---------------------------------------------------------------------------

class _StrModel(BaseModel):
    val: StrNonEmpty


class TestStrNonEmpty:
    def test_accepts_normal_string(self):
        m = _StrModel(val="hello")
        assert m.val == "hello"

    def test_strips_whitespace(self):
        m = _StrModel(val="  hello  ")
        assert m.val == "hello"

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            _StrModel(val="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValidationError):
            _StrModel(val="   ")


# ---------------------------------------------------------------------------
# StrStripNone
# ---------------------------------------------------------------------------

class _OptStrModel(BaseModel):
    val: StrStripNone = None


class TestStrStripNone:
    def test_accepts_none(self):
        m = _OptStrModel(val=None)
        assert m.val is None

    def test_accepts_non_empty(self):
        m = _OptStrModel(val="hello")
        assert m.val == "hello"

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            _OptStrModel(val="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValidationError):
            _OptStrModel(val="   ")
