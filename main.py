"""
main.py
-------
Entry point for the Amazon Great Indian Festival Shopping Budget Planner.

Run this file to launch the application:

    python main.py

This file's only job is to create the Tkinter root window and start the
BudgetPlannerApp. All actual logic lives in the other modules:

    models.py   -> Product / ShoppingPlan data classes
    budget.py   -> BudgetManager (calculations + recommendations)
    storage.py  -> StorageManager (JSON save/load, CSV export)
    charts.py   -> Matplotlib chart-drawing functions
    utils.py    -> validation helpers + small utilities
    gui.py      -> BudgetPlannerApp (the Tkinter interface itself)
"""

import tkinter as tk
from tkinter import messagebox
import traceback

from gui import BudgetPlannerApp


def main():
    root = tk.Tk()
    try:
        app = BudgetPlannerApp(root)
        root.mainloop()
    except Exception as e:
        # A final safety net -- the app should not crash silently.
        traceback.print_exc()
        messagebox.showerror("Unexpected Error",
                              f"The application encountered an unexpected error:\n{e}")


if __name__ == "__main__":
    main()
