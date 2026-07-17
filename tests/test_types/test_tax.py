"""Тесты для типов и расчётов налога."""

import pytest
from decimal import Decimal

from my_tax.types.tax import (
    TaxBonus,
    TaxSummary,
    TaxCharge,
    TaxHistory,
    TaxPayments,
    ListRegions,
    rate_for,
    estimate_tax,
)
from my_tax.enums.general import ClientType


class TestRateFor:
    def test_individual_rate(self):
        rate = rate_for(ClientType.FROM_INDIVIDUAL)

        assert rate.rate == Decimal("0.04")
        assert rate.bonus_rate == Decimal("0.01")
        assert rate.effective_rate == Decimal("0.03")

    def test_legal_entity_rate(self):
        rate = rate_for(ClientType.FROM_LEGAL_ENTITY)

        assert rate.rate == Decimal("0.06")
        assert rate.bonus_rate == Decimal("0.02")
        assert rate.effective_rate == Decimal("0.04")

    def test_foreign_agency_matches_legal_entity(self):
        assert rate_for(ClientType.FROM_FOREIGN_AGENCY).rate == Decimal("0.06")


class TestEstimateTax:
    @pytest.mark.parametrize(
        "amount, nominal, bonus, tax",
        [
            ("1000", "60.00", "20.00", "40.00"),
            ("2500", "150.00", "50.00", "100.00"),
            ("650", "39.00", "13.00", "26.00"),
        ],
    )
    def test_legal_entity_breakdown(self, amount, nominal, bonus, tax):
        estimate = estimate_tax(Decimal(amount), ClientType.FROM_LEGAL_ENTITY)

        assert estimate.nominal_tax == Decimal(nominal)
        assert estimate.bonus_applied == Decimal(bonus)
        assert estimate.tax == Decimal(tax)

    def test_individual_breakdown(self):
        estimate = estimate_tax(Decimal("650"), ClientType.FROM_INDIVIDUAL)

        assert estimate.nominal_tax == Decimal("26.00")
        assert estimate.bonus_applied == Decimal("6.50")
        assert estimate.tax == Decimal("19.50")

    def test_defaults_to_individual(self):
        assert estimate_tax(Decimal("1000")).rate == Decimal("0.04")

    def test_exhausted_bonus_charges_full_rate(self):
        estimate = estimate_tax(
            Decimal("1000"), ClientType.FROM_LEGAL_ENTITY, bonus_available=Decimal("0")
        )

        assert estimate.bonus_applied == Decimal("0")
        assert estimate.tax == Decimal("60.00")

    def test_bonus_capped_by_remaining_balance(self):
        estimate = estimate_tax(
            Decimal("1000"), ClientType.FROM_LEGAL_ENTITY, bonus_available=Decimal("5")
        )

        assert estimate.bonus_applied == Decimal("5")
        assert estimate.tax == Decimal("55.00")

    def test_partial_bonus_is_rounded_to_kopecks(self):
        estimate = estimate_tax(
            Decimal("1000"), ClientType.FROM_INDIVIDUAL, bonus_available=Decimal("5.000")
        )

        assert str(estimate.bonus_applied) == "5.00"

    def test_negative_bonus_balance_treated_as_zero(self):
        estimate = estimate_tax(
            Decimal("1000"), ClientType.FROM_LEGAL_ENTITY, bonus_available=Decimal("-100")
        )

        assert estimate.bonus_applied == Decimal("0")

    def test_effective_rate_drops_while_bonus_lasts(self):
        assert estimate_tax(Decimal("1000"), ClientType.FROM_LEGAL_ENTITY).effective_rate == Decimal("0.0400")

    def test_effective_rate_without_bonus(self):
        estimate = estimate_tax(
            Decimal("1000"), ClientType.FROM_LEGAL_ENTITY, bonus_available=Decimal("0")
        )

        assert estimate.effective_rate == Decimal("0.0600")

    def test_zero_amount_has_no_effective_rate(self):
        estimate = estimate_tax(Decimal("0"), ClientType.FROM_INDIVIDUAL)

        assert estimate.tax == Decimal("0.00")
        assert estimate.effective_rate == Decimal("0")

    def test_rounds_to_kopecks(self):
        estimate = estimate_tax(Decimal("333.33"), ClientType.FROM_INDIVIDUAL)

        assert estimate.nominal_tax == Decimal("13.33")
        assert estimate.bonus_applied == Decimal("3.33")


