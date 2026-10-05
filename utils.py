"""
utils.py
--------
Small, reusable helper/validation functions used throughout the app.

Keeping validation here (instead of scattering "if" checks inside the
GUI code) means:
    * the same rule is applied everywhere it's needed
    * the GUI code stays focused on layout/interaction
    * it's easy to unit-test these functions on their own
"""

from typing import Tuple

CATEGORIES = [
    "Electronics",
    "Smartphones",
    "Laptops",
    "Fashion",
    "Home & Kitchen",
    "Beauty",
    "Grocery",
    "Books",
    "Gaming",
    "Appliances",
    "Other",
]

PRIORITIES = ["High", "Medium", "Low"]


class ValidationError(Exception):
    """Raised when user-entered data fails validation."""
    pass


def validate_non_empty_text(value: str, field_name: str = "Field") -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field_name} cannot be empty.")
    return value


def validate_price(value: str, field_name: str = "Price") -> float:
    """Ensure a price string is a positive number."""
    try:
        price = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid number.")
    if price <= 0:
        raise ValidationError(f"{field_name} must be greater than 0.")
    return price


def validate_discount(value: str) -> float:
    """Ensure a discount string is a number between 0 and 100."""
    try:
        discount = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Discount must be a valid number.")
    if discount < 0 or discount > 100:
        raise ValidationError("Discount must be between 0 and 100.")
    return discount


def validate_quantity(value: str) -> int:
    """Ensure a quantity string is a whole number >= 1."""
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Quantity must be a whole number.")
    if quantity < 1:
        raise ValidationError("Quantity must be at least 1.")
    return quantity


def validate_budget(value: str) -> float:
    """Ensure the total shopping budget is a positive number."""
    try:
        budget = float(value)
    except (TypeError, ValueError):
        raise ValidationError("Budget must be a valid number.")
    if budget <= 0:
        raise ValidationError("Budget must be greater than 0.")
    return budget


def format_currency(amount: float) -> str:
    """Format a number as an Indian-Rupee style string, e.g. Rs 50,000.00."""
    # Note: we use "Rs" instead of the rupee glyph (Rs) because some
    # Tkinter/Matplotlib font combinations on Windows do not render the
    # Unicode rupee sign correctly, showing a blank box instead.
    try:
        return f"Rs {amount:,.2f}"
    except (TypeError, ValueError):
        return "Rs 0.00"


def calculate_bank_offer(subtotal: float, bank_discount_pct: float,
                          max_discount: float, coupon_discount: float) -> Tuple[float, float, float]:
    """
    Calculate the final price after a bank discount (capped at a maximum)
    and an additional flat coupon discount.

    Returns a tuple: (actual_bank_discount, final_price, total_discount)
    """
    raw_bank_discount = subtotal * (bank_discount_pct / 100)
    actual_bank_discount = min(raw_bank_discount, max_discount)
    final_price = subtotal - actual_bank_discount - coupon_discount
    final_price = max(final_price, 0.0)  # never allow a negative price
    total_discount = subtotal - final_price
    return actual_bank_discount, final_price, total_discount
