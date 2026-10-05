"""
storage.py
----------
Handles all file input/output for the application:

    * Saving a ShoppingPlan to a JSON file
    * Loading a ShoppingPlan from a JSON file
    * Exporting the shopping list (+ a short summary) to a CSV file

All file operations are wrapped in try/except so a missing or corrupt
file never crashes the application -- errors are raised as a plain
Exception with a friendly message that the GUI can show in a messagebox.
"""

import json
import csv
import os
from typing import Optional

from models import ShoppingPlan


DEFAULT_DATA_PATH = os.path.join("data", "shopping_plan.json")
DEFAULT_EXPORT_PATH = os.path.join("exports", "shopping_summary.csv")


class StorageManager:
    """Responsible for reading/writing the shopping plan to disk."""

    # ------------------------------------------------------------------
    # JSON save / load
    # ------------------------------------------------------------------
    @staticmethod
    def save_plan(plan: ShoppingPlan, filepath: str = DEFAULT_DATA_PATH) -> None:
        """Save the given ShoppingPlan as a JSON file."""
        try:
            folder = os.path.dirname(filepath)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(plan.to_dict(), f, indent=4)
        except (OSError, IOError) as e:
            raise Exception(f"Could not save the plan to '{filepath}': {e}")

    @staticmethod
    def load_plan(filepath: str = DEFAULT_DATA_PATH) -> ShoppingPlan:
        """Load a ShoppingPlan from a JSON file. Raises Exception on failure."""
        if not os.path.exists(filepath):
            raise Exception(f"File not found: '{filepath}'.")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ShoppingPlan.from_dict(data)
        except json.JSONDecodeError:
            raise Exception(f"'{filepath}' is not a valid shopping plan file (bad JSON).")
        except (OSError, IOError) as e:
            raise Exception(f"Could not read '{filepath}': {e}")
        except (KeyError, TypeError, ValueError) as e:
            raise Exception(f"'{filepath}' has an unexpected/invalid structure: {e}")

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------
    @staticmethod
    def export_csv(plan: ShoppingPlan, filepath: str = DEFAULT_EXPORT_PATH) -> None:
        """Export the shopping list (plus a short summary) to a CSV file."""
        try:
            folder = os.path.dirname(filepath)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # --- Product table -------------------------------------
                writer.writerow([
                    "Product Name", "Category", "Original Price", "Discount %",
                    "Discounted Price", "Quantity", "Total Cost", "Priority"
                ])
                for p in plan.products:
                    writer.writerow([
                        p.name, p.category, f"{p.original_price:.2f}",
                        f"{p.discount:.2f}", f"{p.discounted_price:.2f}",
                        p.quantity, f"{p.total_cost:.2f}", p.priority
                    ])

                # --- Summary section -------------------------------------
                total_original = sum(p.total_original_cost for p in plan.products)
                total_planned = sum(p.total_cost for p in plan.products)
                total_savings = total_original - total_planned

                writer.writerow([])
                writer.writerow(["SUMMARY"])
                writer.writerow(["Total Budget", f"{plan.budget:.2f}"])
                writer.writerow(["Total Original Cost", f"{total_original:.2f}"])
                writer.writerow(["Total Planned Cost", f"{total_planned:.2f}"])
                writer.writerow(["Total Savings", f"{total_savings:.2f}"])
                writer.writerow(["Remaining Budget", f"{plan.budget - total_planned:.2f}"])
        except (OSError, IOError) as e:
            raise Exception(f"Could not export CSV to '{filepath}': {e}")
