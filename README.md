# ClickCounter (Flask + PostgreSQL no Replit)

Site com 4 botões (full-screen). Cada clique:
- incrementa um contador sequencial diário (reinicia automaticamente a cada dia)
- mostra uma notificação do browser com o número sequencial, a data e a hora (HH:MM)
- fica registado na base de dados PostgreSQL (Replit Development Database) via `DATABASE_URL`

O acesso é protegido por PIN: ao abrir o site aparece um modal; após autenticação vai para a dashboard.

## Estrutura
- `app.py` — backend Flask + PostgreSQL + autenticação + export Excel
- `templates/gate.html` — modal de PIN
- `templates/admin.html` — dashboard (gráficos + export)
- `templates/buttons.html` — página full-screen dos botões
- `static/styles.css` — estilos dos botões + modal
- `static/app.js` — lógica dos botões (envio + notificações)
- `static/admin.js` / `static/admin.css` — dashboard

## Endpoints
- `GET /` — página de PIN (gate)
- `POST /api/auth/pin` — autenticação (`{"pin":"1234"}`)
- `GET /admin` — dashboard
- `GET /buttons` — botões full-screen
- `POST /api/click` — regista clique (`{"button_id":1}`) e devolve `{button_id, seq, date, time}`
- `GET /api/admin/stats` — estatísticas agregadas (para gráficos)
- `GET /admin/export.xlsx` — download Excel com os dados da tabela `clicks`

## Como correr no Replit (recomendado)
1. Cria um repositório no GitHub e faz push deste projeto.
2. No Replit: **Create Repl → Import from GitHub** e cola o URL do teu repo.
3. Confirma que existe `requirements.txt` (o Replit instala as dependências automaticamente).
4. Define os Secrets:
	- `DATABASE_URL` (PostgreSQL do Replit Development Database)
	- `ADMIN_PIN` (PIN inicial; o sistema guarda hash na tabela `passwords`)
	- opcional: `FLASK_SECRET_KEY` (para manter sessão estável entre restarts)
5. Run (o Replit executa `app.py`).

Opcional (para garantir “mudança de dia” no fuso horário certo):
- Define um Secret/Env `TIMEZONE` com um valor IANA, por exemplo `Europe/Lisbon`.

## Nota sobre persistência
Os cliques ficam persistidos na tabela `clicks` (PostgreSQL). O `seq` diário é calculado por contagem dos cliques na data atual.

## Publicar link público
No Replit, abre a aba **Webview** e usa o URL público do projeto (Share/Publish) para entregar.
