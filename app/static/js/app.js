const API = "/api";

// ---------- Navigation ----------

document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.section}`).classList.add("active");
    refreshSection(btn.dataset.section);
  });
});

// ---------- Helpers ----------

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const msg = (body && body.error) ? body.error : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return body;
}

function fmtDate(s) {
  if (!s) return "–";
  return s.replace("T", " ").slice(0, 16);
}

function money(n) {
  return `$${Number(n).toFixed(2)}`;
}

async function checkConnection() {
  const dot = document.getElementById("connDot");
  const label = document.getElementById("connLabel");
  try {
    await fetch(`${API}/health`);
    dot.className = "pulse-dot ok";
    label.textContent = "Connected";
  } catch (e) {
    dot.className = "pulse-dot err";
    label.textContent = "Offline";
  }
}

// ---------- Overview ----------

async function loadOverview() {
  const [items, lowStock, taskLoad, orders] = await Promise.all([
    api("/items"),
    api("/reports/low-stock"),
    api("/reports/task-load"),
    api("/orders"),
  ]);

  document.getElementById("statItems").textContent = items.length;
  document.getElementById("statLowStock").textContent = lowStock.length;
  document.getElementById("statOpenTasks").textContent = taskLoad.open || 0;
  document.getElementById("statOrders").textContent = orders.length;

  const tbody = document.querySelector("#overviewLowStockTable tbody");
  tbody.innerHTML = "";
  document.getElementById("overviewLowStockEmpty").hidden = lowStock.length > 0;
  lowStock.slice(0, 8).forEach(item => {
    const tr = document.createElement("tr");
    tr.className = "row-danger";
    tr.innerHTML = `
      <td class="mono">${item.sku}</td>
      <td>${item.name}</td>
      <td>${item.category}</td>
      <td class="mono">${item.quantity}</td>
      <td class="mono">${item.reorder_threshold}</td>`;
    tbody.appendChild(tr);
  });

  const next = await api("/tasks/next");
  const nextEl = document.getElementById("overviewNextTask");
  if (next.title) {
    nextEl.innerHTML = `
      <div class="next-task-title">${next.title}</div>
      <div class="next-task-desc">${next.description || "No description."} — priority ${next.priority}</div>`;
  } else {
    nextEl.innerHTML = `<p class="empty-note">No open tasks.</p>`;
  }
}

// ---------- Items ----------

async function loadItems(sortByQty = false) {
  const items = await api(`/items${sortByQty ? "?sort=quantity" : ""}`);
  const tbody = document.querySelector("#itemsTable tbody");
  tbody.innerHTML = "";
  items.forEach(item => {
    const tr = document.createElement("tr");
    tr.className = item.is_low_stock ? "row-danger" : "row-ok";
    tr.innerHTML = `
      <td class="mono">${item.sku}</td>
      <td>${item.name}</td>
      <td>${item.category}</td>
      <td class="mono">${item.quantity}</td>
      <td class="mono">${item.reorder_threshold}</td>
      <td class="mono">${money(item.unit_price)}</td>
      <td><button class="btn-tiny" data-del="${item.id}">Delete</button></td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll("[data-del]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api(`/items/${btn.dataset.del}`, { method: "DELETE" });
      loadItems(sortByQty);
      populateItemSelects();
    });
  });
}

document.getElementById("sortByQtyBtn").addEventListener("click", () => loadItems(true));

document.getElementById("itemForm").addEventListener("submit", async e => {
  e.preventDefault();
  const errEl = document.getElementById("itemFormError");
  errEl.hidden = true;
  const form = new FormData(e.target);
  try {
    await api("/items", {
      method: "POST",
      body: JSON.stringify({
        sku: form.get("sku"),
        name: form.get("name"),
        category: form.get("category"),
        quantity: Number(form.get("quantity")),
        reorder_threshold: Number(form.get("reorder_threshold")),
        unit_price: Number(form.get("unit_price")),
      }),
    });
    e.target.reset();
    loadItems();
    populateItemSelects();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

// ---------- Tasks ----------

let currentTaskFilter = "";

async function loadTasks() {
  const tasks = await api(`/tasks${currentTaskFilter ? `?status=${currentTaskFilter}` : ""}`);
  const tbody = document.querySelector("#tasksTable tbody");
  tbody.innerHTML = "";
  tasks.forEach(task => {
    const tr = document.createElement("tr");
    const statusClass = `status-${task.status}`;
    let actionBtn = "";
    if (task.status === "open") {
      actionBtn = `<button class="btn-tiny" data-start="${task.id}">Start</button>`;
    } else if (task.status === "in-progress") {
      actionBtn = `<button class="btn-tiny" data-complete="${task.id}">Complete</button>`;
    }
    tr.innerHTML = `
      <td class="mono">${task.priority}</td>
      <td>${task.title}</td>
      <td><span class="status-pill ${statusClass}">${task.status}</span></td>
      <td class="mono">${fmtDate(task.created_at)}</td>
      <td>${actionBtn}</td>`;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll("[data-start]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api(`/tasks/${btn.dataset.start}/start`, { method: "PUT" });
      loadTasks();
    });
  });
  tbody.querySelectorAll("[data-complete]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api(`/tasks/${btn.dataset.complete}/complete`, { method: "PUT" });
      loadTasks();
    });
  });
}

