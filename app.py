import os
from datetime import datetime, timezone, timedelta
from functools import wraps
from io import BytesIO

import psycopg2
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from openpyxl import Workbook

try:
    from replit.object_storage import Client as ObjectStorageClient
except Exception:  # pragma: no cover - optional dependency in non-Replit envs
    ObjectStorageClient = None

app = Flask(__name__)

# Session cookie signing
app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(32)

ALLOWED_BUTTON_IDS = {1, 2, 3, 4}
OBJECT_STORAGE_BUCKET = "BtnIcons"
MAX_ICON_BYTES = 2 * 1024 * 1024

ISO_DATE_REGEX = "^[0-9]{4}-[0-9]{2}-[0-9]{2}"
ISO_TIME_REGEX = "^[0-9]{2}:[0-9]{2}"

DATE_MATCH_SQL = f"""
(
    (date_iso IS NOT NULL AND date_iso = %s)
    OR (
        date IS NOT NULL
        AND (date::text) ~ '{ISO_DATE_REGEX}'
        AND (date::date) = %s
    )
    OR (
        timestamp IS NOT NULL
        AND (timestamp::text) ~ '{ISO_DATE_REGEX}'
        AND left(timestamp::text, 10) = %s
    )
)
"""

NORMALIZED_DATE_SQL = f"""
    COALESCE(
        NULLIF(date_iso, ''),
        CASE
            WHEN date IS NOT NULL AND (date::text) ~ '{ISO_DATE_REGEX}'
                THEN to_char(date::date, 'YYYY-MM-DD')
            ELSE NULL
        END,
        CASE
            WHEN timestamp IS NOT NULL AND (timestamp::text) ~ '{ISO_DATE_REGEX}'
                THEN left(timestamp::text, 10)
            ELSE NULL
        END
    )
"""

NORMALIZED_HOUR_SQL = f"""
    COALESCE(
        CASE
            WHEN time IS NOT NULL AND (time::text) ~ '{ISO_TIME_REGEX}'
                THEN NULLIF(split_part(time::text, ':', 1), '')::int
            ELSE NULL
        END,
        CASE
            WHEN timestamp IS NOT NULL AND (timestamp::text) ~ '{ISO_DATE_REGEX}'
                THEN NULLIF(substring(timestamp::text FROM '^[0-9]{4}-[0-9]{2}-[0-9]{2}.([0-9]{2})'), '')::int
            ELSE NULL
        END
    )
"""


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
    create_click_sql = """
    CREATE TABLE IF NOT EXISTS click (
      id SERIAL PRIMARY KEY,
      button_id INTEGER,
      button TEXT,
      seq INTEGER,
      date TEXT,
      date_iso TEXT,
      time TIME,
      timestamp TIMESTAMPTZ
    );
    """

    create_passwords_sql = """
    CREATE TABLE IF NOT EXISTS passwords (
      id SERIAL PRIMARY KEY,
      pin_hash TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """

    create_button_config_sql = """
    CREATE TABLE IF NOT EXISTS button_config (
      button_id INTEGER PRIMARY KEY,
      label TEXT NOT NULL,
      icon_key TEXT,
      icon_mime TEXT,
      icon_updated_at TIMESTAMPTZ
    );
    """

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(create_click_sql)
            cur.execute(create_passwords_sql)
            cur.execute(create_button_config_sql)
            _migrate_click_schema(cur)
            _migrate_button_config(cur)
        conn.commit()

    _ensure_pin_seeded()
    _ensure_button_config_seeded()


def _migrate_click_schema(cur):
    """Best-effort migration to support older schemas.

    If a previous version created table `click` without some columns (ex: missing
    button_id), we add them. We intentionally avoid NOT NULL constraints here to
    keep older rows valid.
    """

    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS button_id INTEGER;")
    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS button TEXT;")
    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS seq INTEGER;")
    cur.execute("ALTER TABLE click ALTER COLUMN date TYPE TEXT;")
    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS date_iso TEXT;")
    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS time TIME;")
    cur.execute("ALTER TABLE click ADD COLUMN IF NOT EXISTS timestamp TIMESTAMPTZ;")

    # Backfill button_id from button text when possible (e.g. "Botão 1").
    cur.execute(
        """
        UPDATE click
        SET button_id = (regexp_match(button, '(\\d+)'))[1]::int
        WHERE button_id IS NULL
          AND button IS NOT NULL
          AND regexp_match(button, '(\\d+)') IS NOT NULL;
        """
    )


