"""
web
---
Flask web edition of the Festive Budget Planner.

The desktop application (``main.py`` + ``gui.py``) is a Tkinter program, so it
cannot run on a hosting platform such as Render -- those platforms serve HTTP
traffic and have no display server for a GUI window.

This package therefore exposes the *same* application over the web. It does not
duplicate any business logic: every number, recommendation, chart and CSV file
produced here comes from the original modules at the repository root:

    models.py   -> Product / ShoppingPlan
    budget.py   -> BudgetManager (calculations + recommendation engine)
    storage.py  -> StorageManager (JSON sample plan, CSV export)
    charts.py   -> Matplotlib chart drawing
    utils.py    -> validation helpers, currency formatting, bank-offer math

``web/app.py`` is the Flask application; ``web/templates`` and ``web/static``
hold the browser interface.
"""
