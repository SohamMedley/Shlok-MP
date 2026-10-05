"""
budget.py
---------
Contains BudgetManager: all the "business logic" of the application.

This class takes a ShoppingPlan (budget + products) and produces every
derived number the GUI needs to display: totals, savings, per-category
spending, per-priority spending, budget status, and rule-based shopping
recommendations.

Keeping this logic separate from gui.py means the calculations can be
tested/verified independently of the interface, and the GUI stays
focused purely on layout and user interaction.
"""

from typing import List, Dict
from models import ShoppingPlan, Product


class BudgetManager:
    """Performs all budget-related calculations for a ShoppingPlan."""

    def __init__(self, plan: ShoppingPlan):
        self.plan = plan

    # ------------------------------------------------------------------
    # Core totals
    # ------------------------------------------------------------------
    def total_original_cost(self) -> float:
        return sum(p.total_original_cost for p in self.plan.products)

    def total_discount_amount(self) -> float:
        return sum(p.discount_amount_per_unit * p.quantity for p in self.plan.products)

    def total_planned_cost(self) -> float:
        return sum(p.total_cost for p in self.plan.products)

    def total_savings(self) -> float:
        return self.total_original_cost() - self.total_planned_cost()

    def remaining_budget(self) -> float:
        return self.plan.budget - self.total_planned_cost()

    def budget_usage_percent(self) -> float:
        if self.plan.budget <= 0:
            return 0.0
        return (self.total_planned_cost() / self.plan.budget) * 100

    def is_over_budget(self) -> bool:
        return self.total_planned_cost() > self.plan.budget

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def budget_status(self) -> str:
        """Return one of: Safe, Moderate, Near Limit, Over Budget."""
        usage = self.budget_usage_percent()
        if usage > 100:
            return "Over Budget"
        elif usage >= 90:
            return "Near Limit"
        elif usage >= 70:
            return "Moderate"
        else:
            return "Safe"

    # ------------------------------------------------------------------
    # Category / Priority breakdowns
    # ------------------------------------------------------------------
    def spending_by_category(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for p in self.plan.products:
            totals[p.category] = totals.get(p.category, 0.0) + p.total_cost
        return totals

    def spending_by_priority(self) -> Dict[str, float]:
        totals = {"High": 0.0, "Medium": 0.0, "Low": 0.0}
        for p in self.plan.products:
            totals[p.priority] = totals.get(p.priority, 0.0) + p.total_cost
        return totals

    def count_by_priority(self) -> Dict[str, int]:
        counts = {"High": 0, "Medium": 0, "Low": 0}
        for p in self.plan.products:
            counts[p.priority] = counts.get(p.priority, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Rule-based recommendation engine
    # ------------------------------------------------------------------
    def get_recommendations(self) -> List[str]:
        """
        Analyze the current shopping plan and return a list of simple,
        rule-based suggestions (no AI/ML involved -- just if/else logic).
        """
        recommendations: List[str] = []

        if not self.plan.products:
            return ["Add some products to see personalized recommendations."]

        usage = self.budget_usage_percent()
        planned_cost = self.total_planned_cost()

        # --- Overall budget checks -----------------------------------
        if self.is_over_budget():
            over_amount = planned_cost - self.plan.budget
            recommendations.append(
                f"Your planned spending exceeds the budget by {over_amount:,.2f} rupees. "
                "Consider removing low-priority products."
            )
        elif usage >= 90:
            recommendations.append(
                "Your budget is almost fully utilized. Review low-priority purchases."
            )

        # --- Priority checks -------------------------------------------
        counts = self.count_by_priority()
        if counts["Low"] > max(counts["High"], 1) and counts["Low"] >= 2:
            recommendations.append(
                "You have several low-priority products planned. "
                "Consider purchasing high-priority products first."
            )

        # --- Discount checks (per product) -----------------------------
        for p in self.plan.products:
            if p.discount > 40:
                recommendations.append(
                    f"'{p.name}' has a high expected discount ({p.discount:.0f}%). Good time to buy!"
                )
            elif p.discount < 5:
                recommendations.append(
                    f"'{p.name}' has a very low discount ({p.discount:.0f}%). "
                    "Consider checking whether a better sale price is available."
                )

        # --- Category concentration check ------------------------------
        category_totals = self.spending_by_category()
        if planned_cost > 0:
            for category, amount in category_totals.items():
                if (amount / planned_cost) > 0.5:
                    recommendations.append(
                        f"Most of your budget is allocated to {category}. "
                        "Review category allocation for a balanced plan."
                    )

        if not recommendations:
            recommendations.append(
                "Your shopping plan looks well balanced. Happy festive shopping!"
            )

        return recommendations

    # ------------------------------------------------------------------
    # Sorting / Filtering helpers (used by the GUI's product table)
    # ------------------------------------------------------------------
    def filtered_products(self, search_text: str = "", category: str = "All") -> List[Product]:
        """Return products filtered by a name search and/or category."""
        results = self.plan.products
        if category and category != "All":
            results = [p for p in results if p.category == category]
        if search_text:
            search_lower = search_text.lower()
            results = [p for p in results if search_lower in p.name.lower()]
        return results

    @staticmethod
    def sort_products(products: List[Product], sort_key: str, reverse: bool = False) -> List[Product]:
        """Sort a list of products by name, price, discount, category or priority."""
        key_map = {
            "Product Name": lambda p: p.name.lower(),
            "Price": lambda p: p.total_cost,
            "Discount": lambda p: p.discount,
            "Category": lambda p: p.category.lower(),
            "Priority": lambda p: {"High": 0, "Medium": 1, "Low": 2}.get(p.priority, 3),
        }
        key_func = key_map.get(sort_key, key_map["Product Name"])
        return sorted(products, key=key_func, reverse=reverse)
