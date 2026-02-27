"""Tests for types/payment_method.py."""

from my_tax.types.payment_method import PaymentMethod, ListPaymentMethods
from my_tax.enums.invoice import PaymentMethodType


PAYMENT_METHOD_JSON = {
    "id": 1,
    "type": "PHONE",
    "phone": "79991234567",
    "favorite": True,
    "availableForPa": False,
}

PAYMENT_METHOD_ACCOUNT_JSON = {
    "id": 2,
    "type": "ACCOUNT",
    "bankName": "Tinkoff",
    "bankBik": "044525974",
    "currentAccount": "40817810200054769732",
    "corrAccount": "30101810145250000974",
    "favorite": True,
    "availableForPa": True,
}


class TestPaymentMethod:
    def test_phone_type(self):
        pm = PaymentMethod.model_validate(PAYMENT_METHOD_JSON)
        assert pm.type == PaymentMethodType.PHONE
        assert pm.phone == "79991234567"
        assert pm.bank_name is None

    def test_account_type(self):
        pm = PaymentMethod.model_validate(PAYMENT_METHOD_ACCOUNT_JSON)
        assert pm.type == PaymentMethodType.ACCOUNT
        assert pm.bank_name == "Tinkoff"
        assert pm.bank_bik == "044525974"


class TestListPaymentMethods:
    def test_model_validate(self):
        data = {"items": [PAYMENT_METHOD_JSON, PAYMENT_METHOD_ACCOUNT_JSON]}
        result = ListPaymentMethods.model_validate(data)
        assert len(result.items) == 2

    def test_empty_list(self):
        result = ListPaymentMethods.model_validate({"items": []})
        assert result.items == []
