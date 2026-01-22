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

async function ensureNotificationPermission() {
  if (!("Notification" in window)) return "unsupported";
  if (Notification.permission === "granted") return "granted";
  if (Notification.permission === "denied") return "denied";

  try {
    const permission = await Notification.requestPermission();
    return permission;
  } catch {
    return "denied";
  }
}

function notifyClick(record) {
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;

  const title = `Clique registado (Botão ${record.button_id})`;
  const body = `Seq: ${record.seq}\nData: ${record.date}\nHora: ${record.time}`;
  new Notification(title, { body });
}

function setButtonsDisabled(disabled) {
  document.querySelectorAll("button[data-button-id]").forEach((btn) => {
    btn.disabled = disabled;
  });
}

async function handleClick(buttonId) {
  setButtonsDisabled(true);
  try {
    const record = await fetchJson("/api/click", {
      method: "POST",
      body: JSON.stringify({ button_id: buttonId }),
    });

    notifyClick(record);
  } finally {
    setButtonsDisabled(false);
  }
}

function wireUi() {
  document.querySelectorAll("button[data-button-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idRaw = btn.getAttribute("data-button-id");
      const buttonId = Number(idRaw);
      if (!Number.isInteger(buttonId) || buttonId < 1) return;

      // Pedir permissão no contexto de uma ação do utilizador.
      await ensureNotificationPermission();

      try {
        await handleClick(buttonId);
      } catch (err) {
        alert(err.message || "Erro ao registar clique.");
      }
    });
  });
}

(async function init() {
  wireUi();
})();