def _migrate_button_config(cur):
    cur.execute("ALTER TABLE button_config ADD COLUMN IF NOT EXISTS icon_key TEXT;")
    cur.execute("ALTER TABLE button_config ADD COLUMN IF NOT EXISTS icon_mime TEXT;")
    cur.execute("ALTER TABLE button_config ADD COLUMN IF NOT EXISTS icon_updated_at TIMESTAMPTZ;")


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


def _ensure_button_config_seeded():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            for bid in sorted(ALLOWED_BUTTON_IDS):
                cur.execute("SELECT 1 FROM button_config WHERE button_id = %s;", (bid,))
                if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO button_config (button_id, label) VALUES (%s, %s);",
                        (bid, f"Botão {bid}"),
                    )
        conn.commit()


def _get_button_config_map():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT button_id, label, icon_key, icon_mime, icon_updated_at
                FROM button_config
                ORDER BY button_id;
                """
            )
            rows = cur.fetchall()
    config = {}
    for (bid, label, icon_key, icon_mime, icon_updated_at) in rows:
        config[int(bid)] = {
            "label": label,
            "icon_key": icon_key,
            "icon_mime": icon_mime,
            "icon_updated_at": icon_updated_at,
        }
    return config


def _get_button_label(button_id):
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT label FROM button_config WHERE button_id = %s;", (button_id,))
            row = cur.fetchone()
            return row[0] if row else f"Botão {button_id}"


def _get_object_storage_client():
    if ObjectStorageClient is None:
        raise RuntimeError("Replit Object Storage client não está disponível.")
    return ObjectStorageClient()


def _build_icon_key(button_id, ext):
    safe_ext = ext.lstrip(".")
    return f"{OBJECT_STORAGE_BUCKET}/button-{button_id}.{safe_ext}"


def _delete_object_storage_key(client, key):
    """Best-effort delete for different object storage client APIs."""
    for method_name in ("delete", "delete_object", "delete_key", "remove"):
        method = getattr(client, method_name, None)
        if callable(method):
            return method(key)
    raise RuntimeError("Object Storage client não suporta delete().")


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


@app.get("/admin/buttons")
@require_auth
def admin_buttons_config():
    return render_template("button-config.html")


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
                    "error": "PIN ainda não configurado.",
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
    date_iso = today.isoformat()
    click_time_str = now.strftime("%H:%M:%S")
    timestamp_str = now.isoformat(timespec="seconds")
    button_label = _get_button_label(button_id)

    with get_db_conn() as conn:
        # Ensure seq is consistent under concurrent clicks.
        # Exclusive lock serializes increments for the day.
        with conn.cursor() as cur:
            cur.execute("LOCK TABLE click IN EXCLUSIVE MODE;")
            cur.execute(
                f"SELECT COUNT(*) FROM click WHERE button_id = %s AND {DATE_MATCH_SQL};",
                (button_id, date_iso, today, date_iso),
            )
            count_today = int(cur.fetchone()[0])
            seq = count_today + 1

            date_display = today.strftime("%d/%m/%Y")

            cur.execute(
                """
                INSERT INTO click (button_id, button, seq, date, date_iso, time, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    button_id,
                    button_label,
                    seq,
                    date_display,
                    date_iso,
                    click_time_str,
                    timestamp_str,
                ),
            )

        conn.commit()

    return jsonify(
        {
            "button_id": button_id,
            "seq": seq,
            "date": date_display,
            "time": click_time_str[:5],
            "button": button_label,
            "date_iso": date_iso,
            "timestamp": timestamp_str,
        }
    )


