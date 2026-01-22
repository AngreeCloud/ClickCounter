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

function notifyClick(record) {
  const container = document.getElementById("notifications");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `
    <strong>Clique registado (Botão ${record.button})</strong><br>
    <small>Seq: ${record.seq} | Hora: ${record.time}</small>
  `;

  container.appendChild(toast);

  // Remover após 3 segundos
  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

function setButtonsDisabled(disabled) {
  document.querySelectorAll("button[data-button-id]").forEach((btn) => {
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

    notifyClick(record);
  } finally {
    setButtonsDisabled(false);
  }
}

function wireUi() {
  document.querySelectorAll("button[data-button-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const buttonName = btn.innerText.trim();
      try {
        await handleClick(buttonName);
      } catch (err) {
        // Fallback para erro simples se a notificação UI falhar
        alert(err.message || "Erro ao registar clique.");
      }
    });
  });
}

(async function init() {
  wireUi();
})();
