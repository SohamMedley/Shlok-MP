# Amazon Great Indian Festival - Shopping Budget Planner

A Python application (Tkinter + Matplotlib) that helps a shopper plan
their budget for a big festival sale: add products, apply expected
discounts, track spending against a budget, see analytics, and export a
shopping summary.

It ships in **two editions** that share the same calculation modules: the
original **desktop** app (`python main.py`) and a **web** edition
(`python run_web.py`) that runs in any browser and deploys to Render with the
included Blueprint -- see sections 3 and 8, and [`DEPLOYMENT.md`](DEPLOYMENT.md).

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

---

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

**Web edition extras** (same logic, browser interface):

- Responsive dashboard that mirrors the desktop layout, palette and pages
- Your plan is auto-saved in the browser, so a refresh never loses it
- Live sale-price / total / savings preview while filling the product form
- Server-rendered Matplotlib charts (identical to the desktop Analytics tab)
- CSV export and JSON Save/Load as real file downloads and uploads
- Click-to-sort column headings, search, category filter and sort direction
- A printable report (browser Print -> PDF) on the Final Summary page
- Keyboard shortcuts: Ctrl+N add, Ctrl+S save, Ctrl+O load, Ctrl+E export,
  Delete remove
- `/healthz` health endpoint and a 26-test suite that checks desktop/web parity

---

## 3. Two Editions: Desktop and Web

The project now ships in **two editions** that share one set of calculation
modules:

| | Desktop edition | Web edition |
|---|---|---|
| Entry point | `python main.py` | `python run_web.py` (local) / gunicorn on Render |
| Interface | `gui.py` — Tkinter + ttk | `web/` — Flask, HTML/CSS/JS in the browser |
| Calculations | `budget.py` | **the same** `budget.py` |
| Data model | `models.py` | **the same** `models.py` |
| Save / load / CSV | `storage.py` | **the same** `storage.py` |
| Charts | `charts.py` embedded in the window | **the same** `charts.py`, exported as PNG |
| Validation | `utils.py` | **the same** `utils.py` |
| Where the plan lives | `data/shopping_plan.json` | the visitor's browser (`localStorage`) |

A Tkinter window cannot be shown by a cloud host, so the web edition exists to
make the project deployable (see section 8). No logic was copied: `web/app.py`
is a thin Flask layer that passes the browser's plan to the existing classes and
returns their answers, which means both editions always produce identical
numbers, statuses, recommendations, charts and CSV files.
`tests/test_web_app.py` enforces that parity.

The web interface keeps the desktop look and feel — dark sidebar, four pages
(Dashboard, Shopping List, Analytics, Final Summary), the same stat cards,
budget-health bar, priority breakdown, tips panel, product table with
search / filter / sort, the Add-Edit product form, the Bank / Coupon calculator
and the printable report.

---

## 4. Technologies Used

| Purpose            | Library                          |
|---------------------|-----------------------------------|
| Desktop GUI         | `tkinter`, `tkinter.ttk`          |
| Web GUI             | HTML5 / CSS3 / vanilla JavaScript |
| Web server (API)    | `flask`                           |
| Production server   | `gunicorn` (POSIX only — used by Render) |
| Charts              | `matplotlib` (embedded via `FigureCanvasTkAgg` on desktop, rendered to PNG for the web) |
| Data storage        | `json` (save/load plan), `localStorage` in the browser |
| Data export         | `csv` (export shopping list)      |
| Language            | Python 3 (pinned to 3.12 in `.python-version`) |
| Deployment          | Render Blueprint (`render.yaml`)  |

The desktop edition needs only `matplotlib`; the web edition adds `flask`
(and `gunicorn` in production). Everything else is from the Python standard
library — there is no database and no JavaScript build step.

---

## 5. Project Structure

