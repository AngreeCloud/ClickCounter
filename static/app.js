async function fetchJson(url, options) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data && data.error ? data.error : "Erro inesperado.";
    throw new Error(msg);
  }
  return data;
}

function formatClick(click) {
  return `#${click.seq} · ${click.button} · ${click.date} · ${click.time}`;
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function renderLastClick(lastClick) {
  const el = document.getElementById("lastClickText");
  if (!el) return;

  if (!lastClick) {
    el.textContent = "Ainda não há cliques hoje.";
    return;
  }

  el.textContent = formatClick(lastClick);
}

function renderClickList(clicks) {
  const list = document.getElementById("clickList");
  if (!list) return;

  list.innerHTML = "";
  for (const click of clicks) {
    const li = document.createElement("li");
    li.textContent = formatClick(click);
    list.appendChild(li);
  }
}

async function refreshAll() {
  const status = await fetchJson("/api/status");
  setText("statusDate", status.date || "—");
  setText("statusCounter", String(status.counter ?? "—"));
  setText("statusTotalToday", String(status.clicksToday ?? "—"));
  renderLastClick(status.lastClick);

  const clicks = await fetchJson("/api/clicks/today");
  renderClickList(clicks.clicks || []);
}

function setButtonsDisabled(disabled) {
  document.querySelectorAll("button[data-button]").forEach((btn) => {
    btn.disabled = disabled;
  });
}

async function handleClick(buttonName) {
  setButtonsDisabled(true);
  try {
    const record = await fetchJson("/api/click", {
      method: "POST",
      body: JSON.stringify({ button: buttonName }),
    });

    // Atualiza status e lista
    await refreshAll();

    // Pequeno destaque no último clique
    renderLastClick(record);
  } finally {
    setButtonsDisabled(false);
  }
}

function wireUi() {
  document.querySelectorAll("button[data-button]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const name = btn.getAttribute("data-button");
      if (!name) return;

      try {
        await handleClick(name);
      } catch (err) {
        alert(err.message || "Erro ao registar clique.");
      }
    });
  });

  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      try {
        await refreshAll();
      } catch (err) {
        alert(err.message || "Erro ao atualizar.");
      }
    });
  }
}

(async function init() {
  wireUi();
  try {
    await refreshAll();
  } catch (err) {
    console.error(err);
  }
})();
