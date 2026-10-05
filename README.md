# Amazon Great Indian Festival - Shopping Budget Planner

A desktop Python application (Tkinter + Matplotlib) that helps a shopper
plan their budget for a big festival sale: add products, apply expected
discounts, track spending against a budget, see analytics, and export
a shopping summary.

> **Disclaimer:** This is a college/student project. It is **not**
> affiliated with, endorsed by, or connected to Amazon in any way. It
> does not use Amazon's logo, branding, or any real-time price data. All
> prices and discounts entered or shown as "sample data" are fictional
> and for demonstration purposes only.

---

## 1. Introduction

Big sale events tempt shoppers into overspending. This tool lets a user
set a firm budget up front, plan every purchase (with its category,
expected discount, priority and quantity), and see in real time whether
they are on track, close to their limit, or already over budget --
along with simple, rule-based suggestions for staying within budget.

## 2. Features

- Set / reset a total shopping budget with input validation
- Add, edit, delete and clear planned products
- Automatic discount, savings and total-cost calculations
- Live dashboard cards: Total Budget, Planned Spending, Remaining
  Budget, Savings
- Budget status indicator (Safe / Moderate / Near Limit / Over Budget)
  with a color-coded progress bar
- Rule-based "Smart Shopping Recommendations" engine
- Priority analysis (High / Medium / Low spending breakdown)
- Category spending breakdown
- Search products by name + filter by category
- Sort the product table by name, price, discount, category or priority
  (click a column heading, or use the Sort-by dropdown)
- Four Matplotlib charts: category pie chart, budget bar chart,
  original-vs-sale-price comparison, priority spending chart
- Save / Load the entire shopping plan as JSON
- Load a bundled sample plan (8 fictional products) with one click
- Export the shopping list (+ a short summary) to CSV
- A printable "Final Shopping Summary" tab
- A small Bank Offer / Coupon calculator (capped bank discount + flat
  coupon, never lets the final price go below zero)
- A "Festival Shopping Tips" panel (general planning advice only)
- Friendly error dialogs for every invalid input -- the app never
  crashes on bad user input

## 3. Technologies Used

| Purpose            | Library                          |
|---------------------|-----------------------------------|
| GUI                 | `tkinter`, `tkinter.ttk`          |
| Charts              | `matplotlib` (embedded via `FigureCanvasTkAgg`) |
| Data storage        | `json` (save/load plan)           |
| Data export         | `csv` (export shopping list)      |
| Language            | Python 3                          |

`matplotlib` is the only third-party package required; everything else
is from the Python standard library.

## 4. Project Structure

```
Amazon_GIF_Budget_Planner/
|
├── main.py           # Entry point - creates the Tk root window and starts the app
├── gui.py            # BudgetPlannerApp - all Tkinter/ttk widgets and event handlers
├── budget.py         # BudgetManager - every calculation + the recommendation engine
├── models.py         # Product and ShoppingPlan data classes
├── storage.py        # StorageManager - JSON save/load and CSV export
├── charts.py         # Matplotlib chart-drawing functions used by the Analytics tab
├── utils.py          # Validation helpers, currency formatting, bank-offer math
├── requirements.txt  # Third-party dependencies (matplotlib)
├── README.md         # This file
|
├── data/
│   └── shopping_plan.json   # Sample shopping plan (8 fictional products)
|
└── exports/
    └── shopping_summary.csv # Created here the first time you export (not pre-included)
```

### File responsibilities in one line each

- **main.py** -- boots the Tkinter app; catches any unexpected startup error.
- **gui.py** -- builds every tab (Dashboard, Shopping List, Analytics,
  Summary) and wires buttons/forms to the logic in the other modules.
- **budget.py** -- turns a `ShoppingPlan` into every number the GUI
  needs (totals, savings, usage %, status, category/priority
  breakdowns) and produces the rule-based recommendations.
- **models.py** -- plain data classes (`Product`, `ShoppingPlan`) with
  a few calculated properties (discounted price, total cost, etc.) and
  `to_dict` / `from_dict` helpers for JSON conversion.
- **storage.py** -- reads/writes the JSON plan file and writes the CSV
  export, with error handling for missing/corrupt files.
