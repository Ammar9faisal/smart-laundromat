import pytest

from app.services.payment_gateway import SimulatedPaymentGateway


@pytest.mark.parametrize("method", ["pm_card_visa", "pm_card_mastercard"])
def test_successful_test_cards(method):
    result = SimulatedPaymentGateway().charge(4.5, "CAD", method)

    assert result.succeeded
    assert result.failure_reason is None
    assert result.provider_ref.startswith("sim_")


@pytest.mark.parametrize(
    ("method", "reason"),
    [
        ("pm_card_chargeDeclined", "Your card was declined."),
        ("pm_card_chargeDeclinedInsufficientFunds", "Your card has insufficient funds."),
    ],
)
def test_declined_test_cards(method, reason):
    result = SimulatedPaymentGateway().charge(4.5, "CAD", method)

    assert not result.succeeded
    assert result.failure_reason == reason


def test_each_charge_gets_a_new_reference():
    gateway = SimulatedPaymentGateway()

    first = gateway.charge(4.5, "CAD", "pm_card_visa")
    second = gateway.charge(4.5, "CAD", "pm_card_visa")

    assert first.provider_ref != second.provider_ref


def test_unknown_payment_method_is_rejected():
    with pytest.raises(ValueError):
        SimulatedPaymentGateway().charge(4.5, "CAD", "4242424242424242")