@app.get("/api/buttons/config")
@require_auth
def api_buttons_config():
    config = _get_button_config_map()
    result = []
    for bid in sorted(ALLOWED_BUTTON_IDS):
        entry = config.get(bid, {"label": f"Botão {bid}", "icon_key": None})
        icon_updated_at = entry.get("icon_updated_at")
        result.append(
            {
                "button_id": bid,
                "label": entry.get("label", f"Botão {bid}"),
                "has_icon": bool(entry.get("icon_key")),
                "icon_url": f"/api/buttons/icon/{bid}" if entry.get("icon_key") else None,
                "icon_updated_at": icon_updated_at.isoformat() if icon_updated_at else None,
            }
        )
    return jsonify({"buttons": result})


@app.post("/api/buttons/config")
@require_auth
def api_buttons_config_update():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    button_id = payload.get("button_id")
    label = payload.get("label")

    try:
        button_id = int(button_id)
    except Exception:
        return jsonify({"error": "button_id inválido."}), 400

    if button_id not in ALLOWED_BUTTON_IDS:
        return jsonify({"error": "button_id inválido."}), 400

    if not isinstance(label, str) or not label.strip():
        return jsonify({"error": "Label inválido."}), 400

    label = label.strip()[:80]

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE button_config SET label = %s WHERE button_id = %s;",
                (label, button_id),
            )
        conn.commit()

    return jsonify({"ok": True, "button_id": button_id, "label": label})


@app.post("/api/buttons/icon/<int:button_id>")
@require_auth
def api_buttons_icon_upload(button_id):
    if button_id not in ALLOWED_BUTTON_IDS:
        return jsonify({"error": "button_id inválido."}), 400

    if request.content_length and request.content_length > MAX_ICON_BYTES:
        return jsonify({"error": "Ficheiro demasiado grande (máx 2MB)."}), 400

    icon = request.files.get("icon")
    if not icon:
        return jsonify({"error": "Ficheiro 'icon' em falta."}), 400

    mime = icon.mimetype or "application/octet-stream"
    allowed = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "image/svg+xml": "svg",
    }
    if mime not in allowed:
        return jsonify({"error": "Formato inválido. Usa PNG, JPG, WEBP ou SVG."}), 400

    ext = allowed[mime]
    data = icon.read()
    if len(data) > MAX_ICON_BYTES:
        return jsonify({"error": "Ficheiro demasiado grande (máx 2MB)."}), 400

    try:
        client = _get_object_storage_client()
        key = _build_icon_key(button_id, ext)
        client.upload_from_bytes(key, data)
    except Exception as e:
        return jsonify({"error": f"Falha ao guardar no Object Storage: {e}"}), 500

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE button_config
                SET icon_key = %s, icon_mime = %s, icon_updated_at = now()
                WHERE button_id = %s;
                """,
                (key, mime, button_id),
            )
        conn.commit()

    return jsonify({"ok": True, "button_id": button_id})


@app.get("/api/buttons/icon/<int:button_id>")
@require_auth
def api_buttons_icon_get(button_id):
    if button_id not in ALLOWED_BUTTON_IDS:
        return jsonify({"error": "button_id inválido."}), 400

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT icon_key, icon_mime FROM button_config WHERE button_id = %s;",
                (button_id,),
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return ("", 404)
            icon_key, icon_mime = row

    try:
        client = _get_object_storage_client()
        data = client.download_as_bytes(icon_key)
    except Exception as e:
        return jsonify({"error": f"Falha ao ler do Object Storage: {e}"}), 500

    return send_file(BytesIO(data), mimetype=icon_mime or "application/octet-stream")


@app.post("/api/buttons/icon/<int:button_id>/delete")
@require_auth
def api_buttons_icon_delete(button_id):
    if button_id not in ALLOWED_BUTTON_IDS:
        return jsonify({"error": "button_id inválido."}), 400

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT icon_key FROM button_config WHERE button_id = %s;",
                (button_id,),
            )
            row = cur.fetchone()
            icon_key = row[0] if row else None

    warning = None
    if icon_key:
        try:
            client = _get_object_storage_client()
            _delete_object_storage_key(client, icon_key)
        except Exception as e:
            # Ainda assim limpamos a configuração para o UI deixar de mostrar o ícone.
            warning = str(e)

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE button_config
                SET icon_key = NULL, icon_mime = NULL, icon_updated_at = NULL
                WHERE button_id = %s;
                """,
                (button_id,),
            )
        conn.commit()

    payload = {"ok": True, "button_id": button_id}
    if warning:
        payload["warning"] = warning
    return jsonify(payload)


