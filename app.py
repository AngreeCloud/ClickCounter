import os
from datetime import datetime, timezone

import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_db_conn():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL environment variable")

    # Replit/Postgres providers often require TLS.
    # If the URL already sets sslmode, keep it; otherwise default to require.
    if "sslmode=" in database_url:
        return psycopg2.connect(database_url)

    return psycopg2.connect(database_url, sslmode=os.getenv("PGSSLMODE", "require"))


def init_db():
    create_sql = """
    CREATE TABLE IF NOT EXISTS clicks (
      id SERIAL PRIMARY KEY,
      button_id INTEGER NOT NULL,
      seq INTEGER NOT NULL,
      date DATE NOT NULL,
      time TIME NOT NULL
    );
    """

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
        conn.commit()


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/click")
def api_click():
    """Regista um clique e devolve {button_id, seq, date, time}.

    Input JSON:
      {"button_id": 1}
    """

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    button_id = payload.get("button_id")
    try:
        button_id = int(button_id)
    except Exception:
        return jsonify({"error": "button_id tem de ser um inteiro."}), 400

    if button_id < 1:
        return jsonify({"error": "button_id inválido."}), 400

    now = datetime.now(timezone.utc).astimezone()
    today = now.date()
    click_time = now.time().replace(second=0, microsecond=0)

    with get_db_conn() as conn:
        # Ensure seq is consistent under concurrent clicks.
        # Exclusive lock serializes increments for the day.
        with conn.cursor() as cur:
            cur.execute("LOCK TABLE clicks IN EXCLUSIVE MODE;")
            cur.execute("SELECT COUNT(*) FROM clicks WHERE date = CURRENT_DATE;")
            count_today = int(cur.fetchone()[0])
            seq = count_today + 1

            cur.execute(
                """
                INSERT INTO clicks (button_id, seq, date, time)
                VALUES (%s, %s, %s, %s)
                """,
                (button_id, seq, today, click_time),
            )

        conn.commit()

    return jsonify(
        {
            "button_id": button_id,
            "seq": seq,
            "date": today.isoformat(),
            "time": click_time.strftime("%H:%M"),
        }
    )


# Initialize DB when the app starts
try:
    init_db()
except Exception as e:
    # On some platforms, DATABASE_URL may not exist during import time.
    # The API will still fail loudly on first request if DB isn't configured.
    app.logger.warning("DB init skipped/failed: %s", e)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=True)
