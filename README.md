# ClickCounter

Aplicação web com 4 botões em ecrã inteiro que regista cliques numa base de dados PostgreSQL (Replit Development Database). Inclui autenticação por PIN, dashboard de administração com gráficos e exportação para Excel.

Site publicado:
https://click-counter--miguelpedrosa21.replit.app/

## Funcionalidades
- Página de botões em ecrã inteiro (2×2) para uso em touchscreen.
- Registo de cada clique em PostgreSQL, com data/hora e metadados.
- Sequência diária por botão: cada botão tem a sua própria numeração ($1,2,3,\dots$) e faz reset automaticamente no início de cada dia.
- Acesso protegido por PIN:
  - Ao abrir o site aparece o ecrã de login.
  - O PIN é validado no backend e a sessão fica ativa até logout.
  - Existe uma dica de desenvolvimento visível na própria página de login (botão flutuante). O PIN de desenvolvimento aparece aí.
- Dashboard Admin:
  - Totais globais e totais do dia.
  - Gráficos (por botão, últimos 14 dias, por hora no dia atual).
  - Botão Help com popup de ajuda.
  - Configurar botões: alterar nomes e carregar ícones (ícone + label no ecrã de botões).
  - Exportação para Excel (`.xlsx`) com os dados da tabela.

## Tecnologias
- Backend: Python + Flask
- Base de dados: PostgreSQL (via `DATABASE_URL`), com `psycopg2-binary` (sem SQLAlchemy)
- Frontend: HTML/CSS/JavaScript
- Gráficos: Chart.js (via CDN)
- Excel: openpyxl

## Estrutura do projeto
- [app.py](app.py) — servidor Flask, autenticação, API, acesso PostgreSQL e export Excel
- [templates/gate.html](templates/gate.html) — ecrã de PIN (login)
- [templates/admin.html](templates/admin.html) — dashboard de administração
- [templates/button-config.html](templates/button-config.html) — configurar botões (nomes + ícones)
- [templates/buttons.html](templates/buttons.html) — página dos botões (ecrã inteiro)
- [static/styles.css](static/styles.css) — estilos (botões, PIN, toasts)
- [static/gate.js](static/gate.js) — login por PIN + dica de desenvolvimento
- [static/app.js](static/app.js) — envio de cliques para o backend
- [static/admin.js](static/admin.js) / [static/admin.css](static/admin.css) — dashboard (charts + help + logout)
- [static/button-config.js](static/button-config.js) — UI de configuração de botões

## Modelo de dados (PostgreSQL)
Tabela principal: `click`

Campos usados:
- `id` (serial)
- `button_id` (int) — identificador do botão (1..4)
- `button` (text) — etiqueta humana (ex.: "Botão 1")
- `seq` (int) — sequência diária por botão
- `date`, `date_iso`, `time`, `timestamp` — valores de data/hora (o backend é compatível com dados de versões antigas)

Tabela de autenticação:
- `passwords` — guarda o hash do PIN (seed inicial via `ADMIN_PIN`)

Tabela de configuração dos botões:
- `button_config` — guarda nomes e metadados do ícone (label, icon_key, icon_mime, icon_updated_at)
  - Os ficheiros de ícone são guardados no Replit Object Storage (bucket `BtnIcons`).

## Endpoints
Páginas:
- `GET /` — login (PIN)
- `GET /admin` — dashboard (requer sessão)
- `GET /admin/buttons` — configurar botões (requer sessão)
- `GET /buttons` — página dos botões (requer sessão)

API:
- `POST /api/auth/pin` — autentica (`{"pin": "...."}`)
- `POST /api/auth/logout` — termina sessão
- `POST /api/click` — regista clique (`{"button_id": 1}`) e devolve `{button_id, seq, date, time, ...}`
- `GET /api/admin/stats` — estatísticas para os gráficos
- `GET /api/buttons/config` — lista nomes/ícones dos botões
- `POST /api/buttons/config` — atualiza o nome de um botão
- `POST /api/buttons/icon/<id>` — upload de ícone para o botão
- `GET /api/buttons/icon/<id>` — obtém o ícone do botão

Export:
- `GET /admin/export.xlsx` — descarrega `.xlsx`

## Como correr no Replit
1. Importa o repositório no Replit (Import from GitHub).
2. Garante que o Replit instala as dependências a partir de [requirements.txt](requirements.txt).
3. Define os Secrets (Environment Variables):
	- `DATABASE_URL` — ligação PostgreSQL (Replit Development Database)
	- `ADMIN_PIN` — PIN inicial (é guardado como hash na tabela `passwords`)
	- `FLASK_SECRET_KEY` — recomendado para sessão estável (string longa e aleatória)
	- `REPLIT_DB_URL` não é usado (Object Storage usa credenciais do ambiente)
	- opcional: `PGSSLMODE` — por omissão é usado `require`
4. Faz Run.

Nota: se vires dados no site mas não na aba “Development Database”, confirma que o `DATABASE_URL` corresponde exatamente à base de dados que estás a visualizar.

## Como correr localmente (na tua máquina)
Pré-requisitos:
- Python 3.10+ (recomendado)
- Acesso a um PostgreSQL (local ou remoto)

Passos:
1. Clonar o repositório:
	- `git clone <URL_DO_REPO>`
	- `cd ClickCounter`
2. Criar e ativar ambiente virtual:
	- Windows (PowerShell): `python -m venv .venv` e depois `./.venv/Scripts/Activate.ps1`
3. Instalar dependências:
	- `pip install -r requirements.txt`
4. Definir variáveis de ambiente:
	- `DATABASE_URL` (ex.: `postgresql://user:pass@host:5432/dbname`)
	- `ADMIN_PIN`
	- `FLASK_SECRET_KEY`
	- opcional: `PGSSLMODE=require`
5. Arrancar:
	- `python app.py`
6. Abrir no browser:
	- `http://localhost:5000/`

## Notas de segurança
- Não guardes o PIN em texto simples: o sistema guarda apenas hash.
- Em produção, muda o PIN e remove a exposição do PIN de desenvolvimento (a dica existe para facilitar desenvolvimento/testes).