- **charts.py** -- four functions, one per chart, each drawing onto a
  Matplotlib `Figure` that `gui.py` embeds in the Analytics tab.
- **utils.py** -- input validation functions (`validate_price`,
  `validate_discount`, `validate_quantity`, `validate_budget`),
  currency formatting, and the bank-offer calculation.

## 5. How to Install

```bash
pip install -r requirements.txt
```

(`tkinter` ships with most standard Python installers on Windows/macOS.
On Debian/Ubuntu Linux, if it's missing, install it separately with
`sudo apt install python3-tk`.)

## 6. How to Run

```bash
python main.py
```

A window titled **"Amazon Great Indian Festival - Shopping Budget
Planner"** will open at approximately 1200x750 pixels (resizable).

## 7. How It Works (Workflow)

1. Open the **Dashboard** tab and enter a **Total Shopping Budget**,
   then click **Set Budget**.
2. Go to the **Shopping List** tab and fill in the **Add Product**
   form (name, category, original price, expected discount %,
   priority, quantity), then click **Add Product**.
3. The **Dashboard** cards, budget status bar, priority analysis and
   recommendations update automatically every time a product is
   added, edited or deleted.
4. Select a row in the product table and click **Edit Selected** or
   **Delete Selected** to change your plan. Use the search box and
   category filter to narrow the table, and the **Sort by** dropdown
   (or click a column heading) to reorder it.
5. Open the **Analytics** tab to see four live charts.
6. Open the **Summary** tab and click **View Summary** for a final,
   printable-style report.
7. Use **Save Plan** / **Load Plan** to persist your work as JSON, or
   **Export CSV** to get a spreadsheet-friendly shopping list.
   **Load Sample Data** loads the bundled example plan in `data/`.

## 8. Main Calculations

For each product:

```
Discount Amount (per unit) = Original Price x (Discount % / 100)
Discounted Price (per unit) = Original Price - Discount Amount
Total Cost (line item)      = Discounted Price x Quantity
```

For the whole plan:

```
Total Original Cost   = sum(original_price x quantity)            for every product
Total Discount Amount = sum(discount_amount_per_unit x quantity)  for every product
Total Planned Cost    = sum(discounted_price x quantity)          for every product
Total Savings         = Total Original Cost - Total Planned Cost
Remaining Budget      = Total Budget - Total Planned Cost
Budget Usage %        = (Total Planned Cost / Total Budget) x 100
```

Budget status thresholds (based on Budget Usage %):

| Usage          | Status       |
|----------------|--------------|
| < 70%          | Safe         |
| 70% -- 90%     | Moderate     |
| 90% -- 100%    | Near Limit   |
| > 100%         | Over Budget  |

Bank Offer Calculator:

```
Actual Bank Discount = min(Subtotal x Bank Discount %, Maximum Bank Discount)
Final Price          = max(Subtotal - Actual Bank Discount - Coupon Discount, 0)
```

## 9. Sample Data

`data/shopping_plan.json` contains a sample budget (Rs 100,000) and
8 fictional example products (a laptop, a smartphone, headphones,
running shoes, a backpack, a smartwatch, a book set, and a stand
mixer) with example prices and discounts, clearly labeled "(Sample)"
in their names. Click **Load Sample Data** in the Shopping List tab
to load them at any time.

## 10. A Note on the Rupee Symbol

The app displays amounts as `Rs 1,234.56` rather than using the Unicode
rupee glyph (Rs) directly, because that glyph does not render reliably
in every Tkinter/Matplotlib font combination on every operating system
(it can appear as a blank box). This is a small, deliberate design
choice to keep the UI legible everywhere the app runs.

## 11. Future Scope

- Real-time price-tracking APIs (would require an internet connection
  and API keys -- intentionally out of scope for this offline project)
- Direct Amazon product links / affiliate integration
- Historical price tracking and price-drop alerts
- Machine-learning based personalized recommendations
- Multi-user accounts and cloud-synced plans
- A mobile companion app

## 12. Screenshots

*(Insert screenshots here after running the application: Dashboard tab,
Shopping List tab with products added, Analytics tab with charts, and
the Summary tab.)*