document.querySelectorAll(".filter-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    currentTaskFilter = tab.dataset.status;
    loadTasks();
  });
});

document.getElementById("taskForm").addEventListener("submit", async e => {
  e.preventDefault();
  const form = new FormData(e.target);
  await api("/tasks", {
    method: "POST",
    body: JSON.stringify({
      title: form.get("title"),
      description: form.get("description") || "",
      priority: Number(form.get("priority")),
    }),
  });
  e.target.reset();
  loadTasks();
});

// ---------- Orders ----------

async function populateItemSelects() {
  const items = await api("/items");
  const orderSelect = document.getElementById("orderItemSelect");
  const forecastSelect = document.getElementById("forecastItemSelect");
  [orderSelect, forecastSelect].forEach(sel => {
    const placeholder = sel.querySelector("option[disabled]");
    sel.innerHTML = "";
    sel.appendChild(placeholder);
    items.forEach(item => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = `${item.sku} — ${item.name} (${item.quantity} in stock)`;
      sel.appendChild(opt);
    });
  });
}

async function loadOrders() {
  const orders = await api("/orders");
  const tbody = document.querySelector("#ordersTable tbody");
  tbody.innerHTML = "";
  orders.forEach(o => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="status-pill ${o.order_type === 'sale' ? 'status-in-progress' : 'status-closed'}">${o.order_type}</span></td>
      <td class="mono">${o.item_id}</td>
      <td class="mono">${o.quantity}</td>
      <td class="mono">${fmtDate(o.created_at)}</td>`;
    tbody.appendChild(tr);
  });
}

document.getElementById("orderForm").addEventListener("submit", async e => {
  e.preventDefault();
  const errEl = document.getElementById("orderFormError");
  const okEl = document.getElementById("orderFormSuccess");
  errEl.hidden = true;
  okEl.hidden = true;
  const form = new FormData(e.target);
  try {
    const result = await api("/orders", {
      method: "POST",
      body: JSON.stringify({
        item_id: Number(form.get("item_id")),
        quantity: Number(form.get("quantity")),
        order_type: form.get("order_type"),
      }),
    });
    let msg = `Logged. Item now at ${result.item_quantity_after} units.`;
    if (result.auto_generated_restock_task_id) {
      msg += " A restock task was auto-created.";
    }
    okEl.textContent = msg;
    okEl.hidden = false;
    e.target.reset();
    loadOrders();
    populateItemSelects();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.hidden = false;
  }
});

// ---------- Reports ----------

async function loadReports() {
  const lowStock = await api("/reports/low-stock");
  const lowBody = document.querySelector("#reportLowStockTable tbody");
  lowBody.innerHTML = "";
  lowStock.forEach(item => {
    const tr = document.createElement("tr");
    tr.className = "row-danger";
    tr.innerHTML = `
      <td class="mono">${item.sku}</td>
      <td>${item.name}</td>
      <td class="mono">${item.quantity}</td>
      <td class="mono">${item.reorder_threshold}</td>`;
    lowBody.appendChild(tr);
  });

  const salesTrend = await api("/reports/sales-trend");
  const salesBody = document.querySelector("#reportSalesTable tbody");
  salesBody.innerHTML = "";
  document.getElementById("reportSalesEmpty").hidden = salesTrend.length > 0;
  salesTrend.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.category}</td>
      <td class="mono">${row.order_date}</td>
      <td class="mono">${row.units_sold}</td>
      <td class="mono">${money(row.revenue)}</td>`;
    salesBody.appendChild(tr);
  });
}

document.getElementById("forecastForm").addEventListener("submit", async e => {
  e.preventDefault();
  const form = new FormData(e.target);
  const itemId = form.get("item_id");
  const result = await api(`/reports/restock-prediction/${itemId}`);
  const el = document.getElementById("forecastResult");
  el.hidden = false;
  const days = result.predicted_days_until_stockout;
  el.innerHTML = `
    <div class="forecast-headline">${days === null ? "No forecast yet" : `${days} days until stockout`}</div>
    <div class="forecast-sub">${result.recommendation} — confidence: ${result.confidence} — avg usage: ${result.avg_daily_usage}/day</div>`;
});

// ---------- Section refresh dispatch ----------

function refreshSection(section) {
  if (section === "overview") loadOverview();
  if (section === "items") loadItems();
  if (section === "tasks") loadTasks();
  if (section === "orders") { loadOrders(); populateItemSelects(); }
  if (section === "reports") { loadReports(); populateItemSelects(); }
}

// ---------- Init ----------

checkConnection();
loadOverview();
populateItemSelects();
