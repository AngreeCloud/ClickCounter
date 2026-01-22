import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

try:
    from replit import db as replit_db
except Exception:
    replit_db = None  # type: ignore


if os.getenv("REPLIT_DB_URL") and replit_db is not None:
    db = replit_db
else:
    # Local/dev fallback (não persistente). No Replit será usada a Replit DB.
    db = {}

app = Flask(__name__)

ALLOWED_BUTTONS = {"Botão 1", "Botão 2", "Botão 3", "Botão 4"}

META_LAST_DATE_KEY = "meta:last_date"
META_COUNTER_KEY = "meta:counter"


def _db_get(key: str, default=None):
    try:
        return db[key]
    except KeyError:
        return default


def _get_timezone():
    tz_name = os.getenv("TIMEZONE") or os.getenv("TZ") or "Europe/Lisbon"

    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass

    # Fallback: whatever the runtime considers local
    return datetime.now().astimezone().tzinfo


def _now_parts():
    tz = _get_timezone()
    now = datetime.now(tz)

    date_iso = now.strftime("%Y-%m-%d")
    date_display = now.strftime("%d/%m/%Y")
    time_hm = now.strftime("%H:%M")

    return now, date_iso, date_display, time_hm


def _ensure_today_counter(today_iso: str):
    last_date = _db_get(META_LAST_DATE_KEY)

    if last_date != today_iso:
        db[META_LAST_DATE_KEY] = today_iso
        db[META_COUNTER_KEY] = 0


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def api_status():
    _, today_iso, today_display, _ = _now_parts()
    _ensure_today_counter(today_iso)

    counter = int(_db_get(META_COUNTER_KEY, 0) or 0)
    day_key = f"clicks:{today_iso}"
    clicks_today = _db_get(day_key, []) or []

    last_click = clicks_today[-1] if clicks_today else None

    return jsonify(
        {
            "date": today_display,
            "dateIso": today_iso,
            "counter": counter,
            "clicksToday": len(clicks_today),
            "lastClick": last_click,
        }
    )


@app.get("/api/clicks/today")
def api_clicks_today():
    _, today_iso, _, _ = _now_parts()
    day_key = f"clicks:{today_iso}"
    clicks_today = _db_get(day_key, []) or []

    # Safety: don't send huge payloads if the DB grows a lot
    return jsonify({"dateIso": today_iso, "clicks": clicks_today[-200:]})


@app.post("/api/click")
def api_click():
    payload = request.get_json(silent=True) or {}
    button = payload.get("button")

    if button not in ALLOWED_BUTTONS:
        return jsonify({"error": "Botão inválido."}), 400

    now, today_iso, today_display, time_hm = _now_parts()
    _ensure_today_counter(today_iso)

    counter = int(_db_get(META_COUNTER_KEY, 0) or 0) + 1
    db[META_COUNTER_KEY] = counter

    record = {
        "button": button,
        "seq": counter,
        "date": today_display,
        "dateIso": today_iso,
        "time": time_hm,
        "timestamp": now.isoformat(timespec="seconds"),
    }

    day_key = f"clicks:{today_iso}"
    clicks_today = _db_get(day_key, []) or []
    clicks_today.append(record)
    db[day_key] = clicks_today

    return jsonify(record)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
