"""
tests/test_web_app.py
---------------------
Smoke tests + parity checks for the web edition.

The important idea here is *parity*: every number the Flask API returns is
compared against the value the original desktop modules (``BudgetManager``,
``StorageManager``, ``utils``) compute for the same plan. That way the web
edition can never silently drift away from ``gui.py``'s behaviour.

Run with the standard library test runner (no extra dependencies):

    python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ.setdefault("MPLBACKEND", "Agg")

import utils  # noqa: E402
from budget import BudgetManager  # noqa: E402
from models import Product, ShoppingPlan  # noqa: E402
from web.app import app as flask_app  # noqa: E402


SAMPLE_PLAN = {
    "budget": 100000,
    "products": [
        {"name": "Dell Inspiron Laptop (Sample)", "category": "Laptops",
         "original_price": 55000, "discount": 20, "quantity": 1, "priority": "High"},
        {"name": "Galaxy Smartphone (Sample)", "category": "Smartphones",
         "original_price": 25000, "discount": 15, "quantity": 1, "priority": "High"},
        {"name": "Wireless Headphones (Sample)", "category": "Electronics",
         "original_price": 4000, "discount": 30, "quantity": 1, "priority": "Medium"},
        {"name": "Running Shoes (Sample)", "category": "Fashion",
         "original_price": 3500, "discount": 25, "quantity": 1, "priority": "Medium"},
        {"name": "Travel Backpack (Sample)", "category": "Fashion",
         "original_price": 2200, "discount": 10, "quantity": 1, "priority": "Low"},
        {"name": "Fitness Smartwatch (Sample)", "category": "Electronics",
         "original_price": 6000, "discount": 35, "quantity": 1, "priority": "Medium"},
        {"name": "Assorted Book Set (Sample)", "category": "Books",
         "original_price": 1500, "discount": 5, "quantity": 2, "priority": "Low"},
        {"name": "Stand Mixer (Sample)", "category": "Home & Kitchen",
         "original_price": 8000, "discount": 18, "quantity": 1, "priority": "Medium"},
    ],
}


def build_plan(data):
    return ShoppingPlan.from_dict(data)


class WebAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        flask_app.config["TESTING"] = True
        cls.client = flask_app.test_client()

    def post(self, path, payload):
        return self.client.post(path, json=payload)

    # ------------------------------------------------------------------ pages
    def test_index_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("FESTIVE", html)
        self.assertIn("Planned Purchases", html)
        self.assertIn("Budget Health", html)

    def test_health_check(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])

    def test_static_assets_are_served(self):
        for path in ("/static/css/styles.css", "/static/js/app.js", "/favicon.ico"):
            response = self.client.get(path)
            try:
                self.assertEqual(response.status_code, 200, path)
                self.assertTrue(response.get_data())
            finally:
                response.close()   # avoid ResourceWarning on streamed files

    def test_meta_lists_the_standard_categories(self):
        data = self.client.get("/api/meta").get_json()
        self.assertEqual(data["categories"], utils.CATEGORIES)
        self.assertEqual(data["priorities"], utils.PRIORITIES)
        self.assertEqual(len(data["sample_plan"]["products"]), 8)

    # ------------------------------------------------------ parity: analysis
    def test_analysis_matches_budget_manager(self):
        plan = build_plan(SAMPLE_PLAN)
        manager = BudgetManager(plan)

        response = self.post("/api/analyze", {"plan": SAMPLE_PLAN})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        totals = data["totals"]
        self.assertAlmostEqual(totals["original_cost"], manager.total_original_cost(), places=2)
        self.assertAlmostEqual(totals["planned_cost"], manager.total_planned_cost(), places=2)
        self.assertAlmostEqual(totals["savings"], manager.total_savings(), places=2)
        self.assertAlmostEqual(totals["remaining_budget"], manager.remaining_budget(), places=2)
        self.assertAlmostEqual(totals["usage_percent"], manager.budget_usage_percent(), places=2)
        self.assertEqual(data["status"], manager.budget_status())
        self.assertEqual(data["is_over_budget"], manager.is_over_budget())
        self.assertEqual(data["recommendations"], manager.get_recommendations())
        self.assertEqual(data["count_by_priority"], manager.count_by_priority())

        for category, amount in manager.spending_by_category().items():
            self.assertAlmostEqual(data["spending_by_category"][category], amount, places=2)
        for priority, amount in manager.spending_by_priority().items():
            self.assertAlmostEqual(data["spending_by_priority"][priority], amount, places=2)

    def test_per_product_derived_values_match_the_model(self):
        plan = build_plan(SAMPLE_PLAN)
        data = self.post("/api/analyze", {"plan": SAMPLE_PLAN}).get_json()

        self.assertEqual(len(data["products"]), len(plan.products))
        for api_product, model_product in zip(data["products"], plan.products):
            self.assertAlmostEqual(api_product["discounted_price"], model_product.discounted_price, places=2)
            self.assertAlmostEqual(api_product["total_cost"], model_product.total_cost, places=2)
            self.assertAlmostEqual(api_product["total_savings"], model_product.total_savings, places=2)

    def test_search_filter_and_sort_match_budget_manager(self):
        plan = build_plan(SAMPLE_PLAN)
        manager = BudgetManager(plan)

        payload = {
            "plan": SAMPLE_PLAN,
            "search": "sample",
            "category": "Fashion",
            "sort_key": "Price",
            "reverse": True,
        }
        data = self.post("/api/analyze", payload).get_json()
        expected = BudgetManager.sort_products(
            manager.filtered_products(payload["search"], payload["category"]),
            payload["sort_key"], reverse=True,
        )
        self.assertEqual([p["name"] for p in data["visible_products"]],
                         [p.name for p in expected])
        # every visible row points at its position in the full plan
        for row in data["visible_products"]:
            self.assertEqual(plan.products[row["index"]].name, row["name"])

    def test_unknown_sort_key_falls_back_to_product_name(self):
        data = self.post("/api/analyze", {"plan": SAMPLE_PLAN, "sort_key": "Bogus"}).get_json()
        names = [p["name"] for p in data["visible_products"]]
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_over_budget_plan_is_flagged(self):
        plan = {"budget": 1000, "products": SAMPLE_PLAN["products"]}
        data = self.post("/api/analyze", {"plan": plan}).get_json()
        self.assertEqual(data["status"], "Over Budget")
        self.assertTrue(data["is_over_budget"])
        self.assertTrue(any("exceeds" in rec for rec in data["recommendations"]))

    def test_empty_plan(self):
        data = self.post("/api/analyze", {"plan": {"budget": 0, "products": []}}).get_json()
        self.assertEqual(data["product_count"], 0)
        self.assertEqual(data["recommendations"],
                         ["Add some products to see personalized recommendations."])

    # ---------------------------------------------------------- validation
    def test_invalid_payloads_are_rejected_with_friendly_messages(self):
        cases = [
            ({"plan": "nope"}, "JSON object"),
            ({"plan": {"budget": "abc"}}, "Budget must be a valid number."),
            ({"plan": {"budget": -5}}, "Budget cannot be negative."),
            ({"plan": {"products": [{"name": "x"}]}}, "Product #1 is invalid"),
            ("not-an-object", "JSON object"),
        ]
        for payload, expected in cases:
            response = self.post("/api/analyze", payload)
            self.assertEqual(response.status_code, 400, payload)
            self.assertIn(expected, response.get_json()["error"])

    def test_product_validation_reuses_utils(self):
        response = self.post("/api/products/validate", {
            "name": "  Smart TV  ", "category": "Electronics",
            "original_price": "50000", "discount": "20",
            "quantity": "2", "priority": "High",
        })
        self.assertEqual(response.status_code, 200)
        product = response.get_json()["product"]
        self.assertEqual(product["name"], "Smart TV")          # trimmed like the GUI
        self.assertEqual(product["discounted_price"], 40000)
        self.assertEqual(product["total_cost"], 80000)
        self.assertEqual(product["total_savings"], 20000)

    def test_product_validation_error_messages(self):
        base = {"name": "A", "category": "Electronics", "original_price": "10",
                "discount": "0", "quantity": "1", "priority": "High"}
        expectations = {
            "name": "Product Name cannot be empty.",
            "original_price": "Price must be greater than 0.",
            "discount": "Discount must be between 0 and 100.",
            "quantity": "Quantity must be at least 1.",
        }
        for field, message in expectations.items():
            payload = dict(base, **{field: "0" if field != "name" else ""})
            if field == "discount":
                payload["discount"] = "120"
            response = self.post("/api/products/validate", payload)
            self.assertEqual(response.status_code, 400, field)
            self.assertEqual(response.get_json()["error"], message)

    def test_budget_validation(self):
        self.assertEqual(self.post("/api/budget/validate", {"budget": "50000"}).get_json(),
                         {"ok": True, "budget": 50000.0, "reset": False})
        self.assertEqual(self.post("/api/budget/validate", {"budget": "reset"}).get_json(),
                         {"ok": True, "budget": 0.0, "reset": True})
        self.assertEqual(self.post("/api/budget/validate", {"budget": "-1"}).status_code, 400)
        self.assertEqual(self.post("/api/budget/validate", {"budget": ""}).status_code, 400)

    def test_uploaded_plan_is_normalised(self):
        messy = {"budget": "75000", "products": [
            {"name": "Kettle", "category": "Home & Kitchen",
             "original_price": "1200", "discount": "10", "quantity": "1",
             "priority": "Low", "extra_key": "ignored"},
        ]}
        data = self.post("/api/plan/validate", {"plan": messy}).get_json()
        self.assertEqual(data["plan"]["budget"], 75000.0)
        self.assertEqual(data["plan"]["products"][0]["original_price"], 1200.0)
        self.assertNotIn("extra_key", data["plan"]["products"][0])

    # ------------------------------------------------------------ bank offer
    def test_bank_offer_matches_utils(self):
        expected = utils.calculate_bank_offer(10000, 10, 500, 200)
        data = self.post("/api/bank-offer", {
            "subtotal": "10000", "bank_pct": "10",
            "max_discount": "500", "coupon": "200",
        }).get_json()
        self.assertEqual(data["bank_discount"], utils.format_currency(expected[0]))
        self.assertEqual(data["final_price"], utils.format_currency(expected[1]))
        self.assertEqual(data["total_discount"], utils.format_currency(expected[2]))
        self.assertTrue(data["capped"])   # 10% of 10000 is 1000, capped at 500

    def test_bank_offer_never_goes_negative(self):
        data = self.post("/api/bank-offer", {
            "subtotal": "100", "bank_pct": "100",
            "max_discount": "1000", "coupon": "500",
        }).get_json()
        self.assertEqual(data["final_price"], "Rs 0.00")

    def test_bank_offer_validation(self):
        self.assertEqual(self.post("/api/bank-offer", {"subtotal": "0"}).status_code, 400)
        self.assertEqual(self.post("/api/bank-offer",
                                   {"subtotal": "10", "bank_pct": "150"}).status_code, 400)
        self.assertEqual(self.post("/api/bank-offer",
                                   {"subtotal": "10", "coupon": "-5"}).status_code, 400)

    # ---------------------------------------------------------------- charts
    def test_charts_return_pngs(self):
        for kind in ("category", "budget", "price", "priority"):
            response = self.post("/api/chart/" + kind, {"plan": SAMPLE_PLAN})
            self.assertEqual(response.status_code, 200, kind)
            self.assertEqual(response.mimetype, "image/png")
            self.assertTrue(response.data.startswith(b"\x89PNG"), kind)
            self.assertGreater(len(response.data), 1000, kind)

    def test_charts_handle_an_empty_plan(self):
        for kind in ("category", "price"):
            response = self.post("/api/chart/" + kind,
                                 {"plan": {"budget": 0, "products": []}})
            self.assertEqual(response.status_code, 200, kind)
            self.assertTrue(response.data.startswith(b"\x89PNG"))

    def test_unknown_chart_kind_is_404(self):
        response = self.post("/api/chart/nope", {"plan": SAMPLE_PLAN})
        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown chart", response.get_json()["error"])

    # ------------------------------------------------------------------ CSV
    def test_csv_export_matches_storage_manager(self):
        import tempfile
        from storage import StorageManager

        response = self.post("/api/export/csv", {"plan": SAMPLE_PLAN})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("shopping_summary.csv", response.headers["Content-Disposition"])

        handle, path = tempfile.mkstemp(suffix=".csv")
        os.close(handle)
        try:
            StorageManager.export_csv(build_plan(SAMPLE_PLAN), path)
            with open(path, "r", encoding="utf-8", newline="") as fh:
                expected = fh.read()
        finally:
            os.remove(path)

        self.assertEqual(response.get_data(as_text=True), expected)
        self.assertIn("SUMMARY", expected)
        self.assertIn("Total Budget,100000.00", expected)

    # -------------------------------------------------------------- bundling
    def test_bundled_sample_file_matches_the_repo_copy(self):
        from storage import DEFAULT_DATA_PATH, StorageManager

        on_disk = StorageManager.load_plan(os.path.join(ROOT_DIR, DEFAULT_DATA_PATH))
        served = self.client.get("/api/sample").get_json()["plan"]
        self.assertEqual(json.loads(json.dumps(on_disk.to_dict())), served)
        self.assertEqual(len(served["products"]), 8)

    def test_api_404_is_json_but_pages_fall_back_to_the_app(self):
        self.assertEqual(self.client.get("/api/nope").status_code, 404)
        self.assertFalse(self.client.get("/api/nope").get_json()["ok"])

        page = self.client.get("/some/unknown/page")
        self.assertEqual(page.status_code, 404)
        self.assertIn("FESTIVE", page.get_data(as_text=True))


class LogicUnchangedTestCase(unittest.TestCase):
    """Guard rails for the original modules the web edition depends on."""

    def test_product_derived_values(self):
        product = Product("TV", "Electronics", 50000, 20, 2, "High")
        self.assertEqual(product.discounted_price, 40000)
        self.assertEqual(product.total_cost, 80000)
        self.assertEqual(product.total_savings, 20000)

    def test_round_trip_through_json(self):
        plan = build_plan(SAMPLE_PLAN)
        restored = ShoppingPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
        self.assertEqual(restored.budget, plan.budget)
        self.assertEqual(len(restored.products), len(plan.products))
        self.assertEqual(BudgetManager(restored).total_planned_cost(),
                         BudgetManager(plan).total_planned_cost())


if __name__ == "__main__":
    unittest.main(verbosity=2)
