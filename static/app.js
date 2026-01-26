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

async function handleClick(buttonId) {
  setButtonsDisabled(true);
  try {
    const record = await fetchJson("/api/click", {
      method: "POST",
      body: JSON.stringify({ button_id: buttonId }),
    });

    // Mantendo a compatibilidade visual com o que já foi feito,
    // mas garantindo que usamos a resposta do servidor
    const displayRecord = {
      button: `Botão ${record.button_id}`,
      seq: record.seq,
      time: record.time
    };
    notifyClick(displayRecord);
  } finally {
    setButtonsDisabled(false);
  }
}

function wireUi() {
  document.querySelectorAll("button[data-button-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const buttonId = parseInt(btn.getAttribute("data-button-id"));
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
