function setButtonsDisabled(disabled) {
	document.querySelectorAll("button[data-button-id]").forEach((btn) => {
		btn.disabled = disabled;
	});
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

async function handleClick(buttonId) {
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

		showToast(`#${data.seq} · Botão ${data.button_id} · ${data.date} ${data.time}`);
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

			try {
				await handleClick(buttonId);
			} catch (err) {
				alert(err.message || "Erro ao registar clique.");
			}
		});
	});
}

wireUi();
