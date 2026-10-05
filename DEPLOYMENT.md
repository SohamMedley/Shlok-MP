# Deploying the Festive Budget Planner to Render

This document explains how the project runs on [Render](https://render.com) and
how to deploy it in a few clicks with a **Blueprint**.

---

## 1. Why a web edition exists

The original application (`main.py` + `gui.py`) is a **Tkinter desktop program**.
It opens a native window and needs a display server, so it cannot run on any
cloud host — Render serves HTTP traffic and has no screen, no window manager and
no way to show a GUI to a visitor.

So this branch adds a **web edition** that runs on Render while keeping the
desktop app exactly as it was:

| | Desktop edition | Web edition |
|---|---|---|
| Entry point | `python main.py` | `gunicorn web.app:app` (Render) / `python run_web.py` (local) |
| Interface | `gui.py` (Tkinter/ttk) | `web/templates/index.html` + `web/static/` |
| Calculations | `budget.py` | **same** `budget.py` |
| Data model | `models.py` | **same** `models.py` |
| Save/load & CSV | `storage.py` | **same** `storage.py` |
| Charts | `charts.py` drawn into the Tk window | **same** `charts.py`, saved as PNG and sent to the browser |
| Validation | `utils.py` | **same** `utils.py` |
| Plan storage | `data/shopping_plan.json` on disk | the visitor's browser (`localStorage`) |

**No business logic was duplicated.** `web/app.py` is a thin Flask layer that
hands the browser's plan to the existing classes and returns their answers, so
the two editions can never disagree about a number, a status, a recommendation,
a chart or the CSV layout. `tests/test_web_app.py` asserts this parity on every
endpoint.

## 2. Architecture: why there is no database

Render's free tier gives an **ephemeral filesystem** (anything written is lost on
redeploy) and can run **more than one instance** (a file written by one is
invisible to the others). A shared server-side plan file would therefore be both
fragile and wrong — every visitor would see the same shopping list.

Instead the API is **stateless**:

```
browser (owns the plan in localStorage)
   │  POST /api/analyze   { plan, search, category, sort_key, reverse }
   ▼
Flask (web/app.py)
   │  ShoppingPlan.from_dict -> BudgetManager -> dict
   ▼
JSON: totals, status, breakdowns, recommendations, visible rows
```

Each request carries the plan in and gets the numbers out. That means:

- no database, no disk, no sessions → **free plan is enough**
- scales horizontally to any number of instances
- every visitor has a private plan, auto-saved in their own browser
- **Save Plan** / **Load Plan** still move real JSON files, and **Export CSV**
  produces a byte-identical file to the desktop app's export

## 3. What `render.yaml` creates

One web service and nothing else:

| Setting | Value | Why |
|---|---|---|
| `type` | `web` | Public HTTP service with an `onrender.com` URL |
| `runtime` | `python` | Native Python build — no Dockerfile to maintain |
| `plan` | `free` | 512 MB / 0.1 CPU is plenty (the worker idles at ~80 MB) |
| `region` | `singapore` | Closest Render region to India |
| `buildCommand` | `pip install --upgrade pip && pip install -r requirements.txt` | Installs matplotlib, flask, gunicorn |
| `startCommand` | `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 … web.app:app` | Render injects `PORT`; the app must bind `0.0.0.0:$PORT` |
| `healthCheckPath` | `/healthz` | Render marks the deploy live only once this returns 200 |
| `branch` | *(omitted on purpose)* | The service follows whichever branch the Blueprint instance is linked to |

Python version comes from `.python-version` (`3.12`), so builds are reproducible
instead of drifting with Render's default interpreter.

Environment variables set by the Blueprint:

| Variable | Value | Purpose |
|---|---|---|
| `MPLBACKEND` | `Agg` | Matplotlib must never look for a GUI backend on a headless server |
| `MPLCONFIGDIR` | `/tmp/matplotlib` | Writable font/cache directory |
| `PYTHONUNBUFFERED` | `1` | Logs appear in the Render dashboard immediately |
| `PYTHONDONTWRITEBYTECODE` | `1` | No `.pyc` writes to the app directory |
| `FLASK_ENV` | `production` | Disables debug behaviour |
| `WEB_CONCURRENCY` | `1` | Matches the single-worker start command |

No secrets, no `sync: false` prompts — applying the Blueprint needs **zero**
manual configuration.

## 4. Deploy with a Blueprint (recommended)

The Blueprint file lives at the **repository root** as `render.yaml`.

1. Push this branch to GitHub (already done — branch
   `arena/ba47ae3f-shlok-mp`).
