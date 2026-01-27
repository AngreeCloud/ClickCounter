function setButtonsDisabled(disabled) {
	document.querySelectorAll("button[data-button-id]").forEach((btn) => {
		btn.disabled = disabled;
	});
}

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

function showToast(message) {
	const box = document.getElementById("notifications");
	if (!box) return;

	const el = document.createElement("div");
	el.className = "toast";
	el.textContent = message;
	box.appendChild(el);

	setTimeout(() => {
		el.classList.add("fade-out");
		setTimeout(() => el.remove(), 400);
	}, 1500);
}

async function handleClick(buttonId, buttonLabel) {
	setButtonsDisabled(true);
	try {
		const res = await fetch("/api/click", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ button_id: buttonId }),
		});
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			throw new Error(data && data.error ? data.error : "Erro ao registar.");
		}

		const label = data.button || buttonLabel || `Botão ${data.button_id}`;
		showToast(`#${data.seq} · ${label} · ${data.date} ${data.time}`);
	} finally {
		setButtonsDisabled(false);
	}
}

function renderButtons(buttons) {
	const grid = document.getElementById("buttonGrid");
	if (!grid) return;
	grid.innerHTML = "";

	buttons.forEach((btn) => {
		const buttonEl = document.createElement("button");
		buttonEl.className = `btn btn${btn.button_id}`;
		buttonEl.type = "button";
		buttonEl.setAttribute("data-button-id", String(btn.button_id));

		const content = document.createElement("div");
		content.className = "btnContent";

		const icon = document.createElement("img");
		icon.className = "btnIcon";
		icon.alt = "";
		if (btn.icon_url) {
			icon.src = `${btn.icon_url}?v=${btn.icon_updated_at || Date.now()}`;
		} else {
			icon.src = "";
			icon.style.display = "none";
		}

		const label = document.createElement("div");
		label.className = "btnLabel";
		label.textContent = btn.label || `Botão ${btn.button_id}`;

		content.appendChild(icon);
		content.appendChild(label);
		buttonEl.appendChild(content);

		buttonEl.addEventListener("click", async () => {
			const buttonId = Number(btn.button_id);
			if (!Number.isInteger(buttonId) || buttonId < 1) return;

			try {
				await handleClick(buttonId, btn.label);
			} catch (err) {
				alert(err.message || "Erro ao registar clique.");
			}
		});

		grid.appendChild(buttonEl);
	});
}

async function wireUi() {
	try {
		const data = await fetchJson("/api/buttons/config");
		renderButtons(data.buttons || []);
	} catch (err) {
		alert(err.message || "Erro ao carregar botões.");
	}
}

wireUi();