@app.get("/api/admin/stats")
@require_auth
def api_admin_stats():
    today = datetime.now(timezone.utc).astimezone().date()
    lookback_start = today - timedelta(days=13)

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM click;")
            total = int(cur.fetchone()[0])

            cur.execute(
                f"SELECT COUNT(*) FROM click WHERE {DATE_MATCH_SQL};",
                (today.isoformat(), today, today.isoformat()),
            )
            total_today = int(cur.fetchone()[0])

            cur.execute(
                "SELECT button_id, COUNT(*) FROM click GROUP BY button_id ORDER BY button_id;"
            )
            per_button_rows = cur.fetchall()
            per_button = {int(b): int(c) for (b, c) in per_button_rows}

            cur.execute(
                f"""
                WITH normalized AS (
                    SELECT {NORMALIZED_DATE_SQL} AS day_iso
                    FROM click
                )
                SELECT day_iso::date AS day, COUNT(*)
                FROM normalized
                WHERE day_iso IS NOT NULL
                  AND day_iso::date >= %s
                GROUP BY day
                ORDER BY day;
                """,
                (lookback_start,),
            )
            per_day_rows = cur.fetchall()
            per_day = [{"date": d.isoformat(), "count": int(c)} for (d, c) in per_day_rows]

            cur.execute(
                f"""
                WITH normalized AS (
                    SELECT
                        {NORMALIZED_DATE_SQL} AS day_iso,
                        {NORMALIZED_HOUR_SQL} AS hour_val
                    FROM click
                )
                SELECT hour_val, COUNT(*)
                FROM normalized
                WHERE day_iso IS NOT NULL
                  AND day_iso::date = %s
                  AND hour_val IS NOT NULL
                GROUP BY hour_val
                ORDER BY hour_val;
                """,
                (today,),
            )
            per_hour_rows = cur.fetchall()
            per_hour = [{"hour": int(h), "count": int(c)} for (h, c) in per_hour_rows]

    # Ensure keys exist for 1..4
    for bid in sorted(ALLOWED_BUTTON_IDS):
        per_button.setdefault(bid, 0)

    button_config = _get_button_config_map()
    button_labels = {
        bid: (button_config.get(bid, {}).get("label") or f"Botão {bid}")
        for bid in sorted(ALLOWED_BUTTON_IDS)
    }

    return jsonify(
        {
            "total": total,
            "today": total_today,
            "perButton": per_button,
            "perDay": per_day,
            "perHourToday": per_hour,
            "buttonLabels": button_labels,
        }
    )


@app.get("/admin/export.xlsx")
@require_auth
def admin_export_xlsx():
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  id,
                  COALESCE(button_id, NULL) AS button_id,
                  COALESCE(button, '') AS button,
                  COALESCE(seq, NULL) AS seq,
                  date::text AS date,
                  COALESCE(date_iso, '') AS date_iso,
                  time::text AS time,
                  timestamp::text AS timestamp
                FROM click
                ORDER BY id DESC;
                """
            )
            rows = cur.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "click"

    ws.append(["id", "button_id", "button", "seq", "date", "date_iso", "time", "timestamp"])
    for (cid, button_id, button_val, seq, date_val, date_iso, time_val, ts_val) in rows:
        ws.append(
            [
                int(cid) if cid is not None else "",
                int(button_id) if button_id is not None else "",
                str(button_val) if button_val is not None else "",
                int(seq) if seq is not None else "",
                str(date_val) if date_val is not None else "",
                str(date_iso) if date_iso is not None else "",
                str(time_val) if time_val is not None else "",
                str(ts_val) if ts_val is not None else "",
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
