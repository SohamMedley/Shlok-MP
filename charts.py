"""
charts.py
---------
Builds the four Matplotlib charts used in the Analytics tab:

    1. Spending by Category      (pie chart)
    2. Budget vs Planned vs Remaining (bar chart)
    3. Original Price vs Sale Price per product (grouped bar chart)
    4. Priority Spending         (bar chart)

Each function takes a Matplotlib Figure (already embedded in the
Tkinter window by gui.py) and draws onto it. Splitting this out of
gui.py keeps chart-drawing code together and easy to modify without
touching the layout code.
"""

from matplotlib.figure import Figure
from budget import BudgetManager

# A simple, pleasant festival-inspired palette (not Amazon's branding)
COLORS = ["#FF6B35", "#F7C548", "#2EC4B6", "#5C6AC4", "#E56399",
          "#4CAF50", "#FF9F1C", "#8D6A9F", "#00A8E8", "#EF476F"]


def draw_category_pie_chart(fig: Figure, manager: BudgetManager) -> None:
    """Chart 1: Pie chart of spending by category."""
    fig.clear()
    ax = fig.add_subplot(111)
    data = manager.spending_by_category()

    if not data:
        ax.text(0.5, 0.5, "No products added yet", ha="center", va="center")
        ax.axis("off")
        return

    labels = list(data.keys())
    values = list(data.values())
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90,
           colors=COLORS[:len(labels)])
    ax.set_title("Shopping Budget by Category")
    ax.axis("equal")


def draw_budget_bar_chart(fig: Figure, manager: BudgetManager) -> None:
    """Chart 2: Bar chart comparing Total Budget, Planned Spending, Remaining Budget."""
    fig.clear()
    ax = fig.add_subplot(111)

    labels = ["Total Budget", "Planned Spending", "Remaining Budget"]
    values = [
        manager.plan.budget,
        manager.total_planned_cost(),
        max(manager.remaining_budget(), 0),
    ]
    bars = ax.bar(labels, values, color=["#5C6AC4", "#FF6B35", "#4CAF50"])
    ax.set_title("Budget vs Planned Spending")
    ax.set_ylabel("Amount (Rs)")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)


def draw_price_comparison_chart(fig: Figure, manager: BudgetManager) -> None:
    """Chart 3: Grouped bar chart of Original Price vs Discounted (Sale) Price per product."""
    fig.clear()
    ax = fig.add_subplot(111)
    products = manager.plan.products

    if not products:
        ax.text(0.5, 0.5, "No products added yet", ha="center", va="center")
        ax.axis("off")
        return

    names = [p.name for p in products]
    originals = [p.original_price for p in products]
    discounted = [p.discounted_price for p in products]

    x = range(len(names))
    width = 0.35
    ax.bar([i - width / 2 for i in x], originals, width, label="Original Price", color="#8D6A9F")
    ax.bar([i + width / 2 for i in x], discounted, width, label="Sale Price", color="#FF6B35")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_title("Original Price vs Sale Price")
    ax.set_ylabel("Price (Rs)")
    ax.legend()


def draw_priority_chart(fig: Figure, manager: BudgetManager) -> None:
    """Chart 4: Bar chart of spending grouped by priority (High/Medium/Low)."""
    fig.clear()
    ax = fig.add_subplot(111)
    data = manager.spending_by_priority()

    labels = list(data.keys())
    values = list(data.values())
    colors = {"High": "#EF476F", "Medium": "#F7C548", "Low": "#2EC4B6"}
    bar_colors = [colors.get(label, "#5C6AC4") for label in labels]

    bars = ax.bar(labels, values, color=bar_colors)
    ax.set_title("Priority Spending")
    ax.set_ylabel("Amount (Rs)")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8)
