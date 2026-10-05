/* ==========================================================================
   Festive Budget Planner — web edition (browser client)

   The browser owns the shopping plan (auto-saved in localStorage) and posts
   it to the Flask API, which runs the *original* Python logic:
   BudgetManager for every number and recommendation, charts.py for the
   Matplotlib PNGs, storage.py for the CSV export and utils.py for
   validation. Nothing is recalculated here, so the web edition and the
   desktop edition can never disagree.
   ========================================================================== */

(function () {
  "use strict";

  // --------------------------------------------------------------- constants
  var STORAGE_KEY = "festive-budget-plan-v1";
  var VIEW_KEY = "festive-budget-view-v1";

  var STATUS_STYLE = {
    "Safe": { badge: "badge-safe", fill: "fill-green" },
    "Moderate": { badge: "badge-moderate", fill: "fill-yellow" },
    "Near Limit": { badge: "badge-near", fill: "fill-orange" },
    "Over Budget": { badge: "badge-over", fill: "fill-red" }
  };

  var PRIORITY_COLOR = { High: "#EF4444", Medium: "#F59E0B", Low: "#10B981" };

  var PAGE_TITLES = {
    dashboard: ["Dashboard", "Your complete shopping budget overview."],
    shopping: ["Shopping List", "Add, organize and manage planned purchases."],
    analytics: ["Analytics", "Understand where your shopping budget is going."],
    summary: ["Final Summary", "A clean overview of your complete shopping plan."]
  };

  var CHART_TITLES = {
    category: "Spending by Category",
    budget: "Budget vs Planned Spending",
    price: "Original vs Sale Price",
    priority: "Priority Spending"
  };

  // ------------------------------------------------------------------- state
  var plan = { budget: 0, products: [] };
  var view = { search: "", category: "All", sortKey: "Product Name", reverse: false };
  var analysis = null;
  var selectedIndex = null;
  var editingIndex = null;
  var currentPage = "dashboard";
  var chartUrls = {};
  var inflightChart = {};
  var refreshTimer = null;

  // ------------------------------------------------------------------ helpers
  function $(id) { return document.getElementById(id); }

  function fmt(amount) {
    var value = Number(amount);
    if (!isFinite(value)) { value = 0; }
    return "Rs " + value.toLocaleString("en-US", {
      minimumFractionDigits: 2, maximumFractionDigits: 2
    });
  }

  function esc(text) {
    return String(text === null || text === undefined ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function debounce(fn, wait) {
    var timer = null;
    return function () {
      var args = arguments, self = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(self, args); }, wait);
    };
  }

  async function api(path, options) {
    options = options || {};
    var init = { method: options.method || "GET", headers: {} };
    if (options.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(options.body);
    }
    var response = await fetch(path, init);
    if (options.raw) {
      if (!response.ok) {
        var message = "Request failed (" + response.status + ")";
        try { message = (await response.json()).error || message; } catch (e) { /* keep default */ }
        throw new Error(message);
      }
      return response;
    }
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || ("Request failed (" + response.status + ")"));
    }
    return data;
  }

  // -------------------------------------------------------------- persistence
  function saveLocal() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(plan));
      localStorage.setItem(VIEW_KEY, JSON.stringify(view));
      $("storageLabel").textContent = "Saved locally";
    } catch (err) {
      $("storageLabel").textContent = "Not saved (storage blocked)";
    }
  }

  function loadLocal() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.products)) {
          plan = { budget: Number(parsed.budget) || 0, products: parsed.products };
        }
      }
      var rawView = localStorage.getItem(VIEW_KEY);
      if (rawView) {
        var parsedView = JSON.parse(rawView);
        if (parsedView) {
          view.search = parsedView.search || "";
          view.category = parsedView.category || "All";
          view.sortKey = parsedView.sortKey || "Product Name";
          view.reverse = !!parsedView.reverse;
        }
      }
    } catch (err) {
      /* corrupted storage -> start with an empty plan */
      plan = { budget: 0, products: [] };
    }
  }

  // --------------------------------------------------------------- status bar
  var statusTimer = null;
  function setStatus(message, kind) {
    var bar = document.querySelector(".status-bar");
    var label = $("statusLabel");
    label.textContent = (kind === "error" ? "\u26A0 " : kind === "success" ? "\u2713 " : "\u25CF ") + message;
    bar.classList.remove("is-error", "is-success");
    if (kind === "error") { bar.classList.add("is-error"); }
    if (kind === "success") { bar.classList.add("is-success"); }
    clearTimeout(statusTimer);
    statusTimer = setTimeout(function () {
      label.textContent = "\u25CF Ready";
      bar.classList.remove("is-error", "is-success");
    }, 6000);
  }

  var toastTimer = null;
  function toast(message, kind) {
    var el = $("toast");
    el.textContent = message;
    el.className = "toast" + (kind ? " is-" + kind : "");
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.hidden = true; }, 3200);
    setStatus(message, kind);
  }

  // ------------------------------------------------------------------- modals
  function openModal(id) {
    $(id).hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal(id) {
    $(id).hidden = true;
    if (document.querySelectorAll(".modal-backdrop:not([hidden])").length === 0) {
      document.body.style.overflow = "";
    }
  }

  function confirmDialog(title, message, okLabel) {
    return new Promise(function (resolve) {
      $("confirmTitle").textContent = title;
      $("confirmMessage").textContent = message;
      var okBtn = $("confirmOkBtn");
      okBtn.textContent = okLabel || "Confirm";
      openModal("confirmModal");

      function cleanup(result) {
        okBtn.removeEventListener("click", onOk);
        $("confirmModal").removeEventListener("click", onBackdrop);
        closeModal("confirmModal");
        resolve(result);
      }
      function onOk() { cleanup(true); }
      function onBackdrop(event) {
        if (event.target === $("confirmModal")) { cleanup(false); }
      }
      okBtn.addEventListener("click", onOk);
      $("confirmModal").addEventListener("click", onBackdrop);
    });
  }

  // ==================================================================== render
  function render(analysis_) {
    analysis = analysis_;
    var t = analysis.totals;

    $("headerBudget").textContent = "Budget \u2022 " + fmt(analysis.budget);
    $("productCountLabel").textContent = analysis.product_count + " products";

    // ---- dashboard stat cards
    $("cardBudget").textContent = fmt(analysis.budget);
    $("cardPlanned").textContent = fmt(t.planned_cost);
    $("cardRemaining").textContent = fmt(t.remaining_budget);
    $("cardSavings").textContent = fmt(t.savings);

    // ---- budget health
    var style = STATUS_STYLE[analysis.status] || STATUS_STYLE["Safe"];
    var badge = $("statusBadge");
    badge.textContent = analysis.status.toUpperCase();
    badge.className = "badge " + style.badge;

    $("usageLabel").textContent = t.usage_percent.toFixed(1) + "% used";
    var fill = $("progressFill");
    fill.className = "progress-fill " + style.fill;
    fill.style.width = Math.min(Math.max(t.usage_percent, 0), 100) + "%";

    if (analysis.budget <= 0) {
      $("budgetHealthText").textContent = "Set a budget to start tracking your shopping plan.";
    } else if (analysis.is_over_budget) {
      var over = t.planned_cost - analysis.budget;
      $("budgetHealthText").textContent = "Planned spending is " + fmt(over) + " above your budget.";
    } else {
      $("budgetHealthText").textContent = fmt(t.remaining_budget) + " remains available in your shopping budget.";
    }
    $("overBudgetLabel").textContent = analysis.is_over_budget
      ? "\u26A0 Over budget by " + fmt(t.planned_cost - analysis.budget)
      : "";

    // ---- recommendations (dashboard shows the first four, like the desktop app)
    var recHtml = "";
    analysis.recommendations.slice(0, 4).forEach(function (rec) {
      var lower = rec.toLowerCase();
      var icon = "\uD83D\uDCA1";
      if (lower.indexOf("exceeds") !== -1 || lower.indexOf("over") !== -1) { icon = "\u26A0"; }
      else if (lower.indexOf("discount") !== -1 || lower.indexOf("good time") !== -1) { icon = "\uD83D\uDD25"; }
      recHtml += '<div class="rec-card"><span class="rec-icon">' + icon +
        '</span><p class="rec-text">' + esc(rec) + "</p></div>";
    });
    $("recommendations").innerHTML = recHtml || '<p class="muted">No insights yet.</p>';

    // ---- priority breakdown
    var priorityTotals = analysis.spending_by_priority || {};
    var maxPriority = 0;
    Object.keys(priorityTotals).forEach(function (key) {
      maxPriority = Math.max(maxPriority, priorityTotals[key]);
    });
    var priorityHtml = "";
    ["High", "Medium", "Low"].forEach(function (priority) {
      var amount = priorityTotals[priority] || 0;
      var percent = maxPriority > 0 ? (amount / maxPriority) * 100 : 0;
      priorityHtml +=
        '<div class="priority-row">' +
        '<span class="priority-name">' + priority + "</span>" +
        '<span class="priority-bar"><span class="priority-bar-fill" style="width:' +
        percent.toFixed(1) + "%;background:" + PRIORITY_COLOR[priority] + '"></span></span>' +
        '<span class="priority-amount" style="color:' + PRIORITY_COLOR[priority] + '">' +
        fmt(amount) + "</span></div>";
    });
    $("priorityPanel").innerHTML = priorityHtml;

    renderTable();
    renderSummary();
    renderAnalyticsStats();
  }

  function renderTable() {
    var body = $("productTableBody");
    var rows = analysis.visible_products || [];
    var html = "";

    rows.forEach(function (product) {
      var selected = product.index === selectedIndex ? " is-selected" : "";
      var priorityClass = "tag-" + String(product.priority).toLowerCase();
      var discountClass = "num" + (product.discount > 40 ? " discount-strong" : "");
      html +=
        '<tr data-index="' + product.index + '" class="row' + selected + '">' +
        '<td><span class="cell-name">' + esc(product.name) + "</span>" +
        '<span class="cell-sub">' + (product.quantity > 1 ? product.quantity + " units" : "Single unit") + "</span></td>" +
        '<td><span class="tag tag-cat">' + esc(product.category) + "</span></td>" +
        '<td class="num">' + fmt(product.original_price) + "</td>" +
        '<td class="' + discountClass + '">' + Number(product.discount).toFixed(0) + "%</td>" +
        '<td class="num">' + fmt(product.discounted_price) + "</td>" +
        '<td class="num">' + product.quantity + "</td>" +
        '<td class="num"><strong>' + fmt(product.total_cost) + "</strong></td>" +
        '<td><span class="tag ' + priorityClass + '">' + esc(product.priority) + "</span></td>" +
        "</tr>";
    });

    body.innerHTML = html;
    $("tableEmpty").hidden = rows.length > 0;
    $("tableCount").textContent = rows.length + (rows.length === 1 ? " item" : " items") +
      (rows.length !== analysis.product_count ? " of " + analysis.product_count : "");

    var t = analysis.totals;
    $("tableOriginal").textContent = fmt(t.original_cost);
    $("tableSale").textContent = fmt(t.planned_cost);
    $("tableSavings").textContent = fmt(t.savings);

    // column sort indicators (heading text keeps the desktop app's labels)
    document.querySelectorAll(".grid th.sortable").forEach(function (th) {
      var isSorted = th.getAttribute("data-sort") === view.sortKey;
      th.classList.toggle("is-sorted", isSorted);
      var label = th.getAttribute("data-label") || th.getAttribute("data-sort");
      th.textContent = label + (isSorted ? (view.reverse ? " \u2193" : " \u2191") : "");
    });

    $("sortDirBtn").innerHTML = view.reverse ? "Desc &#8595;" : "Asc &#8593;";
    $("editSelectedBtn").disabled = selectedIndex === null;
    $("deleteSelectedBtn").disabled = selectedIndex === null;
  }

  function renderAnalyticsStats() {
    var categories = Object.keys(analysis.spending_by_category || {});
    var t = analysis.totals;
    $("analyticsCount").textContent = String(analysis.product_count);
    $("analyticsCategories").textContent = String(categories.length);
    var rate = t.original_cost > 0 ? (t.savings / t.original_cost) * 100 : 0;
    $("analyticsSavingsRate").textContent = rate.toFixed(1) + "%";
  }

  function renderSummary() {
    var t = analysis.totals;
    var counts = analysis.count_by_priority || { High: 0, Medium: 0, Low: 0 };
    var status = analysis.status;
    var style = STATUS_STYLE[status] || STATUS_STYLE["Safe"];

    $("sumBudget").textContent = fmt(analysis.budget);
    $("sumOriginal").textContent = fmt(t.original_cost);
    $("sumPlanned").textContent = fmt(t.planned_cost);
    $("sumSavings").textContent = fmt(t.savings);
    $("sumRemaining").textContent = fmt(t.remaining_budget);

    var summaryBadge = $("summaryStatusBadge");
    summaryBadge.textContent = status.toUpperCase();
    summaryBadge.className = "badge " + style.badge;

    $("summaryItemCounts").textContent =
      "Products planned:  " + analysis.product_count + "\n\n" +
      "\uD83D\uDD34 High priority:    " + counts.High + "\n" +
      "\uD83D\uDFE1 Medium priority:  " + counts.Medium + "\n" +
      "\uD83D\uDFE2 Low priority:     " + counts.Low + "\n\n" +
      "Budget usage:       " + t.usage_percent.toFixed(1) + "%";

    var lines = [
      "SHOPPING PLAN OVERVIEW",
      "",
      pad("Total Budget", fmt(analysis.budget)),
      pad("Original Cost", fmt(t.original_cost)),
      pad("Expected Sale Cost", fmt(t.planned_cost)),
      pad("Expected Savings", fmt(t.savings)),
      pad("Remaining Budget", fmt(t.remaining_budget)),
      "",
      "BUDGET STATUS",
      "",
      status + " \u2014 " + t.usage_percent.toFixed(1) + "% of budget used",
      "",
      "PRIORITY COUNTS",
      "",
      pad("High Priority", String(counts.High)),
      pad("Medium Priority", String(counts.Medium)),
      pad("Low Priority", String(counts.Low)),
      "",
      "CATEGORY SPENDING",
      ""
    ];

    var categoryTotals = analysis.spending_by_category || {};
    var keys = Object.keys(categoryTotals).sort(function (a, b) {
      return categoryTotals[b] - categoryTotals[a];
    });
    if (keys.length) {
      keys.forEach(function (category) {
        lines.push(pad(category, fmt(categoryTotals[category])));
      });
    } else {
      lines.push("No products have been added yet.");
    }
    $("summaryDetails").textContent = lines.join("\n");

    $("summaryRecommendations").innerHTML = analysis.recommendations.map(function (rec) {
      return "<li>" + esc(rec) + "</li>";
    }).join("");
  }

  function pad(label, value) {
    var out = String(label);
    while (out.length < 19) { out += " "; }
    return out + value;
  }

  // -------------------------------------------------------------------- charts
  function refreshCharts(force) {
    var kinds = ["category", "budget", "price", "priority"];
    var signature = JSON.stringify(plan);

    kinds.forEach(function (kind) {
      if (!force && inflightChart[kind] === signature) { return; }
      inflightChart[kind] = signature;

      var img = document.querySelector('.chart-img[data-chart="' + kind + '"]');
      var skeleton = document.querySelector('.chart-skeleton[data-skeleton="' + kind + '"]');
      if (skeleton) { skeleton.className = "chart-skeleton"; skeleton.textContent = ""; skeleton.hidden = false; }
      if (img) { img.hidden = true; }

      api("/api/chart/" + kind, {
        method: "POST",
        raw: true,
        body: { plan: plan, width: 6.2, height: 4.1, dpi: 110 }
      }).then(function (response) {
        return response.blob();
      }).then(function (blob) {
        var url = URL.createObjectURL(blob);
        if (chartUrls[kind]) { URL.revokeObjectURL(chartUrls[kind]); }
        chartUrls[kind] = url;
        if (img) { img.src = url; img.alt = CHART_TITLES[kind]; img.hidden = false; }
        if (skeleton) { skeleton.hidden = true; }
      }).catch(function (error) {
        delete inflightChart[kind];           // allow a retry on the next visit
        if (img) { img.hidden = true; }
        if (skeleton) {
          skeleton.className = "chart-skeleton chart-error";
          skeleton.textContent = CHART_TITLES[kind] + " could not be drawn: " + error.message;
          skeleton.hidden = false;
        }
        setStatus("Could not load the " + kind + " chart: " + error.message, "error");
      });
    });
  }

  // ------------------------------------------------------------------- refresh
  async function refresh(options) {
    options = options || {};
    try {
      var data = await api("/api/analyze", {
        method: "POST",
        body: {
          plan: plan,
          search: view.search,
          category: view.category,
          sort_key: view.sortKey,
          reverse: view.reverse
        }
      });
      render(data);
      if (currentPage === "analytics") { refreshCharts(options.forceCharts); }
    } catch (error) {
      setStatus(error.message, "error");
      toast(error.message, "error");
    }
  }

  var debouncedRefresh = debounce(function () { refresh({ silent: true }); }, 220);

  function commit(message, kind) {
    saveLocal();
    if (message) { toast(message, kind || "success"); }
    return refresh();
  }

  // ================================================================= navigation
  function showPage(page) {
    if (!PAGE_TITLES[page]) { return; }
    currentPage = page;

    document.querySelectorAll(".page").forEach(function (section) {
      section.classList.toggle("is-active", section.id === "page-" + page);
    });
    document.querySelectorAll(".nav-btn").forEach(function (button) {
      button.classList.toggle("is-active", button.getAttribute("data-page") === page);
    });

    $("topTitle").textContent = PAGE_TITLES[page][0];
    $("topSubtitle").textContent = PAGE_TITLES[page][1];
    $("sidebar").classList.remove("is-open");

    // Every page is rendered from the same `analysis` object, so only the
    // Analytics tab needs extra work when it becomes visible (chart PNGs).
    if (page === "analytics") {
      setTimeout(function () { refreshCharts(false); }, 60);
    }
  }

  // ============================================================ product modal
  function openProductForm(index) {
    editingIndex = (index === undefined || index === null) ? null : index;
    $("productModalTitle").textContent = editingIndex === null ? "ADD PRODUCT" : "EDIT PRODUCT";
    $("productSubmitBtn").textContent = editingIndex === null ? "Add Product" : "Save Changes";
    $("formError").hidden = true;
    $("formPreview").textContent = "";

    if (editingIndex !== null && plan.products[editingIndex]) {
      var product = plan.products[editingIndex];
      $("fName").value = product.name;
      $("fPrice").value = product.original_price;
      $("fDiscount").value = product.discount;
      $("fQuantity").value = product.quantity;
      selectValue("fCategory", product.category);
      selectValue("fPriority", product.priority);
    } else {
      $("fName").value = "";
      $("fPrice").value = "";
      $("fDiscount").value = "0";
      $("fQuantity").value = "1";
      $("fCategory").selectedIndex = 0;
      $("fPriority").value = "Medium";
    }

    openModal("productModal");
    setTimeout(function () { $("fName").focus(); }, 40);
    updateFormPreview();
  }

  function readForm() {
    return {
      name: $("fName").value,
      category: $("fCategory").value,
      original_price: $("fPrice").value,
      discount: $("fDiscount").value,
      quantity: $("fQuantity").value,
      priority: $("fPriority").value
    };
  }

  var updateFormPreview = debounce(async function () {
    var preview = $("formPreview");
    var errorBox = $("formError");
    try {
      var data = await api("/api/products/validate", { method: "POST", body: readForm() });
      var product = data.product;
      preview.textContent = "Sale price " + fmt(product.discounted_price) +
        " per unit  \u2022  total " + fmt(product.total_cost) +
        "  \u2022  you save " + fmt(product.total_savings);
      errorBox.hidden = true;
    } catch (error) {
      preview.textContent = "";
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  }, 260);

  // ================================================================== actions
  async function onSetBudget(event) {
    event.preventDefault();
    var raw = $("budgetInput").value;
    try {
      var data = await api("/api/budget/validate", { method: "POST", body: { budget: raw } });
      plan.budget = data.budget;
      $("budgetInput").value = data.budget ? data.budget : "";
      commit(data.reset ? "Budget reset." : "Budget set to " + fmt(data.budget) + ".");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function onResetBudget() {
    var ok = await confirmDialog(
      "Reset budget?",
      "This sets your total shopping budget back to Rs 0.00. Your products are kept.",
      "Reset Budget"
    );
    if (!ok) { return; }
    plan.budget = 0;
    $("budgetInput").value = "";
    commit("Budget reset.");
  }

  /**
   * Set a <select> to `value`, adding the option first when a loaded JSON plan
   * uses a category/priority that is not in the standard list.
   */
  function selectValue(selectId, value) {
    var select = $(selectId);
    var text = String(value === null || value === undefined ? "" : value);
    var found = Array.prototype.some.call(select.options, function (option) {
      return option.value === text;
    });
    if (!found && text) {
      var option = document.createElement("option");
      option.value = text;
      option.textContent = text + " (custom)";
      select.appendChild(option);
    }
    select.value = text;
  }

  async function onProductSubmit(event) {
    event.preventDefault();
    var errorBox = $("formError");
    try {
      var data = await api("/api/products/validate", { method: "POST", body: readForm() });
      var product = data.product;
      var record = {
        name: product.name,
        category: product.category,
        original_price: product.original_price,
        discount: product.discount,
        quantity: product.quantity,
        priority: product.priority
      };
      if (editingIndex === null) {
        plan.products.push(record);
        selectedIndex = plan.products.length - 1;
        closeModal("productModal");
        commit("'" + record.name + "' added to your plan.");
      } else {
        plan.products[editingIndex] = record;
        selectedIndex = editingIndex;
        closeModal("productModal");
        commit("'" + record.name + "' updated.");
      }
      errorBox.hidden = true;
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
      setStatus(error.message, "error");
    }
  }

  async function onDeleteSelected() {
    if (selectedIndex === null || !plan.products[selectedIndex]) {
      toast("Select a product row first.", "error");
      return;
    }
    var product = plan.products[selectedIndex];
    var ok = await confirmDialog(
      "Delete product?",
      "'" + product.name + "' will be removed from your shopping plan.",
      "Delete"
    );
    if (!ok) { return; }
    plan.products.splice(selectedIndex, 1);
    selectedIndex = null;
    commit("'" + product.name + "' deleted.");
  }

  async function onClearAll() {
    if (!plan.products.length) {
      toast("Your shopping list is already empty.", "error");
      return;
    }
    var ok = await confirmDialog(
      "Clear all products?",
      "All " + plan.products.length + " planned purchases will be removed. Your budget is kept.",
      "Clear All"
    );
    if (!ok) { return; }
    plan.products = [];
    selectedIndex = null;
    commit("Shopping list cleared.");
  }

  function onSavePlan() {
    var blob = new Blob([JSON.stringify(plan, null, 4)], { type: "application/json" });
    downloadBlob(blob, "shopping_plan.json");
    toast("Plan saved as shopping_plan.json.", "success");
  }

  function onLoadPlan() { $("fileInput").click(); }

  async function onFileChosen(event) {
    var file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) { return; }
    try {
      var text = await file.text();
      var parsed = JSON.parse(text);
      var data = await api("/api/plan/validate", { method: "POST", body: { plan: parsed } });
      plan = data.plan;
      selectedIndex = null;
      commit("Loaded '" + file.name + "' (" + plan.products.length + " products).");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function onLoadSample() {
    try {
      var data = await api("/api/sample");
      plan = data.plan;
      selectedIndex = null;
      commit("Sample plan loaded (" + plan.products.length + " fictional products).");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  async function onExportCsv() {
    try {
      setStatus("Preparing CSV export...", "normal");
      var response = await api("/api/export/csv", { method: "POST", raw: true, body: { plan: plan } });
      var blob = await response.blob();
      downloadBlob(blob, "shopping_summary.csv");
      toast("shopping_summary.csv exported.", "success");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function downloadBlob(blob, filename) {
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  }

  async function onBankSubmit(event) {
    event.preventDefault();
    var errorBox = $("bankError");
    var result = $("bankResult");
    try {
      var data = await api("/api/bank-offer", {
        method: "POST",
        body: {
          subtotal: $("bSubtotal").value,
          bank_pct: $("bBankPct").value,
          max_discount: $("bMaxDiscount").value,
          coupon: $("bCoupon").value
        }
      });
      errorBox.hidden = true;
      result.hidden = false;
      result.textContent =
        "Bank discount: " + data.bank_discount + (data.capped ? " (capped)" : "") + "\n" +
        "Total discount: " + data.total_discount + "\n" +
        "Final price: " + data.final_price;
    } catch (error) {
      result.hidden = true;
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  }

  // ==================================================================== wiring
  function wire() {
    // navigation
    document.querySelectorAll(".nav-btn").forEach(function (button) {
      button.addEventListener("click", function () { showPage(button.getAttribute("data-page")); });
    });
    $("hamburger").addEventListener("click", function () {
      $("sidebar").classList.toggle("is-open");
    });

    // global action buttons (sidebar + inline)
    document.body.addEventListener("click", function (event) {
      var target = event.target;
      if (!target || typeof target.closest !== "function") { return; }
      var trigger = target.closest("[data-action]");
      if (!trigger) { return; }
      var action = trigger.getAttribute("data-action");
      if (action === "add-product") { openProductForm(null); }
      if (action === "save-plan") { onSavePlan(); }
      if (action === "load-plan") { onLoadPlan(); }
      if (action === "load-sample") { onLoadSample(); }
      if (action === "export-csv") { onExportCsv(); }
      if (action === "bank-calculator") {
        $("bankResult").hidden = true;
        $("bankError").hidden = true;
        // Pre-fill with the current planned spending, like a real checkout total.
        var subtotal = analysis && analysis.totals ? analysis.totals.planned_cost : 0;
        if (!$("bSubtotal").value && subtotal > 0) { $("bSubtotal").value = subtotal; }
        openModal("bankModal");
      }
    });

    // modal close buttons + backdrop clicks
    document.querySelectorAll("[data-close]").forEach(function (button) {
      button.addEventListener("click", function () { closeModal(button.getAttribute("data-close")); });
    });
    document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
      backdrop.addEventListener("click", function (event) {
        if (event.target === backdrop) { closeModal(backdrop.id); }
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        document.querySelectorAll(".modal-backdrop:not([hidden])").forEach(function (backdrop) {
          closeModal(backdrop.id);
        });
      }
    });

    // budget
    $("budgetForm").addEventListener("submit", onSetBudget);
    $("resetBudgetBtn").addEventListener("click", onResetBudget);

    // product form
    $("productForm").addEventListener("submit", onProductSubmit);
    ["fName", "fPrice", "fDiscount", "fQuantity"].forEach(function (id) {
      $(id).addEventListener("input", updateFormPreview);
    });
    ["fCategory", "fPriority"].forEach(function (id) {
      $(id).addEventListener("change", updateFormPreview);
    });

    // bank calculator
    $("bankForm").addEventListener("submit", onBankSubmit);

    // table interactions
    $("productTableBody").addEventListener("click", function (event) {
      var row = event.target.closest("tr[data-index]");
      if (!row) { return; }
      selectedIndex = Number(row.getAttribute("data-index"));
      renderTable();
    });
    $("productTableBody").addEventListener("dblclick", function (event) {
      var row = event.target.closest("tr[data-index]");
      if (!row) { return; }
      openProductForm(Number(row.getAttribute("data-index")));
    });
    $("editSelectedBtn").addEventListener("click", function () {
      if (selectedIndex === null) { toast("Select a product row first.", "error"); return; }
      openProductForm(selectedIndex);
    });
    $("deleteSelectedBtn").addEventListener("click", onDeleteSelected);
    $("clearAllBtn").addEventListener("click", onClearAll);

    // column heading sort (same behaviour as clicking a Treeview heading)
    document.querySelectorAll(".grid th.sortable").forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort");
        if (view.sortKey === key) { view.reverse = !view.reverse; }
        else { view.sortKey = key; view.reverse = false; }
        $("sortBy").value = view.sortKey;
        saveLocal();
        refresh({ silent: true });
      });
    });

    // search / filter / sort toolbar
    $("searchInput").addEventListener("input", function () {
      view.search = $("searchInput").value;
      selectedIndex = null;
      saveLocal();
      debouncedRefresh();
    });
    $("categoryFilter").addEventListener("change", function () {
      view.category = $("categoryFilter").value;
      selectedIndex = null;
      saveLocal();
      refresh({ silent: true });
    });
    $("sortBy").addEventListener("change", function () {
      view.sortKey = $("sortBy").value;
      saveLocal();
      refresh({ silent: true });
    });
    $("sortDirBtn").addEventListener("click", function () {
      view.reverse = !view.reverse;
      saveLocal();
      refresh({ silent: true });
    });

    // file loading + summary printing
    $("fileInput").addEventListener("change", onFileChosen);
    $("printBtn").addEventListener("click", function () { window.print(); });

    // keyboard shortcuts (mirrors the desktop app's bindings)
    document.addEventListener("keydown", function (event) {
      var mod = event.ctrlKey || event.metaKey;
      if (!mod) { return; }
      var key = event.key.toLowerCase();
      if (key === "s") { event.preventDefault(); onSavePlan(); }
      else if (key === "o") { event.preventDefault(); onLoadPlan(); }
      else if (key === "e") { event.preventDefault(); onExportCsv(); }
      else if (key === "n") { event.preventDefault(); openProductForm(null); }
    });
    document.addEventListener("keydown", function (event) {
      if ((event.key === "Delete") && currentPage === "shopping" && selectedIndex !== null) {
        var tag = (event.target.tagName || "").toLowerCase();
        if (tag === "input" || tag === "select" || tag === "textarea") { return; }
        event.preventDefault();
        onDeleteSelected();
      }
    });
  }

  function populateSelects(categories) {
    var filter = $("categoryFilter");
    filter.innerHTML = '<option value="All">All Categories</option>' +
      categories.map(function (category) {
        return '<option value="' + esc(category) + '">' + esc(category) + "</option>";
      }).join("");
    filter.value = categories.indexOf(view.category) === -1 ? "All" : view.category;
    view.category = filter.value;

    if ($("fCategory").options.length === 0) {
      $("fCategory").innerHTML = categories.map(function (category) {
        return '<option value="' + esc(category) + '">' + esc(category) + "</option>";
      }).join("");
    }
  }

  // ==================================================================== boot
  async function boot() {
    loadLocal();
    wire();

    $("budgetInput").value = plan.budget ? String(plan.budget) : "";
    $("searchInput").value = view.search;
    $("sortBy").value = view.sortKey;

    try {
      var meta = await api("/api/meta");
      populateSelects(meta.categories);
      showPage("dashboard");
      await refresh({ silent: true });
      setStatus(
        plan.products.length
          ? "Restored your plan from this browser (" + plan.products.length + " products)."
          : "Ready \u2014 set a budget, then add products (or load the sample plan).",
        "normal"
      );
    } catch (error) {
      populateSelects([]);
      showPage("dashboard");
      setStatus(error.message, "error");
      toast("Could not reach the planner API: " + error.message, "error");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
