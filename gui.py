"""
Modern GUI for the Amazon Great Indian Festival Shopping Budget Planner.

This file keeps the original application architecture:
- budget.py     -> calculations/recommendations
- models.py     -> Product / ShoppingPlan
- storage.py    -> JSON save/load + CSV export
- charts.py     -> Matplotlib analytics
- utils.py      -> validation + formatting

The interface has been completely redesigned as a modern desktop dashboard
while preserving the application's existing functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import traceback

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from models import Product, ShoppingPlan
from budget import BudgetManager
from storage import StorageManager, DEFAULT_DATA_PATH
import charts
import utils
from utils import ValidationError


# ---------------------------------------------------------------------------
# MODERN THEME
# ---------------------------------------------------------------------------
COLOR_BG = "#F7F8FC"                 # Soft premium background
COLOR_SURFACE = "#FFFFFF"            # Cards / panels
COLOR_SIDEBAR = "#111827"            # Deep navy-black
COLOR_SIDEBAR_HOVER = "#1F2937"      # Sidebar hover

COLOR_TEXT = "#111827"               # Primary text
COLOR_MUTED = "#64748B"              # Secondary text
COLOR_BORDER = "#E2E8F0"             # Subtle borders

# Primary brand — festive orange
COLOR_ACCENT = "#FF6B35"
COLOR_ACCENT_DARK = "#E85D2A"

# Secondary brand — modern indigo
COLOR_BLUE = "#6366F1"
COLOR_PURPLE = "#6366F1"             # Compatibility alias; unified to indigo

# Semantic colors
COLOR_GREEN = "#10B981"              # Success / savings
COLOR_YELLOW = "#F59E0B"             # Warning
COLOR_ORANGE = "#F59E0B"             # Warning / attention
COLOR_RED = "#EF4444"                # Error / danger

# Soft semantic backgrounds
COLOR_SOFT_GREEN = "#ECFDF5"
COLOR_SOFT_YELLOW = "#FFFBEB"
COLOR_SOFT_RED = "#FEF2F2"
COLOR_SOFT_BLUE = "#EEF2FF"

FONT = "Segoe UI"
FONT_TITLE = (FONT, 24, "bold")
FONT_H1 = (FONT, 20, "bold")
FONT_H2 = (FONT, 15, "bold")
FONT_H3 = (FONT, 12, "bold")
FONT_BODY = (FONT, 10)
FONT_BODY_BOLD = (FONT, 10, "bold")
FONT_SMALL = (FONT, 9)
FONT_CARD = (FONT, 19, "bold")
FONT_BIG = (FONT, 27, "bold")


class BudgetPlannerApp:
    """Modern desktop GUI for the shopping budget planner."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Festive Budget — Shopping Budget Planner")
        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)
        self.root.configure(bg=COLOR_BG)

        self.plan = ShoppingPlan(budget=0.0)
        self.manager = BudgetManager(self.plan)
        self.editing_index = None
        self.current_page = "dashboard"
        self.product_window = None
        self._status_after_id = None

        self._configure_styles()
        self._build_shell()
        self._build_pages()
        self._bind_shortcuts()
        self.show_page("dashboard")
        self.refresh_all()

    # ======================================================================
    # STYLE
    # ======================================================================

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=COLOR_BG)
        style.configure("Surface.TFrame", background=COLOR_SURFACE)
        style.configure("TLabel", background=COLOR_BG, foreground=COLOR_TEXT,
                        font=FONT_BODY)
        style.configure("Surface.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_TEXT, font=FONT_BODY)
        style.configure("Muted.TLabel", background=COLOR_BG,
                        foreground=COLOR_MUTED, font=FONT_SMALL)
        style.configure("SurfaceMuted.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_MUTED, font=FONT_SMALL)
        style.configure("PageTitle.TLabel", background=COLOR_BG,
                        foreground=COLOR_TEXT, font=FONT_TITLE)
        style.configure("PageSubtitle.TLabel", background=COLOR_BG,
                        foreground=COLOR_MUTED, font=FONT_BODY)
        style.configure("Section.TLabel", background=COLOR_BG,
                        foreground=COLOR_TEXT, font=FONT_H2)
        style.configure("SurfaceSection.TLabel", background=COLOR_SURFACE,
                        foreground=COLOR_TEXT, font=FONT_H2)

        style.configure(
            "Primary.TButton",
            background=COLOR_ACCENT,
            foreground="white",
            font=FONT_BODY_BOLD,
            padding=(15, 9),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLOR_ACCENT_DARK), ("pressed", COLOR_ACCENT_DARK)],
            foreground=[("disabled", "#CBD5E1")],
        )

        style.configure(
            "Secondary.TButton",
            background="#FFFFFF",
            foreground=COLOR_TEXT,
            font=FONT_BODY_BOLD,
            padding=(13, 8),
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#F1F5F9"), ("pressed", "#E2E8F0")],
        )

        style.configure(
            "Danger.TButton",
            background="#FFFFFF",
            foreground=COLOR_RED,
            font=FONT_BODY_BOLD,
            padding=(13, 8),
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Danger.TButton",
            background=[("active", COLOR_SOFT_RED)],
        )

        style.configure(
            "TEntry",
            fieldbackground="#FFFFFF",
            foreground=COLOR_TEXT,
            insertcolor=COLOR_TEXT,
            bordercolor=COLOR_BORDER,
            padding=8,
        )
        style.map("TEntry", bordercolor=[("focus", COLOR_ACCENT)])

        style.configure(
            "TCombobox",
            fieldbackground="#FFFFFF",
            foreground=COLOR_TEXT,
            padding=7,
        )

        style.configure(
            "Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground=COLOR_TEXT,
            rowheight=38,
            font=FONT_BODY,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", COLOR_SOFT_BLUE)],
            foreground=[("selected", COLOR_TEXT)],
        )
        style.configure(
            "Treeview.Heading",
            background="#F8FAFC",
            foreground=COLOR_MUTED,
            font=(FONT, 9, "bold"),
            padding=(8, 10),
            relief="flat",
        )
        style.map("Treeview.Heading", background=[("active", "#F1F5F9")])

        style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_ACCENT,
            borderwidth=0,
            thickness=12,
        )
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_GREEN,
            borderwidth=0,
            thickness=12,
        )
        style.configure(
            "Yellow.Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_YELLOW,
            borderwidth=0,
            thickness=12,
        )
        style.configure(
            "Orange.Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_ORANGE,
            borderwidth=0,
            thickness=12,
        )
        style.configure(
            "Red.Horizontal.TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_RED,
            borderwidth=0,
            thickness=12,
        )

    # ======================================================================
    # APP SHELL / NAVIGATION
    # ======================================================================

    def _build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=COLOR_SIDEBAR, width=235)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.root, bg=COLOR_BG)
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_topbar()

        self.page_container = tk.Frame(self.content, bg=COLOR_BG)
        self.page_container.pack(fill="both", expand=True, padx=28, pady=(10, 24))

        self.status_bar = tk.Frame(self.root, bg="#FFFFFF",
                                   highlightbackground=COLOR_BORDER,
                                   highlightthickness=1, height=30)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_bar,
            text="● Ready",
            bg="#FFFFFF",
            fg=COLOR_MUTED,
            font=(FONT, 9),
            anchor="w",
        )
        self.status_label.pack(side="left", padx=14)

        self.product_count_label = tk.Label(
            self.status_bar,
            text="0 products",
            bg="#FFFFFF",
            fg=COLOR_MUTED,
            font=(FONT, 9),
            anchor="e",
        )
        self.product_count_label.pack(side="right", padx=14)

    def _build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(26, 30))

        tk.Label(
            brand, text="🛍", bg=COLOR_SIDEBAR, fg="white",
            font=(FONT, 26)
        ).pack(side="left", padx=(0, 10))

        brand_text = tk.Frame(brand, bg=COLOR_SIDEBAR)
        brand_text.pack(side="left")

        tk.Label(
            brand_text, text="FESTIVE", bg=COLOR_SIDEBAR,
            fg="white", font=(FONT, 13, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand_text, text="BUDGET", bg=COLOR_SIDEBAR,
            fg="#CBD5E1", font=(FONT, 10, "bold")
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "⌂", "Dashboard"),
            ("shopping", "🛒", "Shopping List"),
            ("analytics", "▥", "Analytics"),
            ("summary", "▤", "Final Summary"),
        ]

        for page, icon, text in nav_items:
            self._make_nav_button(page, icon, text)

        spacer = tk.Frame(self.sidebar, bg=COLOR_SIDEBAR)
        spacer.pack(fill="both", expand=True)

        quick = tk.Frame(self.sidebar, bg="#172033")
        quick.pack(fill="x", padx=14, pady=(0, 12))

        tk.Label(
            quick, text="QUICK ACTIONS", bg="#172033",
            fg="#94A3B8", font=(FONT, 8, "bold")
        ).pack(anchor="w", padx=12, pady=(12, 7))

        self._make_sidebar_action(quick, "＋  Add Product", self.open_product_form)
        self._make_sidebar_action(quick, "↥  Save Plan", self.on_save_plan)
        self._make_sidebar_action(quick, "↧  Load Plan", self.on_load_plan)

        tk.Label(
            self.sidebar,
            text="Student Project\nOffline planning tool",
            bg=COLOR_SIDEBAR,
            fg="#94A3B8",
            font=(FONT, 8),
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 18))

    def _make_nav_button(self, page, icon, text):
        button = tk.Button(
            self.sidebar,
            text=f"  {icon}    {text}",
            command=lambda p=page: self.show_page(p),
            bg=COLOR_SIDEBAR,
            fg="#CBD5E1",
            activebackground=COLOR_SIDEBAR_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            anchor="w",
            padx=18,
            pady=12,
            font=(FONT, 10, "bold"),
            cursor="hand2",
        )
        button.pack(fill="x", padx=10, pady=2)
        self.nav_buttons[page] = button

    def _make_sidebar_action(self, parent, text, command):
        button = tk.Button(
            parent, text=text, command=command,
            bg="#172033", fg="#E2E8F0",
            activebackground="#253247", activeforeground="white",
            relief="flat", bd=0, anchor="w",
            padx=12, pady=7, font=(FONT, 9), cursor="hand2"
        )
        button.pack(fill="x", padx=4, pady=1)

    def _build_topbar(self):
        top = tk.Frame(self.content, bg=COLOR_BG, height=82)
        top.pack(fill="x", padx=28, pady=(18, 0))
        top.pack_propagate(False)

        left = tk.Frame(top, bg=COLOR_BG)
        left.pack(side="left", fill="y")

        self.top_title = tk.Label(
            left, text="Dashboard", bg=COLOR_BG, fg=COLOR_TEXT,
            font=FONT_TITLE
        )
        self.top_title.pack(anchor="w")

        self.top_subtitle = tk.Label(
            left,
            text="Plan your festival shopping with confidence.",
            bg=COLOR_BG, fg=COLOR_MUTED, font=FONT_BODY
        )
        self.top_subtitle.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(top, bg=COLOR_BG)
        right.pack(side="right", fill="y")

        self.header_budget_label = tk.Label(
            right, text="Budget  •  Rs 0.00",
            bg=COLOR_SOFT_BLUE, fg=COLOR_BLUE,
            font=(FONT, 9, "bold"), padx=14, pady=8
        )
        self.header_budget_label.pack(side="right", pady=15)

    def show_page(self, page):
        if page not in self.pages:
            return

        for name, frame in self.pages.items():
            frame.pack_forget()

        self.pages[page].pack(fill="both", expand=True)

        titles = {
            "dashboard": ("Dashboard", "Your complete shopping budget overview."),
            "shopping": ("Shopping List", "Add, organize and manage planned purchases."),
            "analytics": ("Analytics", "Understand where your shopping budget is going."),
            "summary": ("Final Summary", "A clean overview of your complete shopping plan."),
        }
        title, subtitle = titles[page]
        self.top_title.config(text=title)
        self.top_subtitle.config(text=subtitle)

        for name, button in self.nav_buttons.items():
            if name == page:
                button.config(bg=COLOR_ACCENT, fg="white",
                              activebackground=COLOR_ACCENT_DARK)
            else:
                button.config(bg=COLOR_SIDEBAR, fg="#CBD5E1",
                              activebackground=COLOR_SIDEBAR_HOVER)

        self.current_page = page

        if page == "analytics":
            self.root.after(50, self.refresh_charts)
        elif page == "summary":
            self.refresh_summary()

    def _build_pages(self):
        self.pages = {}
        for name in ("dashboard", "shopping", "analytics", "summary"):
            self.pages[name] = tk.Frame(self.page_container, bg=COLOR_BG)

        self._build_dashboard_page()
        self._build_shopping_page()
        self._build_analytics_page()
        self._build_summary_page()

    # ======================================================================
    # COMMON UI HELPERS
    # ======================================================================

    def _card(self, parent, padx=0, pady=0):
        frame = tk.Frame(
            parent,
            bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
        )
        if padx or pady:
            frame.pack(padx=padx, pady=pady)
        return frame

    def _make_stat_card(self, parent, column, title, value, color, subtitle):
        card = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1
        )
        card.grid(row=0, column=column, sticky="nsew", padx=6)

        tk.Frame(card, bg=color, height=4).pack(fill="x", side="top")

        body = tk.Frame(card, bg=COLOR_SURFACE)
        body.pack(fill="both", expand=True, padx=16, pady=13)

        tk.Label(
            body, text=title.upper(), bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 8, "bold")
        ).pack(anchor="w")

        label = tk.Label(
            body, text=value, bg=COLOR_SURFACE,
            fg=color, font=FONT_CARD
        )
        label.pack(anchor="w", pady=(6, 2))

        tk.Label(
            body, text=subtitle, bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 8)
        ).pack(anchor="w")

        return label

    def _section_header(self, parent, title, subtitle=None):
        header = tk.Frame(parent, bg=COLOR_SURFACE)
        header.pack(fill="x", padx=18, pady=(16, 10))

        tk.Label(
            header, text=title, bg=COLOR_SURFACE,
            fg=COLOR_TEXT, font=FONT_H2
        ).pack(side="left")

        if subtitle:
            tk.Label(
                header, text=subtitle, bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 9)
            ).pack(side="left", padx=10, pady=(3, 0))

        return header

    def _set_status(self, message, kind="normal"):
        if self._status_after_id:
            try:
                self.root.after_cancel(self._status_after_id)
            except tk.TclError:
                pass

        colors = {
            "success": COLOR_GREEN,
            "warning": COLOR_ORANGE,
            "error": COLOR_RED,
            "normal": COLOR_MUTED,
        }
        symbol = {
            "success": "✓",
            "warning": "⚠",
            "error": "✕",
            "normal": "●",
        }
        self.status_label.config(
            text=f"{symbol.get(kind, '●')} {message}",
            fg=colors.get(kind, COLOR_MUTED),
        )

        self._status_after_id = self.root.after(
            5000, lambda: self.status_label.config(
                text="● Ready", fg=COLOR_MUTED
            )
        )

    # ======================================================================
    # DASHBOARD
    # ======================================================================

    def _build_dashboard_page(self):
        page = self.pages["dashboard"]

        budget_card = tk.Frame(
            page, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        budget_card.pack(fill="x", pady=(0, 14))

        left = tk.Frame(budget_card, bg=COLOR_SURFACE)
        left.pack(side="left", fill="x", expand=True, padx=18, pady=16)

        tk.Label(
            left, text="SHOPPING BUDGET", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 8, "bold")
        ).pack(anchor="w")

        budget_form = tk.Frame(left, bg=COLOR_SURFACE)
        budget_form.pack(fill="x", pady=(7, 0))

        self.budget_entry = ttk.Entry(budget_form, width=20,
                                      font=(FONT, 11))
        self.budget_entry.pack(side="left", ipady=2)

        ttk.Button(
            budget_form, text="Set Budget",
            style="Primary.TButton",
            command=self.on_set_budget
        ).pack(side="left", padx=8)

        ttk.Button(
            budget_form, text="Reset",
            style="Secondary.TButton",
            command=self.on_reset_budget
        ).pack(side="left")

        tk.Label(
            budget_card,
            text="Set your spending limit first, then build your shopping list.",
            bg=COLOR_SURFACE, fg=COLOR_MUTED,
            font=(FONT, 9), justify="left"
        ).pack(side="right", padx=18)

        cards = tk.Frame(page, bg=COLOR_BG)
        cards.pack(fill="x", pady=(0, 14))
        for i in range(4):
            cards.columnconfigure(i, weight=1)

        self.card_budget_val = self._make_stat_card(
            cards, 0, "Total Budget", "Rs 0.00", COLOR_ACCENT, "Your spending limit"
        )
        self.card_planned_val = self._make_stat_card(
            cards, 1, "Planned Spending", "Rs 0.00", COLOR_BLUE, "Expected sale cost"
        )
        self.card_remaining_val = self._make_stat_card(
            cards, 2, "Remaining", "Rs 0.00", COLOR_GREEN, "Available to spend"
        )
        self.card_savings_val = self._make_stat_card(
            cards, 3, "Savings", "Rs 0.00", COLOR_PURPLE, "Expected discount savings"
        )

        lower = tk.Frame(page, bg=COLOR_BG)
        lower.pack(fill="both", expand=True)
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=2)
        lower.rowconfigure(0, weight=1)

        self._build_budget_health(lower)
        self._build_recommendations(lower)

        bottom = tk.Frame(page, bg=COLOR_BG)
        bottom.pack(fill="x", pady=(14, 0))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        self._build_priority_panel(bottom)
        self._build_quick_tips_panel(bottom)

    def _build_budget_health(self, parent):
        box = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self._section_header(
            box, "Budget Health", "Live spending utilization"
        )

        inner = tk.Frame(box, bg=COLOR_SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        row = tk.Frame(inner, bg=COLOR_SURFACE)
        row.pack(fill="x")

        self.status_badge = tk.Label(
            row, text="SAFE", bg=COLOR_SOFT_GREEN, fg=COLOR_GREEN,
            font=(FONT, 9, "bold"), padx=12, pady=6
        )
        self.status_badge.pack(side="left")

        self.usage_label = tk.Label(
            row, text="0.0% used", bg=COLOR_SURFACE,
            fg=COLOR_TEXT, font=(FONT, 11, "bold")
        )
        self.usage_label.pack(side="right")

        self.progress_bar = ttk.Progressbar(
            inner, orient="horizontal", mode="determinate",
            maximum=100, style="Green.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x", pady=(15, 8))

        self.budget_health_text = tk.Label(
            inner, text="Set a budget to begin.",
            bg=COLOR_SURFACE, fg=COLOR_MUTED,
            font=(FONT, 10), anchor="w"
        )
        self.budget_health_text.pack(fill="x")

        self.over_budget_label = tk.Label(
            inner, text="", bg=COLOR_SURFACE, fg=COLOR_RED,
            font=(FONT, 10, "bold"), anchor="w"
        )
        self.over_budget_label.pack(fill="x", pady=(8, 0))

    def _build_recommendations(self, parent):
        box = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        box.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        self._section_header(
            box, "Smart Insights", "Rule-based recommendations"
        )

        self.recommendations_frame = tk.Frame(box, bg=COLOR_SURFACE)
        self.recommendations_frame.pack(
            fill="both", expand=True, padx=18, pady=(0, 12)
        )

    def _build_priority_panel(self, parent):
        box = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        box.grid(row=0, column=0, sticky="ew", padx=(0, 7))

        self._section_header(box, "Priority Breakdown")

        self.priority_rows = {}
        data = [
            ("High", COLOR_RED),
            ("Medium", COLOR_YELLOW),
            ("Low", COLOR_GREEN),
        ]

        for priority, color in data:
            row = tk.Frame(box, bg=COLOR_SURFACE)
            row.pack(fill="x", padx=18, pady=3)

            tk.Label(
                row, text=priority, bg=COLOR_SURFACE,
                fg=COLOR_TEXT, font=(FONT, 9, "bold"), width=9, anchor="w"
            ).pack(side="left")

            amount = tk.Label(
                row, text="Rs 0.00", bg=COLOR_SURFACE,
                fg=color, font=(FONT, 9, "bold")
            )
            amount.pack(side="right")

            bar = ttk.Progressbar(
                row, orient="horizontal", maximum=100,
                style="Modern.Horizontal.TProgressbar", length=140
            )
            bar.pack(side="right", padx=12)

            self.priority_rows[priority] = (bar, amount, color)

        tk.Frame(box, bg=COLOR_SURFACE, height=10).pack()

    def _build_quick_tips_panel(self, parent):
        box = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        box.grid(row=0, column=1, sticky="ew", padx=(7, 0))

        self._section_header(box, "Festival Planning Tips")

        tips = [
            "Compare prices before the sale begins.",
            "Keep a firm spending limit.",
            "Prioritize essentials over impulse purchases.",
            "Review low-priority items when near the limit.",
        ]

        for tip in tips:
            row = tk.Frame(box, bg=COLOR_SURFACE)
            row.pack(fill="x", padx=18, pady=2)
            tk.Label(
                row, text="•", bg=COLOR_SURFACE,
                fg=COLOR_ACCENT, font=(FONT, 12, "bold")
            ).pack(side="left")
            tk.Label(
                row, text=tip, bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 9), anchor="w"
            ).pack(side="left", padx=7)

        tk.Label(
            box,
            text="Offline project • prices and discounts are illustrative.",
            bg=COLOR_SURFACE, fg="#94A3B8",
            font=(FONT, 8, "italic")
        ).pack(anchor="w", padx=18, pady=(8, 13))

    # ======================================================================
    # SHOPPING LIST
    # ======================================================================

    def _build_shopping_page(self):
        page = self.pages["shopping"]

        toolbar = tk.Frame(
            page, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        toolbar.pack(fill="x", pady=(0, 10))

        search_group = tk.Frame(toolbar, bg=COLOR_SURFACE)
        search_group.pack(side="left", padx=14, pady=12)

        tk.Label(
            search_group, text="⌕", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 16)
        ).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_table())

        search_entry = ttk.Entry(
            search_group, textvariable=self.search_var,
            width=30, font=(FONT, 10)
        )
        search_entry.pack(side="left", padx=(6, 0), ipady=2)

        tk.Label(
            toolbar, text="Category", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 9)
        ).pack(side="left", padx=(18, 6))

        self.filter_combo = ttk.Combobox(
            toolbar, values=["All"] + utils.CATEGORIES,
            state="readonly", width=18
        )
        self.filter_combo.current(0)
        self.filter_combo.pack(side="left")
        self.filter_combo.bind("<<ComboboxSelected>>",
                               lambda _: self.refresh_table())

        tk.Label(
            toolbar, text="Sort", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 9)
        ).pack(side="left", padx=(18, 6))

        self.sort_combo = ttk.Combobox(
            toolbar,
            values=["Product Name", "Price", "Discount", "Category", "Priority"],
            state="readonly", width=16
        )
        self.sort_combo.current(0)
        self.sort_combo.pack(side="left")
        self.sort_combo.bind("<<ComboboxSelected>>",
                             lambda _: self.refresh_table())

        ttk.Button(
            toolbar, text="+ Add Product",
            style="Primary.TButton",
            command=self.open_product_form
        ).pack(side="right", padx=14, pady=8)

        table_card = tk.Frame(
            page, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        table_card.pack(fill="both", expand=True)

        header = tk.Frame(table_card, bg=COLOR_SURFACE)
        header.pack(fill="x", padx=18, pady=(15, 8))

        tk.Label(
            header, text="Planned Purchases", bg=COLOR_SURFACE,
            fg=COLOR_TEXT, font=FONT_H2
        ).pack(side="left")

        self.table_count_label = tk.Label(
            header, text="0 items", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 9)
        )
        self.table_count_label.pack(side="left", padx=10)

        action_frame = tk.Frame(header, bg=COLOR_SURFACE)
        action_frame.pack(side="right")

        ttk.Button(
            action_frame, text="Edit", style="Secondary.TButton",
            command=self.on_edit_selected
        ).pack(side="left", padx=3)

        ttk.Button(
            action_frame, text="Delete", style="Danger.TButton",
            command=self.on_delete_selected
        ).pack(side="left", padx=3)

        ttk.Button(
            action_frame, text="Clear All", style="Danger.TButton",
            command=self.on_clear_all
        ).pack(side="left", padx=3)

        table_frame = tk.Frame(table_card, bg=COLOR_SURFACE)
        table_frame.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        columns = (
            "product", "category", "original", "discount",
            "discounted", "quantity", "total", "priority"
        )
        headings = {
            "product": "Product",
            "category": "Category",
            "original": "Original Price",
            "discount": "Discount",
            "discounted": "Sale Price",
            "quantity": "Qty",
            "total": "Total Cost",
            "priority": "Priority",
        }

        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings",
            selectmode="browse"
        )

        widths = {
            "product": 220,
            "category": 135,
            "original": 130,
            "discount": 95,
            "discounted": 130,
            "quantity": 70,
            "total": 135,
            "priority": 100,
        }

        for col in columns:
            self.tree.heading(
                col, text=headings[col],
                command=lambda c=headings[col]: self._set_sort_and_refresh(c)
            )
            self.tree.column(
                col, width=widths[col],
                anchor="w" if col in ("product", "category") else "center",
                stretch=True
            )

        self.tree.tag_configure("high", foreground=COLOR_RED)
        self.tree.tag_configure("medium", foreground="#B45309")
        self.tree.tag_configure("low", foreground=COLOR_GREEN)

        vsb = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        hsb = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _: self.on_edit_selected())

        totals = tk.Frame(
            page, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        totals.pack(fill="x", pady=(10, 0))

        self.table_original_label = self._total_metric(
            totals, "Original", "Rs 0.00", COLOR_TEXT
        )
        self.table_sale_label = self._total_metric(
            totals, "Planned Cost", "Rs 0.00", COLOR_BLUE
        )
        self.table_savings_label = self._total_metric(
            totals, "Savings", "Rs 0.00", COLOR_GREEN
        )

        actions = tk.Frame(totals, bg=COLOR_SURFACE)
        actions.pack(side="right", padx=12, pady=10)

        ttk.Button(
            actions, text="Load Sample Data",
            style="Secondary.TButton",
            command=self.on_load_sample_data
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Save Plan",
            style="Secondary.TButton",
            command=self.on_save_plan
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Export CSV",
            style="Primary.TButton",
            command=self.on_export_csv
        ).pack(side="left", padx=3)

    def _total_metric(self, parent, title, value, color):
        frame = tk.Frame(parent, bg=COLOR_SURFACE)
        frame.pack(side="left", padx=16, pady=9)

        tk.Label(
            frame, text=title.upper(), bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 8, "bold")
        ).pack(anchor="w")
        label = tk.Label(
            frame, text=value, bg=COLOR_SURFACE,
            fg=color, font=(FONT, 11, "bold")
        )
        label.pack(anchor="w", pady=(2, 0))
        return label

    # ======================================================================
    # PRODUCT FORM MODAL
    # ======================================================================

    def open_product_form(self):
        if self.product_window and self.product_window.winfo_exists():
            self.product_window.lift()
            self.product_window.focus_force()
            return

        self.editing_index = None
        self._create_product_window()

    def _create_product_window(self):
        self.product_window = tk.Toplevel(self.root)
        self.product_window.title(
            "Edit Product" if self.editing_index is not None else "Add Product"
        )
        self.product_window.geometry("520x510")
        self.product_window.resizable(False, False)
        self.product_window.configure(bg=COLOR_BG)
        self.product_window.transient(self.root)
        self.product_window.grab_set()

        header = tk.Frame(self.product_window, bg=COLOR_SIDEBAR)
        header.pack(fill="x")

        tk.Label(
            header,
            text="EDIT PRODUCT" if self.editing_index is not None else "ADD PRODUCT",
            bg=COLOR_SIDEBAR, fg="white", font=(FONT, 15, "bold")
        ).pack(anchor="w", padx=22, pady=(17, 2))

        tk.Label(
            header,
            text="Enter the details for your planned purchase.",
            bg=COLOR_SIDEBAR, fg="#CBD5E1", font=(FONT, 9)
        ).pack(anchor="w", padx=22, pady=(0, 16))

        body = tk.Frame(self.product_window, bg=COLOR_SURFACE)
        body.pack(fill="both", expand=True, padx=18, pady=18)

        self.form_title_label = tk.Label(
            body,
            text="Product Details",
            bg=COLOR_SURFACE, fg=COLOR_TEXT, font=FONT_H3
        )
        self.form_title_label.grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        fields = [
            ("Product Name", "name"),
            ("Original Price (Rs)", "price"),
            ("Expected Discount (%)", "discount"),
            ("Quantity", "quantity"),
        ]

        for row, (label, _) in enumerate(fields, start=1):
            tk.Label(
                body, text=label, bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 9, "bold")
            ).grid(row=row, column=0, sticky="w", pady=6)

        self.name_entry = ttk.Entry(body, width=30)
        self.name_entry.grid(row=1, column=1, sticky="ew", pady=5)

        self.price_entry = ttk.Entry(body, width=30)
        self.price_entry.grid(row=2, column=1, sticky="ew", pady=5)

        self.discount_entry = ttk.Entry(body, width=30)
        self.discount_entry.grid(row=3, column=1, sticky="ew", pady=5)

        self.quantity_entry = ttk.Entry(body, width=30)
        self.quantity_entry.grid(row=4, column=1, sticky="ew", pady=5)
        self.quantity_entry.insert(0, "1")

        tk.Label(
            body, text="Category", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 9, "bold")
        ).grid(row=5, column=0, sticky="w", pady=6)

        self.category_combo = ttk.Combobox(
            body, values=utils.CATEGORIES, state="readonly", width=28
        )
        self.category_combo.grid(row=5, column=1, sticky="ew", pady=5)
        self.category_combo.current(0)

        tk.Label(
            body, text="Priority", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 9, "bold")
        ).grid(row=6, column=0, sticky="w", pady=6)

        self.priority_combo = ttk.Combobox(
            body, values=utils.PRIORITIES, state="readonly", width=28
        )
        self.priority_combo.grid(row=6, column=1, sticky="ew", pady=5)
        self.priority_combo.current(1)

        body.columnconfigure(1, weight=1)

        button_row = tk.Frame(body, bg=COLOR_SURFACE)
        button_row.grid(
            row=7, column=0, columnspan=2,
            sticky="e", pady=(22, 0)
        )

        ttk.Button(
            button_row, text="Cancel",
            style="Secondary.TButton",
            command=self.on_cancel_edit
        ).pack(side="left", padx=4)

        ttk.Button(
            button_row,
            text="Save Changes" if self.editing_index is not None else "Add Product",
            style="Primary.TButton",
            command=self.on_add_or_update_product
        ).pack(side="left", padx=4)

        self.product_window.protocol("WM_DELETE_WINDOW", self.on_cancel_edit)
        self.name_entry.focus_set()

    def _close_product_window(self):
        if self.product_window and self.product_window.winfo_exists():
            self.product_window.grab_release()
            self.product_window.destroy()
        self.product_window = None

    # ======================================================================
    # ANALYTICS
    # ======================================================================

    def _build_analytics_page(self):
        page = self.pages["analytics"]

        top = tk.Frame(page, bg=COLOR_BG)
        top.pack(fill="x", pady=(0, 10))

        self.analytics_kpis = {}
        for i, (key, title) in enumerate([
            ("items", "PRODUCTS"),
            ("planned", "PLANNED COST"),
            ("savings", "EXPECTED SAVINGS"),
            ("usage", "BUDGET USED"),
        ]):
            top.columnconfigure(i, weight=1)
            card = tk.Frame(
                top, bg=COLOR_SURFACE,
                highlightbackground=COLOR_BORDER, highlightthickness=1
            )
            card.grid(row=0, column=i, sticky="ew", padx=5)

            tk.Label(
                card, text=title, bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 8, "bold")
            ).pack(anchor="w", padx=14, pady=(10, 3))

            value = tk.Label(
                card, text="0", bg=COLOR_SURFACE,
                fg=COLOR_TEXT, font=(FONT, 15, "bold")
            )
            value.pack(anchor="w", padx=14, pady=(0, 10))
            self.analytics_kpis[key] = value

        chart_grid = tk.Frame(page, bg=COLOR_BG)
        chart_grid.pack(fill="both", expand=True)
        chart_grid.columnconfigure(0, weight=1)
        chart_grid.columnconfigure(1, weight=1)
        chart_grid.rowconfigure(0, weight=1)
        chart_grid.rowconfigure(1, weight=1)

        self.fig_category = Figure(figsize=(5.2, 3.2), dpi=90)
        self.fig_budget = Figure(figsize=(5.2, 3.2), dpi=90)
        self.fig_price = Figure(figsize=(5.2, 3.2), dpi=90)
        self.fig_priority = Figure(figsize=(5.2, 3.2), dpi=90)

        self.canvas_category = self._chart_card(
            chart_grid, 0, 0, self.fig_category
        )
        self.canvas_budget = self._chart_card(
            chart_grid, 0, 1, self.fig_budget
        )
        self.canvas_price = self._chart_card(
            chart_grid, 1, 0, self.fig_price
        )
        self.canvas_priority = self._chart_card(
            chart_grid, 1, 1, self.fig_priority
        )

    def _chart_card(self, parent, row, column, figure):
        card = tk.Frame(
            parent, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        card.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)

        canvas = FigureCanvasTkAgg(figure, master=card)
        widget = canvas.get_tk_widget()
        widget.configure(bg=COLOR_SURFACE, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=5, pady=5)
        return canvas

    def refresh_charts(self):
        try:
            charts.draw_category_pie_chart(self.fig_category, self.manager)
            charts.draw_budget_bar_chart(self.fig_budget, self.manager)
            charts.draw_price_comparison_chart(self.fig_price, self.manager)
            charts.draw_priority_chart(self.fig_priority, self.manager)

            for fig in (
                self.fig_category,
                self.fig_budget,
                self.fig_price,
                self.fig_priority,
            ):
                fig.patch.set_facecolor(COLOR_SURFACE)
                fig.tight_layout(pad=1.5)

            self.canvas_category.draw()
            self.canvas_budget.draw()
            self.canvas_price.draw()
            self.canvas_priority.draw()

            m = self.manager
            self.analytics_kpis["items"].config(
                text=str(len(m.plan.products))
            )
            self.analytics_kpis["planned"].config(
                text=utils.format_currency(m.total_planned_cost())
            )
            self.analytics_kpis["savings"].config(
                text=utils.format_currency(m.total_savings())
            )
            self.analytics_kpis["usage"].config(
                text=f"{m.budget_usage_percent():.1f}%"
            )
        except Exception as e:
            self._set_status(f"Could not refresh charts: {e}", "error")

    # ======================================================================
    # SUMMARY
    # ======================================================================

    def _build_summary_page(self):
        page = self.pages["summary"]

        header = tk.Frame(
            page, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        header.pack(fill="x", pady=(0, 12))

        tk.Label(
            header, text="Shopping Plan Report",
            bg=COLOR_SURFACE, fg=COLOR_TEXT,
            font=FONT_H1
        ).pack(anchor="w", padx=20, pady=(18, 2))

        tk.Label(
            header,
            text="A final snapshot of your budget, purchases, savings and recommendations.",
            bg=COLOR_SURFACE, fg=COLOR_MUTED, font=FONT_BODY
        ).pack(anchor="w", padx=20, pady=(0, 16))

        overview = tk.Frame(page, bg=COLOR_BG)
        overview.pack(fill="x", pady=(0, 12))
        for i in range(5):
            overview.columnconfigure(i, weight=1)

        self.summary_values = {}
        summary_cards = [
            ("budget", "Budget", COLOR_ACCENT),
            ("original", "Original Cost", COLOR_TEXT),
            ("planned", "Sale Cost", COLOR_BLUE),
            ("savings", "Savings", COLOR_GREEN),
            ("remaining", "Remaining", COLOR_PURPLE),
        ]

        for i, (key, title, color) in enumerate(summary_cards):
            card = tk.Frame(
                overview, bg=COLOR_SURFACE,
                highlightbackground=COLOR_BORDER, highlightthickness=1
            )
            card.grid(row=0, column=i, sticky="ew", padx=4)

            tk.Label(
                card, text=title.upper(), bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 8, "bold")
            ).pack(anchor="w", padx=12, pady=(11, 3))

            value = tk.Label(
                card, text="Rs 0.00", bg=COLOR_SURFACE,
                fg=color, font=(FONT, 12, "bold")
            )
            value.pack(anchor="w", padx=12, pady=(0, 11))
            self.summary_values[key] = value

        middle = tk.Frame(page, bg=COLOR_BG)
        middle.pack(fill="both", expand=True)
        middle.columnconfigure(0, weight=2)
        middle.columnconfigure(1, weight=1)
        middle.rowconfigure(0, weight=1)

        report = tk.Frame(
            middle, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        report.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self._section_header(report, "Plan Details")

        self.summary_details = tk.Text(
            report,
            wrap="word",
            font=(FONT, 10),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=5,
            state="disabled",
        )
        self.summary_details.pack(fill="both", expand=True)

        side = tk.Frame(
            middle, bg=COLOR_SURFACE,
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        side.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._section_header(side, "Plan Status")

        self.summary_status_badge = tk.Label(
            side, text="SAFE", bg=COLOR_SOFT_GREEN,
            fg=COLOR_GREEN, font=(FONT, 10, "bold"),
            padx=12, pady=8
        )
        self.summary_status_badge.pack(anchor="w", padx=18, pady=5)

        self.summary_item_counts = tk.Label(
            side, text="", bg=COLOR_SURFACE,
            fg=COLOR_TEXT, font=(FONT, 9),
            justify="left", anchor="w"
        )
        self.summary_item_counts.pack(fill="x", padx=18, pady=10)

        tk.Label(
            side, text="RECOMMENDATIONS", bg=COLOR_SURFACE,
            fg=COLOR_MUTED, font=(FONT, 8, "bold")
        ).pack(anchor="w", padx=18, pady=(8, 4))

        self.summary_recommendations = tk.Text(
            side, height=10, wrap="word",
            font=(FONT, 9), bg=COLOR_SURFACE,
            fg=COLOR_MUTED, relief="flat", bd=0,
            state="disabled"
        )
        self.summary_recommendations.pack(fill="both", expand=True,
                                          padx=18, pady=(0, 10))

        actions = tk.Frame(side, bg=COLOR_SURFACE)
        actions.pack(fill="x", padx=14, pady=(0, 14))

        ttk.Button(
            actions, text="Save Plan",
            style="Secondary.TButton",
            command=self.on_save_plan
        ).pack(side="left", padx=3)

        ttk.Button(
            actions, text="Export CSV",
            style="Primary.TButton",
            command=self.on_export_csv
        ).pack(side="left", padx=3)

    # ======================================================================
    # EVENT HANDLERS — BUDGET
    # ======================================================================

    def on_set_budget(self):
        try:
            budget = utils.validate_budget(self.budget_entry.get())
            self.plan.budget = budget
            self.refresh_all()
            self._set_status(
                f"Budget set to {utils.format_currency(budget)}", "success"
            )
        except ValidationError as e:
            messagebox.showerror("Invalid Budget", str(e))
            self._set_status("Invalid budget entered.", "error")

    def on_reset_budget(self):
        if messagebox.askyesno(
            "Reset Budget",
            "Reset the total budget to Rs 0.00?\n\nYour products will remain."
        ):
            self.plan.budget = 0.0
            self.budget_entry.delete(0, "end")
            self.refresh_all()
            self._set_status("Budget reset.", "warning")

    # ======================================================================
    # EVENT HANDLERS — PRODUCT
    # ======================================================================

    def _read_product_form(self) -> Product:
        name = utils.validate_non_empty_text(
            self.name_entry.get(), "Product name"
        )

        category = self.category_combo.get()
        if not category:
            raise ValidationError("Please select a category.")

        priority = self.priority_combo.get()
        if not priority:
            raise ValidationError("Please select a priority.")

        price = utils.validate_price(
            self.price_entry.get(), "Original price"
        )
        discount = utils.validate_discount(self.discount_entry.get())
        quantity = utils.validate_quantity(self.quantity_entry.get())

        return Product(
            name=name,
            category=category,
            original_price=price,
            discount=discount,
            quantity=quantity,
            priority=priority,
        )

    def on_add_or_update_product(self):
        try:
            product = self._read_product_form()
        except ValidationError as e:
            messagebox.showerror("Invalid Product Details", str(e))
            return

        if self.editing_index is None:
            self.plan.add_product(product)
            action = f"'{product.name}' added to your plan."
        else:
            self.plan.update_product(self.editing_index, product)
            action = f"'{product.name}' updated."
            self.editing_index = None

        self._clear_product_form()
        self._close_product_window()
        self.refresh_all()
        self._set_status(action, "success")

    def on_edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Select a product from the table first."
            )
            return

        index = self._get_plan_index_from_selection(selected[0])
        if index is None:
            messagebox.showerror(
                "Error", "Could not locate the selected product."
            )
            return

        product = self.plan.products[index]
        self.editing_index = index

        if self.product_window and self.product_window.winfo_exists():
            self._close_product_window()

        self._create_product_window()

        self.name_entry.insert(0, product.name)
        self.price_entry.insert(0, str(product.original_price))
        self.discount_entry.insert(0, str(product.discount))
        self.quantity_entry.delete(0, "end")
        self.quantity_entry.insert(0, str(product.quantity))
        self.category_combo.set(product.category)
        self.priority_combo.set(product.priority)

    def on_cancel_edit(self):
        self.editing_index = None
        self._clear_product_form()
        self._close_product_window()

    def on_delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "No Selection",
                "Select a product from the table first."
            )
            return

        index = self._get_plan_index_from_selection(selected[0])
        if index is None:
            messagebox.showerror(
                "Error", "Could not locate the selected product."
            )
            return

        product = self.plan.products[index]

        if messagebox.askyesno(
            "Delete Product",
            f"Delete '{product.name}' from your shopping plan?"
        ):
            self.plan.remove_product(index)

            if self.editing_index is not None:
                if self.editing_index == index:
                    self.on_cancel_edit()
                elif self.editing_index > index:
                    self.editing_index -= 1

            self.refresh_all()
            self._set_status(f"'{product.name}' deleted.", "success")

    def on_clear_all(self):
        if not self.plan.products:
            self._set_status("Shopping list is already empty.", "warning")
            return

        if messagebox.askyesno(
            "Clear Shopping List",
            f"Remove all {len(self.plan.products)} products?"
        ):
            self.plan.clear_products()
            self.on_cancel_edit()
            self.refresh_all()
            self._set_status("Shopping list cleared.", "success")

    def _clear_product_form(self):
        if not hasattr(self, "name_entry") or not self.name_entry.winfo_exists():
            return

        self.name_entry.delete(0, "end")
        self.price_entry.delete(0, "end")
        self.discount_entry.delete(0, "end")
        self.quantity_entry.delete(0, "end")
        self.quantity_entry.insert(0, "1")

        try:
            self.category_combo.current(0)
            self.priority_combo.current(1)
        except tk.TclError:
            pass

    def _get_plan_index_from_selection(self, item_id):
        try:
            return int(item_id)
        except (TypeError, ValueError):
            return None

    # ======================================================================
    # SAVE / LOAD / EXPORT
    # ======================================================================

    def on_save_plan(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialdir="data",
            initialfile="shopping_plan.json",
            filetypes=[("JSON files", "*.json")],
        )
        if not filepath:
            return

        try:
            StorageManager.save_plan(self.plan, filepath)
            self._set_status("Shopping plan saved successfully.", "success")
            messagebox.showinfo(
                "Plan Saved",
                f"Shopping plan saved to:\n{filepath}"
            )
        except Exception as e:
            self._set_status("Save failed.", "error")
            messagebox.showerror("Save Failed", str(e))

    def on_load_plan(self):
        filepath = filedialog.askopenfilename(
            initialdir="data",
            filetypes=[("JSON files", "*.json")],
        )
        if not filepath:
            return

        try:
            new_plan = StorageManager.load_plan(filepath)
            self.plan = new_plan
            self.manager = BudgetManager(self.plan)
            self.on_cancel_edit()

            self.budget_entry.delete(0, "end")
            if self.plan.budget:
                self.budget_entry.insert(0, str(self.plan.budget))

            self.refresh_all()
            self._set_status("Shopping plan loaded successfully.", "success")
            messagebox.showinfo(
                "Plan Loaded",
                f"Shopping plan loaded from:\n{filepath}"
            )
        except Exception as e:
            self._set_status("Load failed.", "error")
            messagebox.showerror("Load Failed", str(e))

    def on_load_sample_data(self):
        if self.plan.products and not messagebox.askyesno(
            "Load Sample Data",
            "This will replace your current shopping plan.\n\nContinue?"
        ):
            return

        try:
            new_plan = StorageManager.load_plan(DEFAULT_DATA_PATH)
            self.plan = new_plan
            self.manager = BudgetManager(self.plan)
            self.on_cancel_edit()

            self.budget_entry.delete(0, "end")
            self.budget_entry.insert(0, str(self.plan.budget))

            self.refresh_all()
            self.show_page("dashboard")
            self._set_status("Sample shopping plan loaded.", "success")
        except Exception as e:
            self._set_status("Could not load sample data.", "error")
            messagebox.showerror(
                "Could Not Load Sample Data", str(e)
            )

    def on_export_csv(self):
        if not self.plan.products:
            messagebox.showwarning(
                "Nothing to Export",
                "Add some products before exporting."
            )
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialdir="exports",
            initialfile="shopping_summary.csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not filepath:
            return

        try:
            StorageManager.export_csv(self.plan, filepath)
            self._set_status("Shopping list exported to CSV.", "success")
            messagebox.showinfo(
                "Export Complete",
                f"Shopping list exported to:\n{filepath}"
            )
        except Exception as e:
            self._set_status("Export failed.", "error")
            messagebox.showerror("Export Failed", str(e))

    # ======================================================================
    # BANK OFFER CALCULATOR
    # ======================================================================

    def _open_bank_calculator(self):
        window = tk.Toplevel(self.root)
        window.title("Bank Offer Calculator")
        window.geometry("430x400")
        window.resizable(False, False)
        window.configure(bg=COLOR_BG)
        window.transient(self.root)
        window.grab_set()

        header = tk.Frame(window, bg=COLOR_SIDEBAR)
        header.pack(fill="x")
        tk.Label(
            header, text="BANK / COUPON CALCULATOR",
            bg=COLOR_SIDEBAR, fg="white",
            font=(FONT, 13, "bold")
        ).pack(anchor="w", padx=20, pady=(16, 3))
        tk.Label(
            header, text="Estimate your final payable price.",
            bg=COLOR_SIDEBAR, fg="#CBD5E1",
            font=(FONT, 9)
        ).pack(anchor="w", padx=20, pady=(0, 15))

        body = tk.Frame(window, bg=COLOR_SURFACE)
        body.pack(fill="both", expand=True, padx=16, pady=16)

        entries = {}
        fields = [
            ("Subtotal (Rs)", "subtotal"),
            ("Bank Discount (%)", "bank_pct"),
            ("Maximum Bank Discount (Rs)", "max_discount"),
            ("Coupon Discount (Rs)", "coupon"),
        ]

        for row, (label, key) in enumerate(fields):
            tk.Label(
                body, text=label, bg=COLOR_SURFACE,
                fg=COLOR_MUTED, font=(FONT, 9, "bold")
            ).grid(row=row, column=0, sticky="w", pady=6)
            entry = ttk.Entry(body, width=20)
            entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            entries[key] = entry

        body.columnconfigure(1, weight=1)

        result = tk.Label(
            body, text="", bg=COLOR_SOFT_GREEN,
            fg=COLOR_GREEN, font=(FONT, 10, "bold"),
            wraplength=360, justify="left", padx=12, pady=10
        )
        result.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 8))

        def calculate():
            try:
                subtotal = utils.validate_price(
                    entries["subtotal"].get(), "Subtotal"
                )
                bank_pct = float(entries["bank_pct"].get() or 0)
                max_discount = float(entries["max_discount"].get() or 0)
                coupon = float(entries["coupon"].get() or 0)

                if not 0 <= bank_pct <= 100:
                    raise ValidationError(
                        "Bank discount % must be between 0 and 100."
                    )
                if max_discount < 0 or coupon < 0:
                    raise ValidationError(
                        "Discount amounts cannot be negative."
                    )

                actual_bank_discount, final_price, total_discount = (
                    utils.calculate_bank_offer(
                        subtotal, bank_pct, max_discount, coupon
                    )
                )

                result.config(
                    text=(
                        f"Bank discount: {utils.format_currency(actual_bank_discount)}\n"
                        f"Total discount: {utils.format_currency(total_discount)}\n"
                        f"Final price: {utils.format_currency(final_price)}"
                    )
                )
            except ValidationError as e:
                messagebox.showerror("Invalid Input", str(e), parent=window)
            except ValueError:
                messagebox.showerror(
                    "Invalid Input",
                    "Please enter valid numbers in all fields.",
                    parent=window
                )

        ttk.Button(
            body, text="Calculate Final Price",
            style="Primary.TButton",
            command=calculate
        ).grid(row=6, column=0, columnspan=2, pady=6)

    def on_calculate_bank_offer(self):
        # Kept as a public method for compatibility with the original GUI.
        self._open_bank_calculator()

    # ======================================================================
    # REFRESH / DASHBOARD DATA
    # ======================================================================

    def refresh_all(self):
        self.refresh_dashboard()
        self.refresh_table()

        if self.current_page == "analytics":
            self.refresh_charts()
        if self.current_page == "summary":
            self.refresh_summary()

        self.header_budget_label.config(
            text=f"Budget  •  {utils.format_currency(self.plan.budget)}"
        )
        self.product_count_label.config(
            text=f"{len(self.plan.products)} product"
            f"{'' if len(self.plan.products) == 1 else 's'}"
        )

    def refresh_dashboard(self):
        m = self.manager

        self.card_budget_val.config(
            text=utils.format_currency(m.plan.budget)
        )
        self.card_planned_val.config(
            text=utils.format_currency(m.total_planned_cost())
        )
        self.card_remaining_val.config(
            text=utils.format_currency(m.remaining_budget())
        )
        self.card_savings_val.config(
            text=utils.format_currency(m.total_savings())
        )

        status = m.budget_status()
        usage = m.budget_usage_percent()

        status_data = {
            "Safe": (
                COLOR_GREEN, COLOR_SOFT_GREEN,
                "Green.Horizontal.TProgressbar"
            ),
            "Moderate": (
                COLOR_YELLOW, COLOR_SOFT_YELLOW,
                "Yellow.Horizontal.TProgressbar"
            ),
            "Near Limit": (
                COLOR_ORANGE, "#FFF3E0",
                "Orange.Horizontal.TProgressbar"
            ),
            "Over Budget": (
                COLOR_RED, COLOR_SOFT_RED,
                "Red.Horizontal.TProgressbar"
            ),
        }

        color, bg, style = status_data.get(
            status,
            status_data["Safe"]
        )

        self.status_badge.config(
            text=status.upper(),
            bg=bg,
            fg=color
        )
        self.usage_label.config(
            text=f"{usage:.1f}% used"
        )
        self.progress_bar.config(
            style=style,
            value=min(max(usage, 0), 100)
        )

        if m.plan.budget <= 0:
            self.budget_health_text.config(
                text="Set a budget to start tracking your shopping plan."
            )
        elif m.is_over_budget():
            over = m.total_planned_cost() - m.plan.budget
            self.budget_health_text.config(
                text=(
                    f"Planned spending is {utils.format_currency(over)} "
                    "above your budget."
                )
            )
        else:
            remaining = m.remaining_budget()
            self.budget_health_text.config(
                text=(
                    f"{utils.format_currency(remaining)} remains available "
                    "in your shopping budget."
                )
            )

        self.over_budget_label.config(
            text=(
                f"⚠ Over budget by "
                f"{utils.format_currency(m.total_planned_cost() - m.plan.budget)}"
                if m.is_over_budget() else ""
            )
        )

        priority_totals = m.spending_by_priority()
        max_priority = max(priority_totals.values()) if priority_totals else 0

        for priority, (bar, amount, priority_color) in self.priority_rows.items():
            amount_value = priority_totals.get(priority, 0)
            percent = (
                (amount_value / max_priority) * 100
                if max_priority > 0 else 0
            )
            bar.config(value=percent)
            amount.config(text=utils.format_currency(amount_value))

        for child in self.recommendations_frame.winfo_children():
            child.destroy()

        recommendations = m.get_recommendations()
        for i, rec in enumerate(recommendations[:4]):
            rec_card = tk.Frame(
                self.recommendations_frame,
                bg="#F8FAFC",
                highlightbackground=COLOR_BORDER,
                highlightthickness=1
            )
            rec_card.pack(fill="x", pady=3)

            icon = "💡"
            if "exceeds" in rec.lower() or "over" in rec.lower():
                icon = "⚠"
            elif "discount" in rec.lower() or "good time" in rec.lower():
                icon = "🔥"

            tk.Label(
                rec_card, text=icon,
                bg="#F8FAFC", fg=COLOR_ACCENT,
                font=(FONT, 12)
            ).pack(side="left", padx=(10, 7), pady=9)

            tk.Label(
                rec_card, text=rec,
                bg="#F8FAFC", fg=COLOR_TEXT,
                font=(FONT, 9), wraplength=430,
                justify="left", anchor="w"
            ).pack(side="left", fill="x", expand=True, pady=8, padx=(0, 8))

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return

        for row in self.tree.get_children():
            self.tree.delete(row)

        search_text = (
            self.search_var.get()
            if hasattr(self, "search_var") else ""
        )
        category = (
            self.filter_combo.get()
            if hasattr(self, "filter_combo") else "All"
        )
        sort_key = (
            self.sort_combo.get()
            if hasattr(self, "sort_combo") else "Product Name"
        )

        indexed_products = list(enumerate(self.plan.products))

        if category and category != "All":
            indexed_products = [
                (i, p) for i, p in indexed_products
                if p.category == category
            ]

        if search_text:
            search_lower = search_text.lower()
            indexed_products = [
                (i, p) for i, p in indexed_products
                if search_lower in p.name.lower()
            ]

        key_map = {
            "Product Name": lambda pair: pair[1].name.lower(),
            "Price": lambda pair: pair[1].total_cost,
            "Discount": lambda pair: pair[1].discount,
            "Category": lambda pair: pair[1].category.lower(),
            "Priority": lambda pair: {
                "High": 0, "Medium": 1, "Low": 2
            }.get(pair[1].priority, 3),
        }

        indexed_products.sort(
            key=key_map.get(sort_key, key_map["Product Name"])
        )

        for original_index, p in indexed_products:
            tag = p.priority.lower()
            self.tree.insert(
                "", "end",
                iid=str(original_index),
                values=(
                    p.name,
                    p.category,
                    utils.format_currency(p.original_price),
                    f"{p.discount:.0f}%",
                    utils.format_currency(p.discounted_price),
                    p.quantity,
                    utils.format_currency(p.total_cost),
                    p.priority,
                ),
                tags=(tag,)
            )

        total = len(indexed_products)
        self.table_count_label.config(
            text=f"{total} item{'s' if total != 1 else ''}"
        )

        self.table_original_label.config(
            text=utils.format_currency(self.manager.total_original_cost())
        )
        self.table_sale_label.config(
            text=utils.format_currency(self.manager.total_planned_cost())
        )
        self.table_savings_label.config(
            text=utils.format_currency(self.manager.total_savings())
        )

    def _set_sort_and_refresh(self, column_name):
        self.sort_combo.set(column_name)
        self.refresh_table()

    # ======================================================================
    # SUMMARY
    # ======================================================================

    def refresh_summary(self):
        m = self.manager
        counts = m.count_by_priority()
        status = m.budget_status()

        self.summary_values["budget"].config(
            text=utils.format_currency(m.plan.budget)
        )
        self.summary_values["original"].config(
            text=utils.format_currency(m.total_original_cost())
        )
        self.summary_values["planned"].config(
            text=utils.format_currency(m.total_planned_cost())
        )
        self.summary_values["savings"].config(
            text=utils.format_currency(m.total_savings())
        )
        self.summary_values["remaining"].config(
            text=utils.format_currency(m.remaining_budget())
        )

        status_colors = {
            "Safe": (COLOR_GREEN, COLOR_SOFT_GREEN),
            "Moderate": (COLOR_YELLOW, COLOR_SOFT_YELLOW),
            "Near Limit": (COLOR_ORANGE, "#FFF3E0"),
            "Over Budget": (COLOR_RED, COLOR_SOFT_RED),
        }
        color, bg = status_colors.get(
            status, (COLOR_GREEN, COLOR_SOFT_GREEN)
        )
        self.summary_status_badge.config(
            text=status.upper(), fg=color, bg=bg
        )

        self.summary_item_counts.config(
            text=(
                f"Products planned:  {len(m.plan.products)}\n\n"
                f"🔴 High priority:    {counts['High']}\n"
                f"🟡 Medium priority:  {counts['Medium']}\n"
                f"🟢 Low priority:     {counts['Low']}\n\n"
                f"Budget usage:       {m.budget_usage_percent():.1f}%"
            )
        )

        detail_lines = [
            "SHOPPING PLAN OVERVIEW",
            "",
            f"Total Budget       {utils.format_currency(m.plan.budget)}",
            f"Original Cost      {utils.format_currency(m.total_original_cost())}",
            f"Expected Sale Cost {utils.format_currency(m.total_planned_cost())}",
            f"Expected Savings   {utils.format_currency(m.total_savings())}",
            f"Remaining Budget   {utils.format_currency(m.remaining_budget())}",
            "",
            "BUDGET STATUS",
            "",
            f"{status} — {m.budget_usage_percent():.1f}% of budget used",
            "",
            "PRIORITY COUNTS",
            "",
            f"High Priority      {counts['High']}",
            f"Medium Priority    {counts['Medium']}",
            f"Low Priority       {counts['Low']}",
            "",
            "CATEGORY SPENDING",
            "",
        ]

        category_totals = m.spending_by_category()
        if category_totals:
            for category, amount in sorted(
                category_totals.items(), key=lambda item: item[1], reverse=True
            ):
                detail_lines.append(
                    f"{category:<20} {utils.format_currency(amount)}"
                )
        else:
            detail_lines.append("No products have been added yet.")

        self.summary_details.config(state="normal")
        self.summary_details.delete("1.0", "end")
        self.summary_details.insert("1.0", "\n".join(detail_lines))
        self.summary_details.config(state="disabled")

        recommendations = m.get_recommendations()
        self.summary_recommendations.config(state="normal")
        self.summary_recommendations.delete("1.0", "end")
        for rec in recommendations:
            self.summary_recommendations.insert(
                "end", f"• {rec}\n\n"
            )
        self.summary_recommendations.config(state="disabled")

    # ======================================================================
    # SHORTCUTS
    # ======================================================================

    def _bind_shortcuts(self):
        self.root.bind("<Control-s>", lambda _: self.on_save_plan())
        self.root.bind("<Control-o>", lambda _: self.on_load_plan())
        self.root.bind("<Control-e>", lambda _: self.on_export_csv())
        self.root.bind("<Control-n>", lambda _: self.open_product_form())
        self.root.bind("<Delete>", lambda _: self.on_delete_selected())


# ---------------------------------------------------------------------------
# Standalone execution support
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    try:
        BudgetPlannerApp(root)
        root.mainloop()
    except Exception as e:
        traceback_text = str(e)
        traceback.print_exc()
        messagebox.showerror("Unexpected Error", traceback_text)
        raise
