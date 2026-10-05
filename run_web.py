"""
run_web.py
----------
Convenience launcher for the *web* edition of the Festive Budget Planner.

    python run_web.py

Then open http://127.0.0.1:5000 in a browser.

This is the development entry point. In production (Render) the app is served
by gunicorn using the start command declared in ``render.yaml``:

    gunicorn --bind 0.0.0.0:$PORT web.app:app

The desktop Tkinter edition is still available with ``python main.py``.
"""

import os

from web.app import app


def main() -> None:
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    print(f"Festive Budget Planner (web edition) -> http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop.\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
