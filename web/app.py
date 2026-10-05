"""
web/app.py
----------
Flask web edition of the Festive Budget Planner.

Design notes
~~~~~~~~~~~~
Render's free tier gives an *ephemeral* filesystem and may run more than one
instance, so the server deliberately keeps **no** shopping plan of its own.
Every browser owns its plan (auto-saved in ``localStorage``) and posts it to
the API whenever a calculation, chart or export is needed. The API is a pure
function:  plan in -> numbers out.

That keeps the deployment stateless (works on the free plan, scales to any
number of instances, no database) while reusing the original logic modules
verbatim:

    BudgetManager      -> all totals, status, breakdowns and recommendations
    StorageManager     -> sample plan loading and the CSV export layout
    charts.draw_*      -> the same four Matplotlib charts as the desktop app
    utils.validate_*   -> the same validation rules and error messages
    utils.calculate_bank_offer -> the bank / coupon calculator

Run locally:

    python -m web.app            # development server on http://127.0.0.1:5000

Run in production (what render.yaml does):

    gunicorn --bind 0.0.0.0:$PORT web.app:app
"""

from __future__ import annotations

import io
import os
import sys
import tempfile

# --------------------------------------------------------------------------
# Make the repository root importable, so the original modules (models.py,
# budget.py, ...) can be used unchanged from inside this package.
# --------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Matplotlib must never try to open a window on a headless server.
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

