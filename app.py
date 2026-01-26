import os
from datetime import datetime, timezone
from functools import wraps
from io import BytesIO

import psycopg2
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from openpyxl import Workbook

app = Flask(__name__)

# Session cookie signing
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

ALLOWED_BUTTON_IDS = {1, 2, 3, 4}


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
    create_clicks_sql = """
    CREATE TABLE IF NOT EXISTS clicks (
      id SERIAL PRIMARY KEY,
      button_id INTEGER NOT NULL,
      seq INTEGER NOT NULL,
      date DATE NOT NULL,
      time TIME NOT NULL
    );
    """

    create_passwords_sql = """
    CREATE TABLE IF NOT EXISTS passwords (
      id SERIAL PRIMARY KEY,
      pin_hash TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(create_clicks_sql)
            cur.execute(create_passwords_sql)
        conn.commit()

    _ensure_pin_seeded()


def _ensure_pin_seeded():
    """Seed initial PIN from env ADMIN_PIN if passwords table is empty."""
    admin_pin = os.getenv("ADMIN_PIN")
    if not admin_pin:
        return

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM passwords;")
            count = int(cur.fetchone()[0])
            if count == 0:
                cur.execute(
                    "INSERT INTO passwords (pin_hash) VALUES (%s);",
                    (generate_password_hash(admin_pin),),
                )
        conn.commit()


def _get_current_pin_hash():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pin_hash FROM passwords ORDER BY id DESC LIMIT 1;")
            row = cur.fetchone()
            return row[0] if row else None


def require_auth(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("gate"))
        return view_fn(*args, **kwargs)

    return wrapper


@app.get("/")
def gate():
    if session.get("authed"):
        return redirect(url_for("admin_dashboard"))
    return render_template("gate.html")


@app.get("/buttons")
@require_auth
def buttons_page():
    return render_template("buttons.html")


@app.get("/admin")
@require_auth
def admin_dashboard():
    return render_template("admin.html")


@app.post("/api/auth/pin")
def api_auth_pin():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    pin = payload.get("pin")
    if not isinstance(pin, str) or not pin.strip():
        return jsonify({"error": "PIN inválido."}), 400

    pin_hash = _get_current_pin_hash()
    if not pin_hash:
        return (
            jsonify(
                {
                    "error": "PIN ainda não configurado. Define o Secret ADMIN_PIN e reinicia o Repl.",
                }
            ),
            503,
        )

    if not check_password_hash(pin_hash, pin):
        return jsonify({"error": "PIN incorreto."}), 401

    session["authed"] = True
    return jsonify({"ok": True})


@app.post("/api/auth/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.post("/api/click")
@require_auth
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

    if button_id not in ALLOWED_BUTTON_IDS:
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


@app.get("/api/admin/stats")
@require_auth
def api_admin_stats():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clicks;")
            total = int(cur.fetchone()[0])

            cur.execute("SELECT COUNT(*) FROM clicks WHERE date = CURRENT_DATE;")
            total_today = int(cur.fetchone()[0])

            cur.execute(
                "SELECT button_id, COUNT(*) FROM clicks GROUP BY button_id ORDER BY button_id;"
            )
            per_button_rows = cur.fetchall()
            per_button = {int(b): int(c) for (b, c) in per_button_rows}

            cur.execute(
                """
                SELECT date, COUNT(*)
                FROM clicks
                WHERE date >= CURRENT_DATE - INTERVAL '13 days'
                GROUP BY date
                ORDER BY date;
                """
            )
            per_day_rows = cur.fetchall()
            per_day = [{"date": d.isoformat(), "count": int(c)} for (d, c) in per_day_rows]

            cur.execute(
                """
                SELECT EXTRACT(HOUR FROM time)::int AS hour, COUNT(*)
                FROM clicks
                WHERE date = CURRENT_DATE
                GROUP BY hour
                ORDER BY hour;
                """
            )
            per_hour_rows = cur.fetchall()
            per_hour = [{"hour": int(h), "count": int(c)} for (h, c) in per_hour_rows]

    # Ensure keys exist for 1..4
    for bid in sorted(ALLOWED_BUTTON_IDS):
        per_button.setdefault(bid, 0)

    return jsonify(
        {
            "total": total,
            "today": total_today,
            "perButton": per_button,
            "perDay": per_day,
            "perHourToday": per_hour,
        }
    )


@app.get("/admin/export.xlsx")
@require_auth
def admin_export_xlsx():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, button_id, seq, date, time
                FROM clicks
                ORDER BY date DESC, time DESC, id DESC;
                """
            )
            rows = cur.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "clicks"

    ws.append(["id", "button_id", "seq", "date", "time"])
    for (cid, button_id, seq, date_val, time_val) in rows:
        ws.append(
            [
                int(cid),
                int(button_id),
                int(seq),
                date_val.isoformat(),
                time_val.strftime("%H:%M:%S"),
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"clicks_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Initialize DB when the app starts
try:
    init_db()
except Exception as e:
    # On some platforms, DATABASE_URL may not exist during import time.
    # The API will still fail loudly on first request if DB isn't configured.
    app.logger.warning("DB init skipped/failed: %s", e)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
