import json
from decimal import Decimal
from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import Numeric
from sqlalchemy.exc import IntegrityError

from backend import models
from backend.schemas.billing import ExpenseCreate, PaymentCreate
from backend.schemas.clinical import TreatmentCreate
from backend.schemas.laboratory import LabPaymentCreate


@pytest.mark.parametrize("amount", [0, -1, "-100.00", "1.001"])
def test_payment_rejects_non_positive_or_over_precise_amount(amount):
    with pytest.raises(ValidationError):
        PaymentCreate(patient_id=1, amount=amount)


@pytest.mark.parametrize("cost", [0, -1, "-50.00", "2.999"])
def test_expense_rejects_non_positive_or_over_precise_cost(cost):
    with pytest.raises(ValidationError):
        ExpenseCreate(
            item_name="Invalid expense",
            cost=cost,
            category="test",
            date=date(2026, 8, 22),
        )


def test_treatment_rejects_negative_values_and_excessive_discount():
    with pytest.raises(ValidationError):
        TreatmentCreate(patient_id=1, cost=-1)
    with pytest.raises(ValidationError):
        TreatmentCreate(patient_id=1, cost=100, discount=100.01)


def test_lab_payment_requires_positive_amount():
    with pytest.raises(ValidationError):
        LabPaymentCreate(laboratory_id=1, amount=0)


def test_decimal_inputs_stay_exact_but_serialize_as_json_numbers():
    payment = PaymentCreate(patient_id=1, amount="100.25")
    assert payment.amount == Decimal("100.25")
    payload = json.loads(payment.model_dump_json())
    assert payload["amount"] == 100.25
    assert isinstance(payload["amount"], float)


def test_all_persisted_money_columns_use_numeric():
    money_columns = (
        models.Payment.amount,
        models.Expense.cost,
        models.SalaryPayment.amount,
        models.LabPayment.amount,
        models.Treatment.cost,
        models.Treatment.discount,
        models.Treatment.unit_price,
        models.LabOrder.cost,
        models.LabOrder.price_to_patient,
        models.Procedure.price,
        models.SubscriptionPlan.price,
        models.SubscriptionPayment.amount,
        models.SubscriptionCheckout.expected_amount,
        models.Tenant.total_revenue,
        models.User.commission_percent,
        models.User.fixed_salary,
        models.User.per_appointment_fee,
        models.PriceList.coverage_percent,
        models.PriceList.copay_percent,
        models.PriceList.copay_fixed,
        models.PriceListItem.price,
        models.PriceListItem.discount_percent,
        models.Material.standard_price,
        models.Batch.cost_per_unit,
        models.TreatmentMaterialUsage.cost_calculated,
        models.AILog.cost,
        models.DailySystemStats.total_revenue,
    )
    assert all(isinstance(column.property.columns[0].type, Numeric) for column in money_columns)


def test_database_rejects_negative_expense_even_without_api_validation(db_session):
    db_session.add(
        models.Expense(
            item_name="Bypass attempt",
            cost=-1,
            category="test",
            date=date(2026, 8, 22),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_database_rejects_treatment_discount_above_cost(db_session):
    db_session.add(
        models.Treatment(
            patient_id=1,
            cost=Decimal("100.00"),
            discount=Decimal("150.00"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