from flask import (  # noqa: E402
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

import charts  # noqa: E402
import utils  # noqa: E402
from budget import BudgetManager  # noqa: E402
from models import Product, ShoppingPlan  # noqa: E402
from storage import DEFAULT_DATA_PATH, StorageManager  # noqa: E402
from utils import ValidationError  # noqa: E402


SAMPLE_PLAN_PATH = os.path.join(ROOT_DIR, DEFAULT_DATA_PATH)

# The four analytics charts, keyed by the name used in the URL.
CHART_RENDERERS = {
    "category": charts.draw_category_pie_chart,
    "budget": charts.draw_budget_bar_chart,
    "price": charts.draw_price_comparison_chart,
    "priority": charts.draw_priority_chart,
}

SORT_OPTIONS = ["Product Name", "Price", "Discount", "Category", "Priority"]

# Guards against absurd payloads on a public URL.
MAX_PRODUCTS = 500


# ==========================================================================
# Helpers
# ==========================================================================

def _error(message: str, status: int = 400):
    """Return a consistent JSON error body."""
    return jsonify({"ok": False, "error": message}), status


def _get_payload() -> dict:
    """Read the JSON body, tolerating an empty/invalid one."""
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")
    return payload


def _plan_from_payload(payload: dict) -> ShoppingPlan:
    """
    Rebuild a ShoppingPlan from a posted JSON body.

    Accepts either the plan itself (``{"budget": ..., "products": [...]}``) or
    a wrapper (``{"plan": {...}, "search": ...}``), which is what the browser
    client sends together with its view options.
    """
    raw = payload.get("plan", payload)
    if not isinstance(raw, dict):
        raise ValidationError("The shopping plan must be a JSON object.")

    products = raw.get("products", []) or []
    if not isinstance(products, list):
        raise ValidationError("'products' must be a list.")
    if len(products) > MAX_PRODUCTS:
        raise ValidationError(f"A plan cannot hold more than {MAX_PRODUCTS} products.")

    try:
        budget = float(raw.get("budget", 0) or 0)
    except (TypeError, ValueError):
        raise ValidationError("Budget must be a valid number.")
    if budget < 0:
        raise ValidationError("Budget cannot be negative.")

    plan = ShoppingPlan(budget=budget)
    for index, item in enumerate(products, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Product #{index} must be a JSON object.")
        try:
            plan.add_product(Product.from_dict(item))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError(f"Product #{index} is invalid: {exc}")
    return plan


def _product_dict(product: Product) -> dict:
    """A product plus every derived value the interface displays."""
    data = product.to_dict()
    data.update({
        "discount_amount_per_unit": round(product.discount_amount_per_unit, 2),
        "discounted_price": round(product.discounted_price, 2),
        "total_original_cost": round(product.total_original_cost, 2),
        "total_cost": round(product.total_cost, 2),
        "total_savings": round(product.total_savings, 2),
    })
    return data


def _analysis(plan: ShoppingPlan, payload: dict) -> dict:
    """Run BudgetManager over the plan and shape the result as JSON."""
    manager = BudgetManager(plan)

    search = str(payload.get("search", "") or "")
    category = str(payload.get("category", "All") or "All")
    sort_key = str(payload.get("sort_key", "Product Name") or "Product Name")
    if sort_key not in SORT_OPTIONS:
        sort_key = "Product Name"
    reverse = bool(payload.get("reverse", False))

    filtered = manager.filtered_products(search_text=search, category=category)
    visible = BudgetManager.sort_products(filtered, sort_key, reverse=reverse)

    # Position of each product inside the full plan, so the browser can
    # edit/delete the right row after filtering and sorting have reordered it.
    index_by_product = {id(product): position
                        for position, product in enumerate(plan.products)}

    return {
        "ok": True,
        "budget": round(plan.budget, 2),
        "product_count": len(plan.products),
        "totals": {
            "original_cost": round(manager.total_original_cost(), 2),
            "planned_cost": round(manager.total_planned_cost(), 2),
            "savings": round(manager.total_savings(), 2),
            "remaining_budget": round(manager.remaining_budget(), 2),
            "discount_amount": round(manager.total_discount_amount(), 2),
            "usage_percent": round(manager.budget_usage_percent(), 2),
        },
        "status": manager.budget_status(),
        "is_over_budget": manager.is_over_budget(),
        "spending_by_category": {
            key: round(value, 2)
            for key, value in manager.spending_by_category().items()
        },
        "spending_by_priority": {
            key: round(value, 2)
            for key, value in manager.spending_by_priority().items()
        },
        "count_by_priority": manager.count_by_priority(),
        "recommendations": manager.get_recommendations(),
        "products": [_product_dict(p) for p in plan.products],
        "visible_products": [
            dict(_product_dict(p), index=index_by_product.get(id(p), -1)) for p in visible
        ],
    }


def _load_sample_plan() -> dict:
    """The bundled 8-product demo plan, as plain JSON."""
    plan = StorageManager.load_plan(SAMPLE_PLAN_PATH)
    return plan.to_dict()


# ==========================================================================
# Application factory
# ==========================================================================

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.json.sort_keys = False
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB is plenty

    # ---------------------------------------------------------------- pages
    @app.get("/")
    def index():
        return render_template(
            "index.html",
            categories=utils.CATEGORIES,
            priorities=utils.PRIORITIES,
            sort_options=SORT_OPTIONS,
            chart_kinds=list(CHART_RENDERERS),
        )

    @app.get("/healthz")
    def healthz():
        """Health check used by Render (see healthCheckPath in render.yaml)."""
        return jsonify({
            "ok": True,
            "status": "healthy",
            "service": "festive-budget-planner",
            "python": sys.version.split()[0],
        })

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.svg",
                                   mimetype="image/svg+xml")

    # ----------------------------------------------------------------- meta
    @app.get("/api/meta")
    def api_meta():
        """Dropdown values + the bundled sample plan, in one round trip."""
        try:
            sample = _load_sample_plan()
        except Exception:
            sample = {"budget": 0, "products": []}

        return jsonify({
            "ok": True,
            "categories": utils.CATEGORIES,
            "priorities": utils.PRIORITIES,
            "sort_options": SORT_OPTIONS,
            "chart_kinds": list(CHART_RENDERERS),
            "sample_plan": sample,
            "max_products": MAX_PRODUCTS,
        })

    @app.get("/api/sample")
    def api_sample():
        try:
            return jsonify({"ok": True, "plan": _load_sample_plan()})
        except Exception as exc:  # missing/corrupt bundled file
            return _error(f"Could not load the sample plan: {exc}", 500)

    # -------------------------------------------------------------- analyze
    @app.post("/api/analyze")
    def api_analyze():
        """The main endpoint: plan (+ view options) in, dashboard data out."""
        try:
            payload = _get_payload()
            return jsonify(_analysis(_plan_from_payload(payload), payload))
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:  # never leak a stack trace to the browser
            app.logger.exception("analyze failed")
            return _error(f"Could not analyse the plan: {exc}", 500)

    # ------------------------------------------------------- product form
    @app.post("/api/products/validate")
    def api_validate_product():
        """
        Validate the raw strings typed into the Add/Edit Product form using
        the very same helpers the desktop GUI uses, so both editions reject
        identical input with identical wording.
        """
        try:
            payload = _get_payload()
            product = Product(
                name=utils.validate_non_empty_text(payload.get("name", ""), "Product Name"),
                category=utils.validate_non_empty_text(payload.get("category", ""), "Category"),
                original_price=utils.validate_price(payload.get("original_price", ""), "Price"),
                discount=utils.validate_discount(payload.get("discount", "")),
                quantity=utils.validate_quantity(payload.get("quantity", "")),
                priority=utils.validate_non_empty_text(payload.get("priority", ""), "Priority"),
            )
            return jsonify({"ok": True, "product": _product_dict(product)})
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            return _error(str(exc))

    @app.post("/api/budget/validate")
    def api_validate_budget():
        """Validate the budget field exactly like the desktop app does."""
        try:
            payload = _get_payload()
            value = payload.get("budget", "")
            if value in (None, ""):
                raise ValidationError("Budget cannot be empty.")
            if str(value).strip().lower() in {"reset", "0"}:
                return jsonify({"ok": True, "budget": 0.0, "reset": True})
            return jsonify({"ok": True, "budget": utils.validate_budget(value),
                            "reset": False})
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            return _error(str(exc))

    @app.post("/api/plan/validate")
    def api_validate_plan():
        """
        Check a JSON file the user wants to load, and hand back a normalised
        plan (so stray keys, string numbers, etc. are cleaned up).
        """
        try:
            payload = _get_payload()
            raw = payload.get("plan", payload)
            plan = _plan_from_payload({"plan": raw})
            return jsonify({"ok": True, "plan": plan.to_dict()})
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            return _error(f"That file is not a valid shopping plan: {exc}")

    # --------------------------------------------------------------- charts
    @app.post("/api/chart/<kind>")
    def api_chart(kind: str):
        """Render one Matplotlib chart (charts.py) and return it as a PNG."""
        renderer = CHART_RENDERERS.get(kind)
        if renderer is None:
            return _error(
                f"Unknown chart '{kind}'. Available: {', '.join(CHART_RENDERERS)}.",
                404,
            )
        try:
            payload = _get_payload()
            plan = _plan_from_payload(payload)
            manager = BudgetManager(plan)

            width = float(payload.get("width", 6.0) or 6.0)
            height = float(payload.get("height", 4.0) or 4.0)
            dpi = int(payload.get("dpi", 110) or 110)
            width = min(max(width, 2.0), 14.0)
            height = min(max(height, 2.0), 14.0)
            dpi = min(max(dpi, 60), 200)

            figure = Figure(figsize=(width, height), dpi=dpi)
            renderer(figure, manager)

            buffer = io.BytesIO()
            figure.savefig(buffer, format="png", bbox_inches="tight",
                           facecolor="white")
            buffer.seek(0)

            return Response(buffer.getvalue(), mimetype="image/png",
                            headers={"Cache-Control": "no-store"})
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            app.logger.exception("chart %s failed", kind)
            return _error(f"Could not draw the chart: {exc}", 500)

    # --------------------------------------------------------------- export
    @app.post("/api/export/csv")
    def api_export_csv():
        """
        Produce the shopping-list CSV. StorageManager.export_csv writes to a
        path, so we let it write to a temporary file and stream that back --
        the CSV layout stays identical to the desktop app's export.
        """
        tmp_path = None
        try:
            payload = _get_payload()
            plan = _plan_from_payload(payload)

            handle, tmp_path = tempfile.mkstemp(suffix=".csv", prefix="shopping_summary_")
            os.close(handle)
            StorageManager.export_csv(plan, tmp_path)

            with open(tmp_path, "r", encoding="utf-8", newline="") as handle:
                content = handle.read()

            return Response(
                content,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": 'attachment; filename="shopping_summary.csv"',
                    "Cache-Control": "no-store",
                },
            )
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            app.logger.exception("csv export failed")
            return _error(f"Could not export the CSV: {exc}", 500)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    # -------------------------------------------------------- bank calculator
    @app.post("/api/bank-offer")
    def api_bank_offer():
        """The Bank / Coupon calculator, using utils.calculate_bank_offer."""
        try:
            payload = _get_payload()
            subtotal = utils.validate_price(payload.get("subtotal", ""), "Subtotal")

            try:
                bank_pct = float(payload.get("bank_pct", 0) or 0)
                max_discount = float(payload.get("max_discount", 0) or 0)
                coupon = float(payload.get("coupon", 0) or 0)
            except (TypeError, ValueError):
                raise ValidationError("Please enter valid numbers in all fields.")

            if not 0 <= bank_pct <= 100:
                raise ValidationError("Bank discount % must be between 0 and 100.")
            if max_discount < 0 or coupon < 0:
                raise ValidationError("Discount amounts cannot be negative.")

            actual_bank_discount, final_price, total_discount = utils.calculate_bank_offer(
                subtotal, bank_pct, max_discount, coupon
            )
            return jsonify({
                "ok": True,
                "subtotal": utils.format_currency(subtotal),
                "bank_discount": utils.format_currency(actual_bank_discount),
                "total_discount": utils.format_currency(total_discount),
                "final_price": utils.format_currency(final_price),
                "capped": actual_bank_discount < subtotal * (bank_pct / 100) - 1e-9,
            })
        except ValidationError as exc:
            return _error(str(exc))
        except Exception as exc:
            return _error(str(exc))

    # ------------------------------------------------------------ fallbacks
    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return _error("Endpoint not found.", 404)
        return render_template("index.html",
                               categories=utils.CATEGORIES,
                               priorities=utils.PRIORITIES,
                               sort_options=SORT_OPTIONS,
                               chart_kinds=list(CHART_RENDERERS)), 404

    @app.errorhandler(413)
    def too_large(_):
        return _error("That plan is too large to upload (limit is 2 MB).", 413)

    @app.errorhandler(500)
    def server_error(_):
        return _error("Internal server error.", 500)

    return app


# Module-level app: this is what `gunicorn web.app:app` serves.
app = create_app()


if __name__ == "__main__":
    # Local development only -- Render uses the gunicorn start command.
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