class TestTaxBonus:
    def test_parses_api_alias(self):
        bonus = TaxBonus.model_validate({"bonusAmount": 6320})

        assert bonus.amount == Decimal("6320")
        assert bonus.limit == Decimal("10000")
        assert bonus.spent == Decimal("3680")
        assert not bonus.is_exhausted()

    def test_exhausted(self):
        assert TaxBonus.model_validate({"bonusAmount": 0}).is_exhausted()

    def test_balance_above_limit_does_not_report_negative_spent(self):
        bonus = TaxBonus.model_validate({"bonusAmount": 12130})

        assert bonus.spent == Decimal("0")


class TestTaxSummary:
    def test_parses_api_response(self):
        summary = TaxSummary.model_validate({
            "totalForPayment": 5556,
            "total": 5556,
            "tax": 5556,
            "debt": 0,
            "overpayment": 0,
            "penalty": 0,
            "nominalTax": 8334,
            "taxPeriodId": 202607,
            "lastPaymentAmount": 1200,
            "lastPaymentDate": "2026-06-28T00:00:00Z",
        })

        assert summary.total_for_payment == Decimal("5556")
        assert summary.nominal_tax == Decimal("8334")
        assert summary.tax_period_id == 202607
        assert summary.last_payment_date.year == 2026

    def test_optional_fields_default(self):
        summary = TaxSummary.model_validate({"totalForPayment": 0, "total": 0, "tax": 0})

        assert summary.debt == Decimal("0")
        assert summary.nominal_tax is None
        assert summary.regions == []


class TestTaxCharge:
    def _charge(self, **overrides) -> TaxCharge:
        data = {
            "taxPeriodId": 202607,
            "taxAmount": 8334,
            "bonusAmount": 2778,
            "paidAmount": 2778,
            "taxBaseAmount": 138900,
            "dueDate": "2026-08-28T00:00:00Z",
            "oktmo": "46000000",
            "regionName": "Московская обл.",
            "receiptCount": 42,
        }
        data.update(overrides)
        return TaxCharge.model_validate(data)

    def test_parses_api_aliases(self):
        charge = self._charge()

        assert charge.tax_amount == Decimal("8334")
        assert charge.bonus_amount == Decimal("2778")
        assert charge.tax_base_amount == Decimal("138900")
        assert charge.due_date.month == 8
        assert charge.region_name == "Московская обл."
        assert charge.receipt_count == 42

    def test_unpaid_amount(self):
        assert self._charge().unpaid_amount == Decimal("5556")

    def test_fully_paid(self):
        charge = self._charge(paidAmount=8334)

        assert charge.unpaid_amount == Decimal("0")
        assert charge.is_paid()

    def test_overpaid_does_not_report_negative(self):
        assert self._charge(paidAmount=9000).unpaid_amount == Decimal("0")

    def test_unknown_charge_type_is_preserved(self):
        assert self._charge(type="SOME_NEW_TYPE").type == "SOME_NEW_TYPE"


class TestTaxHistory:
    def test_aggregates_records(self):
        history = TaxHistory.model_validate({
            "records": [
                {"taxPeriodId": 202606, "taxAmount": 1000, "bonusAmount": 300, "taxBaseAmount": 25000},
                {"taxPeriodId": 202607, "taxAmount": 2000, "bonusAmount": 600, "taxBaseAmount": 50000},
            ]
        })

        assert history.get_total_tax() == Decimal("3000")
        assert history.get_total_bonus() == Decimal("900")
        assert history.get_total_base() == Decimal("75000")

    def test_empty_history(self):
        history = TaxHistory.model_validate({"records": []})

        assert history.get_total_tax() == Decimal("0")
        assert history.get_total_base() == Decimal("0")


class TestTaxPayments:
    def test_totals(self):
        payments = TaxPayments.model_validate({
            "records": [
                {"amount": 1200, "operationDate": "2026-06-28T00:00:00Z", "status": "PAID"},
                {"amount": 800, "operationDate": "2026-05-28T00:00:00Z", "status": "PAID"},
            ]
        })

        assert payments.get_total() == Decimal("2000")
        assert payments.records[0].status == "PAID"

    def test_empty(self):
        assert TaxPayments.model_validate({"records": []}).get_total() == Decimal("0")


class TestListRegions:
    def test_find_by_oktmo(self):
        regions = ListRegions.model_validate({
            "items": [
                {"oktmo": "45000000", "name": "Москва"},
                {"oktmo": "46000000", "name": "Московская обл."},
            ],
            "unavailable": [],
        })

        assert regions.find_by_oktmo("46000000").name == "Московская обл."

    def test_find_by_unknown_oktmo(self):
        regions = ListRegions.model_validate({"items": []})

        assert regions.find_by_oktmo("46000000") is None