```
Shlok-MP/
|
├── main.py           # Desktop entry point - creates the Tk root window and starts the app
├── gui.py            # BudgetPlannerApp - all Tkinter/ttk widgets and event handlers
├── budget.py         # BudgetManager - every calculation + the recommendation engine
├── models.py         # Product and ShoppingPlan data classes
├── storage.py        # StorageManager - JSON save/load and CSV export
├── charts.py         # Matplotlib chart-drawing functions (Tk window + PNG for the web)
├── utils.py          # Validation helpers, currency formatting, bank-offer math
|
├── run_web.py        # Web edition entry point - starts Flask on http://127.0.0.1:5000
├── web/
│   ├── __init__.py
│   ├── app.py        # Flask app: JSON API + the page route; reuses the modules above
│   ├── templates/
│   │   └── index.html    # Single-page interface (Dashboard / Shopping / Analytics / Summary)
│   └── static/
│       ├── css/styles.css    # Ports the Tkinter theme (same palette, cards, sidebar)
│       ├── js/app.js         # Client: localStorage plan, API calls, modals, charts
│       └── favicon.svg
|
├── tests/
│   └── test_web_app.py   # Endpoint tests + desktop/web parity checks (26 tests)
|
├── render.yaml       # Render Blueprint - one free Python web service
├── .python-version   # Pins Python 3.12 for reproducible builds
├── .gitignore        # Keeps __pycache__/, .venv/, exports/ out of git
├── requirements.txt  # Third-party dependencies (matplotlib, flask, gunicorn)
├── README.md         # This file
├── DEPLOYMENT.md     # Step-by-step Render deployment guide + troubleshooting
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
  Matplotlib `Figure` that `gui.py` embeds in the Analytics tab and
  that `web/app.py` saves as a PNG.
- **utils.py** -- input validation functions (`validate_price`,
  `validate_discount`, `validate_quantity`, `validate_budget`),
  currency formatting, and the bank-offer calculation.
- **run_web.py** -- starts the Flask web edition for local development.
- **web/app.py** -- the whole web backend: a stateless JSON API
  (`/api/analyze`, `/api/chart/<kind>`, `/api/export/csv`,
  `/api/bank-offer`, validation endpoints, `/healthz`) that delegates
  every calculation to the modules above.
- **web/templates/index.html**, **web/static/** -- the browser
  interface: sidebar navigation, four pages, modals, toasts and the
  client-side plan storage.
- **tests/test_web_app.py** -- smoke tests for each endpoint plus
  parity assertions against `BudgetManager` / `StorageManager` / `utils`.
- **render.yaml** -- Render Blueprint: one free Python web service with
  its build command, start command, health check and environment.

---

## 6. How to Install

```bash
pip install -r requirements.txt
```

This installs everything both editions need: `matplotlib` for the charts,
`flask` for the web API, and `gunicorn` for production (skipped automatically on
Windows, where it cannot run).

(`tkinter` ships with most standard Python installers on Windows/macOS and is
only needed for the desktop edition. On Debian/Ubuntu Linux, if it's missing,
install it separately with `sudo apt install python3-tk`.)

Only want the desktop app? `pip install matplotlib` is enough.

---

## 7. How to Run

**Desktop edition** (Tkinter window):

```bash
python main.py
```

A window titled **"Amazon Great Indian Festival - Shopping Budget
Planner"** will open at approximately 1200x750 pixels (resizable).

**Web edition** (browser):

```bash
python run_web.py
```

Then open <http://127.0.0.1:5000>. Everything works the same way — set a
budget, add products, watch the dashboard, open Analytics for the four charts,
and use Save Plan / Load Plan / Export CSV. Your plan is auto-saved in the
browser, so refreshing the page keeps it.

To reproduce the exact production command Render uses (Linux/macOS):

```bash
PORT=5000 gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 web.app:app
```

---

## 8. Deploying to Render

The web edition deploys to [Render](https://render.com) from the Blueprint file
`render.yaml` at the repository root. **Full guide, environment-variable table
and troubleshooting: [`DEPLOYMENT.md`](DEPLOYMENT.md).**

Short version:

1. Render dashboard -> **New** -> **Blueprint**.
2. Connect the repository `SohamMedley/Shlok-MP`.
3. **Branch**: pick the branch that contains `render.yaml`.
4. **Blueprint Path**: leave empty (it defaults to `render.yaml`).
5. Tick the **festive-budget-planner** service and click **Apply**.

The first build takes about 2-4 minutes. When the service shows **Live**, open
its `*.onrender.com` URL.

What the Blueprint provisions:

| Setting | Value |
|---|---|
| Service | `festive-budget-planner` (type `web`, runtime `python`) |
| Plan | `free` (512 MB / 0.1 CPU) — no database, no disk, no secrets |
| Region | `singapore` (closest to India) |
| Build | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 ... web.app:app` |
| Health check | `/healthz` |
| Python | 3.12 (from `.python-version`) |
| Environment | `MPLBACKEND=Agg`, `MPLCONFIGDIR=/tmp/matplotlib`, `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`, `FLASK_ENV=production`, `WEB_CONCURRENCY=1` |

Notes:

- The service is **stateless**: each request carries the plan in and gets the
  numbers out, so there is nothing to migrate, back up or configure. Every
  visitor's plan stays private in their own browser.
- A **free** web service sleeps after ~15 minutes without traffic; the first
  request afterwards takes ~30-50 seconds to wake it. Change `plan: free` to
  `plan: starter` in `render.yaml` for an always-on instance.
- Every push to the linked branch redeploys automatically, and edits to
  `render.yaml` are synced to the live service.
- `branch` is deliberately **not** set in `render.yaml`, so the same file works
  from a feature branch or from `main` after merging.

---

## 9. How It Works (Workflow)

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

---

## 10. Main Calculations

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

---

## 11. Sample Data

`data/shopping_plan.json` contains a sample budget (Rs 100,000) and
8 fictional example products (a laptop, a smartphone, headphones,
running shoes, a backpack, a smartwatch, a book set, and a stand
mixer) with example prices and discounts, clearly labeled "(Sample)"
in their names. Click **Load Sample Data** in the Shopping List tab
to load them at any time.

---

## 12. A Note on the Rupee Symbol

The app displays amounts as `Rs 1,234.56` rather than using the Unicode
rupee glyph (Rs) directly, because that glyph does not render reliably
in every Tkinter/Matplotlib font combination on every operating system
(it can appear as a blank box). This is a small, deliberate design
choice to keep the UI legible everywhere the app runs.

---

## 13. Tests

The test suite uses only the standard library:

```bash
python -m unittest discover -s tests -t . -v
```

26 tests cover every endpoint (`/`, `/healthz`, `/api/meta`, `/api/analyze`,
`/api/chart/<kind>`, `/api/export/csv`, `/api/bank-offer`, the validation
endpoints, error handling) and — more importantly — compare the API's output
against the original modules directly: totals, savings, remaining budget, usage
%, budget status, category and priority breakdowns, the recommendation list,
search + filter + sort order, per-product derived values, the exact CSV bytes
and the bank-offer maths. If the web edition ever drifted from the desktop
edition, these tests would fail.

---

## 14. Future Scope

- Real-time price-tracking APIs (would require an internet connection
  and API keys -- intentionally out of scope for this offline project)
- Direct Amazon product links / affiliate integration
- Historical price tracking and price-drop alerts
- Machine-learning based personalized recommendations
- Multi-user accounts and cloud-synced plans
- A mobile companion app

---

## 15. Screenshots

*(Insert screenshots here after running the application: Dashboard tab,
Shopping List tab with products added, Analytics tab with charts, and
the Summary tab.)*
