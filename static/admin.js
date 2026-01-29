async function fetchJson(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data && data.error ? data.error : "Falha ao carregar stats");
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data && data.error ? data.error : "Erro");
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function buildPerButtonChart(ctx, perButton, buttonLabels) {
  const labels = [
    buttonLabels[1] || "Botão 1",
    buttonLabels[2] || "Botão 2",
    buttonLabels[3] || "Botão 3",
    buttonLabels[4] || "Botão 4",
  ];
  const data = [perButton[1] || 0, perButton[2] || 0, perButton[3] || 0, perButton[4] || 0];

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Cliques",
          data,
          backgroundColor: ["#7c3aed", "#22c55e", "#3b82f6", "#f43f5e"],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function buildPerDayChart(ctx, perDay) {
  const labels = perDay.map((x) => x.date);
  const data = perDay.map((x) => x.count);

  return new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Cliques/dia",
          data,
          borderColor: "#a78bfa",
          backgroundColor: "rgba(167, 139, 250, 0.18)",
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function buildPerHourChart(ctx, perHourToday) {
  const hourToCount = new Map(perHourToday.map((x) => [x.hour, x.count]));
  const labels = [];
  const data = [];
  for (let h = 0; h < 24; h++) {
    labels.push(String(h).padStart(2, "0") + ":00");
    data.push(hourToCount.get(h) || 0);
  }

  return new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Cliques",
          data,
          backgroundColor: "rgba(34, 197, 94, 0.35)",
          borderColor: "rgba(34, 197, 94, 0.8)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

(async function init() {
  const logoutBtn = document.getElementById("logoutBtn");
  const helpModal = document.getElementById("helpModal");
  const helpBtn = document.getElementById("helpBtn");
  const helpClose = document.getElementById("helpClose");

  const exportSplit = document.getElementById("exportSplit");
  const exportToggle = document.getElementById("exportToggle");
  const exportMenu = document.getElementById("exportMenu");

  const setHelpOpen = (open) => {
    if (!helpModal) return;
    helpModal.hidden = !open;
  };

  if (helpBtn) {
    helpBtn.addEventListener("click", () => setHelpOpen(true));
  }
  if (helpClose) helpClose.addEventListener("click", () => setHelpOpen(false));
  if (helpModal) {
    helpModal.addEventListener("click", (e) => {
      if (e.target === helpModal) setHelpOpen(false);
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      setHelpOpen(false);
      if (exportMenu) exportMenu.hidden = true;
      if (exportToggle) exportToggle.setAttribute("aria-expanded", "false");
    }
  });

  const setExportMenuOpen = (open) => {
    if (!exportMenu || !exportToggle) return;
    exportMenu.hidden = !open;
    exportToggle.setAttribute("aria-expanded", open ? "true" : "false");
  };

  if (exportToggle && exportMenu) {
    exportToggle.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      setExportMenuOpen(exportMenu.hidden);
    });
  }

  document.addEventListener("click", (e) => {
    if (!exportMenu || exportMenu.hidden) return;
    if (exportSplit && exportSplit.contains(e.target)) return;
    setExportMenuOpen(false);
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      logoutBtn.disabled = true;
      try {
        await postJson("/api/auth/logout");
        window.location.href = "/";
      } catch (err) {
        alert(err.message || "Erro ao terminar sessão.");
        logoutBtn.disabled = false;
      }
    });
  }

  let stats = null;
  try {
    stats = await fetchJson("/api/admin/stats");
  } catch (err) {
    console.error("Falha ao carregar estatísticas", err);
    if (err && err.status === 401) {
      window.location.href = "/";
      return;
    }
  }

  const safeStats = stats || { perButton: {}, perDay: [], perHourToday: [] };
  setText("totalAll", stats && stats.total != null ? String(stats.total) : "—");
  setText("totalToday", stats && stats.today != null ? String(stats.today) : "—");

  const perButtonCtx = document.getElementById("perButtonChart");
  const perDayCtx = document.getElementById("perDayChart");
  const perHourCtx = document.getElementById("perHourChart");

  const buttonLabels = (stats && stats.buttonLabels) || {};
  if (perButtonCtx) buildPerButtonChart(perButtonCtx, safeStats.perButton || {}, buttonLabels);
  if (perDayCtx) buildPerDayChart(perDayCtx, safeStats.perDay || []);
  if (perHourCtx) buildPerHourChart(perHourCtx, safeStats.perHourToday || []);
})();
