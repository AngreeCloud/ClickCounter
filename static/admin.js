async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error("Falha ao carregar stats");
  return res.json();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data && data.error ? data.error : "Erro");
  return data;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function buildPerButtonChart(ctx, perButton) {
  const labels = ["Botão 1", "Botão 2", "Botão 3", "Botão 4"];
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
  const stats = await fetchJson("/api/admin/stats");

  setText("totalAll", String(stats.total ?? "—"));
  setText("totalToday", String(stats.today ?? "—"));

  const perButtonCtx = document.getElementById("perButtonChart");
  const perDayCtx = document.getElementById("perDayChart");
  const perHourCtx = document.getElementById("perHourChart");

  if (perButtonCtx) buildPerButtonChart(perButtonCtx, stats.perButton || {});
  if (perDayCtx) buildPerDayChart(perDayCtx, stats.perDay || []);
  if (perHourCtx) buildPerHourChart(perHourCtx, stats.perHourToday || []);

  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await postJson("/api/auth/logout");
      window.location.href = "/";
    });
  }
})();
