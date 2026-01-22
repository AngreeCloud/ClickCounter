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

function renderLastClick(lastClick) {
  const el = document.getElementById("lastClickText");
  if (!el) return;

  if (!lastClick) {
    el.textContent = "Ainda não há cliques hoje.";
    return;
  }

  el.textContent = formatClick(lastClick);
}

async function loadLastClick() {
  const status = await fetchJson("/api/status");
  renderLastClick(status.lastClick);
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

    // Mostra imediatamente o resultado devolvido pelo backend
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
}

(async function init() {
  wireUi();
  try {
    await loadLastClick();
  } catch (err) {
    console.error(err);
  }
})();
