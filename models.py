"""
models.py
----------
Defines the core data structures used across the application:

    Product      -> represents a single planned purchase
    ShoppingPlan -> represents the full collection of products + budget

Keeping these as plain data-holding classes (with a few convenience
methods) makes it easy to convert them to/from dictionaries for JSON
storage, and keeps calculation logic (in budget.py) separate from the
data itself.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


@dataclass
class Product:
    """Represents one product the user is planning to buy."""

    name: str
    category: str
    original_price: float
    discount: float          # percentage, e.g. 15 means 15%
    quantity: int
    priority: str            # "High" / "Medium" / "Low"

    # ---- Derived (computed) values -------------------------------------
    @property
    def discount_amount_per_unit(self) -> float:
        """Rupees saved per single unit because of the discount."""
        return self.original_price * (self.discount / 100)

    @property
    def discounted_price(self) -> float:
        """Price of ONE unit after the discount is applied."""
        return self.original_price - self.discount_amount_per_unit

    @property
    def total_original_cost(self) -> float:
        """Original price x quantity (before discount)."""
        return self.original_price * self.quantity

    @property
    def total_cost(self) -> float:
        """Final cost the user will actually pay for this line item."""
        return self.discounted_price * self.quantity

    @property
    def total_savings(self) -> float:
        """Total rupees saved on this product because of the discount."""
        return self.total_original_cost - self.total_cost

    # ---- Conversion helpers ---------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Convert this product into a plain dictionary (for JSON/CSV)."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Product":
        """Re-create a Product object from a dictionary (loaded from JSON)."""
        return Product(
            name=data["name"],
            category=data["category"],
            original_price=float(data["original_price"]),
            discount=float(data["discount"]),
            quantity=int(data["quantity"]),
            priority=data["priority"],
        )


@dataclass
class ShoppingPlan:
    """Holds the user's total budget and every planned Product."""

    budget: float = 0.0
    products: List[Product] = field(default_factory=list)

    # ---- Basic list operations --------------------------------------
    def add_product(self, product: Product) -> None:
        self.products.append(product)

    def remove_product(self, index: int) -> None:
        if 0 <= index < len(self.products):
            del self.products[index]

    def update_product(self, index: int, product: Product) -> None:
        if 0 <= index < len(self.products):
            self.products[index] = product

    def clear_products(self) -> None:
        self.products.clear()

    # ---- Conversion helpers ---------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget": self.budget,
            "products": [p.to_dict() for p in self.products],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ShoppingPlan":
        plan = ShoppingPlan(budget=float(data.get("budget", 0.0)))
        for item in data.get("products", []):
            plan.add_product(Product.from_dict(item))
        return plan
