async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

function setError(msg) {
  const el = document.getElementById("pinError");
  if (!el) return;
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("pinForm");
  const input = document.getElementById("pinInput");

  const devHintBtn = document.getElementById("devHintBtn");
  const devHintPanel = document.getElementById("devHintPanel");

  if (input) input.focus();

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    setError("");

    const pin = input ? input.value : "";
    const { ok, data } = await postJson("/api/auth/pin", { pin });

    if (!ok) {
      setError(data && data.error ? data.error : "Falha ao autenticar.");
      return;
    }

    window.location.href = "/admin";
  });

  const setHintOpen = (open) => {
    if (!devHintPanel || !devHintBtn) return;
    devHintPanel.hidden = !open;
    devHintBtn.setAttribute("aria-expanded", String(open));
  };

  if (devHintBtn && devHintPanel) {
    devHintBtn.addEventListener("click", () => {
      setHintOpen(devHintPanel.hidden);
    });

    document.addEventListener("click", (e) => {
      const t = e.target;
      if (!(t instanceof Element)) return;
      if (t === devHintBtn || devHintPanel.contains(t)) return;
      setHintOpen(false);
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") setHintOpen(false);
    });
  }
});