2. Render dashboard → **New** → **Blueprint**.
3. Connect / choose the repository `SohamMedley/Shlok-MP`.
4. **Blueprint Name**: e.g. `Shlok-MP`.
5. **Branch**: select `arena/ba47ae3f-shlok-mp`
   *(or `main`, once this branch is merged — the file works from any branch)*.
6. **Blueprint Path**: leave empty (defaults to `render.yaml` at the root).
7. Click **Next**. The screen that previously said
   *"Blueprint file `render.yaml` not found on main branch"* will now list one
   service: **festive-budget-planner**. Tick it.
8. Click **Apply**.

The first build takes ~2–4 minutes (matplotlib is the slow part). When the
service flips to **Live**, open its `https://festive-budget-planner.onrender.com`
URL.

> **Free-tier cold start:** a free web service sleeps after ~15 minutes with no
> traffic; the first request after that takes ~30–50 seconds to wake it. This is
> normal. Set `plan: starter` in `render.yaml` (or change the instance type in
> the dashboard) for an always-on service.

Every later push to the linked branch re-deploys automatically, and any change
to `render.yaml` is synced to the live service.

## 5. Deploy manually instead (no Blueprint)

If you prefer a plain web service:

1. Render dashboard → **New** → **Web Service** → connect `SohamMedley/Shlok-MP`.
2. **Branch**: `arena/ba47ae3f-shlok-mp`
3. **Runtime**: Python
4. **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
5. **Start Command**:
   `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 web.app:app`
6. **Instance Type**: Free
7. Add the environment variables from the table in §3 (at minimum
   `MPLBACKEND=Agg`).
8. **Create Web Service**.

## 6. Run it locally

```bash
pip install -r requirements.txt

python run_web.py          # web edition  -> http://127.0.0.1:5000
python main.py             # desktop edition (Tkinter window)
```

To reproduce Render's exact production command locally (POSIX only):

```bash
PORT=5000 gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 web.app:app
```

## 7. Tests

`tests/test_web_app.py` runs with the standard library — no extra packages:

```bash
python -m unittest discover -s tests -t . -v
```

26 tests cover every endpoint and, most importantly, compare the API's output
against `BudgetManager`, `StorageManager` and `utils` directly: totals, savings,
budget status, usage %, category/priority breakdowns, recommendations,
search + filter + sort order, per-product derived values, the CSV bytes, and the
bank-offer maths.

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| *"Blueprint file `render.yaml` not found on main branch"* | Render is looking at a branch without the file | Pick the branch that contains `render.yaml`, or merge this branch into `main` |
| Deploy succeeds but the service never goes **Live** | Health check failing | Confirm `healthCheckPath` is `/healthz`; `curl <url>/healthz` should return `{"ok": true, …}` |
| *"Application failed to respond to port"* | App bound to the wrong interface/port | Keep `--bind 0.0.0.0:$PORT`; never hardcode a port |
| Build fails on `gunicorn` | Building on Windows locally | `requirements.txt` skips gunicorn on Windows; use `python run_web.py` |
| Charts show an error tile | Matplotlib cache not writable | `MPLBACKEND=Agg` and `MPLCONFIGDIR=/tmp/matplotlib` must be set |
| First request after a while is slow | Free-tier sleep | Expected; upgrade to `starter` if it matters |
| Numbers differ from the desktop app | Should be impossible | Run the test suite; the API calls the same `BudgetManager` |

## 9. Files added for deployment

```
render.yaml               # Render Blueprint (one free web service)
.python-version           # pins Python 3.12 for reproducible builds
.gitignore                # keeps __pycache__/, .venv/, exports/ out of git
run_web.py                # local launcher for the web edition
DEPLOYMENT.md             # this file
web/
├── __init__.py
├── app.py                # Flask app: API + page route, reuses the root modules
├── templates/index.html  # single-page interface (Dashboard / Shopping / Analytics / Summary)
└── static/
    ├── css/styles.css    # ports the Tkinter theme (same palette, cards, sidebar)
    ├── js/app.js         # client: localStorage plan, API calls, modals, charts
    └── favicon.svg
tests/
├── __init__.py
└── test_web_app.py       # endpoint + parity tests
```

Nothing in the original desktop application was modified: `main.py`, `gui.py`,
`budget.py`, `models.py`, `storage.py`, `charts.py`, `utils.py` and
`data/shopping_plan.json` are untouched. `requirements.txt` gained `flask` and
`gunicorn` alongside the existing `matplotlib`.
