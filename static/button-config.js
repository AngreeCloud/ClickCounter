async function fetchJson(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data && data.error ? data.error : "Erro ao carregar");
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
    const err = new Error(data && data.error ? data.error : "Erro ao guardar");
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

async function uploadIcon(buttonId, file) {
  const form = new FormData();
  form.append("icon", file);
  const res = await fetch(`/api/buttons/icon/${buttonId}`, {
    method: "POST",
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data && data.error ? data.error : "Erro ao enviar ícone");
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

function createCard(button) {
  const card = document.createElement("div");
  card.className = "configCard";

  const header = document.createElement("div");
  header.className = "configRow";

  const preview = document.createElement("div");
  preview.className = "configPreview";

  const previewIcon = document.createElement("img");
  previewIcon.alt = "Ícone";

  const previewLabel = document.createElement("div");
  previewLabel.className = "configPreviewLabel";
  previewLabel.textContent = button.label || `Botão ${button.button_id}`;

  if (button.icon_url) {
    previewIcon.src = `${button.icon_url}?v=${button.icon_updated_at || Date.now()}`;
  } else {
    previewIcon.src = "";
  }

  preview.appendChild(previewIcon);
  preview.appendChild(previewLabel);

  const form = document.createElement("div");
  form.className = "configRow";

  const labelWrap = document.createElement("div");
  const labelTitle = document.createElement("div");
  labelTitle.className = "noteText";
  labelTitle.textContent = `Botão ${button.button_id}`;
  const labelInput = document.createElement("input");
  labelInput.className = "inputText";
  labelInput.value = button.label || `Botão ${button.button_id}`;
  labelWrap.appendChild(labelTitle);
  labelWrap.appendChild(labelInput);

  const iconWrap = document.createElement("div");
  const iconTitle = document.createElement("div");
  iconTitle.className = "noteText";
  iconTitle.textContent = "Ícone (PNG, JPG, WEBP, SVG · máx 2MB)";
  const iconInput = document.createElement("input");
  iconInput.className = "fileInput";
  iconInput.type = "file";
  iconInput.accept = "image/png,image/jpeg,image/webp,image/svg+xml";
  iconWrap.appendChild(iconTitle);
  iconWrap.appendChild(iconInput);

  form.appendChild(labelWrap);
  form.appendChild(iconWrap);

  const actions = document.createElement("div");
  actions.className = "configActions";

  const saveBtn = document.createElement("button");
  saveBtn.className = "btn";
  saveBtn.textContent = "Guardar nome";

  const iconBtn = document.createElement("button");
  iconBtn.className = "btn btnGhost";
  iconBtn.textContent = "Enviar ícone";

  const status = document.createElement("div");
  status.className = "noteText";
  status.textContent = "";

  actions.appendChild(saveBtn);
  actions.appendChild(iconBtn);
  actions.appendChild(status);

  card.appendChild(preview);
  card.appendChild(form);
  card.appendChild(actions);

  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    status.textContent = "A guardar...";
    try {
      const payload = { button_id: button.button_id, label: labelInput.value };
      const res = await postJson("/api/buttons/config", payload);
      previewLabel.textContent = res.label;
      status.textContent = "Nome guardado.";
    } catch (err) {
      alert(err.message || "Erro ao guardar nome.");
      status.textContent = "";
    } finally {
      saveBtn.disabled = false;
    }
  });

  iconBtn.addEventListener("click", async () => {
    if (!iconInput.files || !iconInput.files[0]) {
      alert("Seleciona um ficheiro primeiro.");
      return;
    }
    iconBtn.disabled = true;
    status.textContent = "A enviar...";
    try {
      await uploadIcon(button.button_id, iconInput.files[0]);
      previewIcon.src = `/api/buttons/icon/${button.button_id}?v=${Date.now()}`;
      status.textContent = "Ícone enviado.";
    } catch (err) {
      alert(err.message || "Erro ao enviar ícone.");
      status.textContent = "";
    } finally {
      iconBtn.disabled = false;
    }
  });

  return card;
}

(async function init() {
  const grid = document.getElementById("configGrid");
  if (!grid) return;

  try {
    const data = await fetchJson("/api/buttons/config");
    const buttons = data.buttons || [];
    buttons.forEach((btn) => grid.appendChild(createCard(btn)));
  } catch (err) {
    alert(err.message || "Erro ao carregar configurações.");
  }
})();
