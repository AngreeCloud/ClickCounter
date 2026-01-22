# ClickCounter (Flask + Replit DB)

Site com 4 botões. Cada clique:
- incrementa um contador sequencial diário (reinicia automaticamente a cada dia)
- mostra ao utilizador o número sequencial, a data e a hora (HH:MM)
- fica registado na base de dados integrada do Replit (Replit DB)

## Estrutura
- `main.py` — backend Flask + endpoints
- `templates/index.html` — página principal
- `static/styles.css` — estilos responsivos
- `static/app.js` — lógica do front-end (fetch à API)

## Endpoints
- `GET /` — UI
- `GET /api/status` — data atual, contador atual, total de cliques de hoje, último clique
- `POST /api/click` — regista clique (`{"button":"Botão 1"}`)
- `GET /api/clicks/today` — lista (até 200) cliques de hoje

## Como correr no Replit (recomendado)
1. Cria um repositório no GitHub e faz push deste projeto.
2. No Replit: **Create Repl → Import from GitHub** e cola o URL do teu repo.
3. Confirma que existe `requirements.txt` (o Replit instala as dependências automaticamente).
4. Run (o Replit vai executar `main.py`).

Opcional (para garantir “mudança de dia” no fuso horário certo):
- Define um Secret/Env `TIMEZONE` com um valor IANA, por exemplo `Europe/Lisbon`.

## Nota sobre persistência
A Replit DB é persistente: os cliques e o contador mantêm-se mesmo que atualizes a página ou reinicies o Repl.

## Publicar link público
No Replit, abre a aba **Webview** e usa o URL público do projeto (Share/Publish) para entregar.
