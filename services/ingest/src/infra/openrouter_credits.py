"""Live OpenRouter balance gate for news ingestion."""

from decimal import Decimal
import os

import requests

from config import OPENROUTER_MANAGEMENT_API_KEY, OPENROUTER_MIN_CREDITS_USD
from infra.rate_limit import wait_for_url


class CreditCheckError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _money(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CreditCheckError("credit_check_failed")
    amount = Decimal(str(value))
    if not amount.is_finite():
        raise CreditCheckError("credit_check_failed")
    return amount


def _get_data(endpoint: str, key: str) -> dict:
    # Fixed origin and no redirects keep credentials on OpenRouter.
    url = "https://openrouter.ai/api/v1/" + endpoint
    wait_for_url(url)
    try:
        response = requests.get(
            url, headers={"Authorization": f"Bearer {key}"},
            timeout=10, allow_redirects=False,
        )
        if response.status_code != 200:
            raise CreditCheckError("credit_check_failed")
        data = response.json()["data"]
        if not isinstance(data, dict):
            raise CreditCheckError("credit_check_failed")
        return data
    except (requests.RequestException, ValueError, KeyError, TypeError):
        raise CreditCheckError("credit_check_failed") from None


def check_available_credits() -> float:
    """Return usable USD or stop when balance is low or cannot be verified.

    The minimum is an operational floor for an item's calls and reserve,
    not a price quote or a reservation of credits.
    """
    generation_key = os.getenv("OPEN_ROUTER_API_KEY")
    if not generation_key or not OPENROUTER_MANAGEMENT_API_KEY:
        raise CreditCheckError("credit_check_failed")
    minimum = _money(OPENROUTER_MIN_CREDITS_USD)
    if minimum <= 0:
        raise CreditCheckError("credit_check_failed")
    try:
        account = _get_data("credits", OPENROUTER_MANAGEMENT_API_KEY)
        key = _get_data("key", generation_key)
        available = _money(account["total_credits"]) - _money(account["total_usage"])
        remaining = key["limit_remaining"]
        if remaining is not None:
            available = min(available, _money(remaining))
        budget = key.get("effective_budget")
        if budget is not None:
            available = min(available, _money(budget["remaining_usd"]))
    except (KeyError, TypeError):
        raise CreditCheckError("credit_check_failed") from None
    if available < minimum:
        raise CreditCheckError("insufficient_credits")
    return float(available)
