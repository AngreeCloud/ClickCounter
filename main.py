import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://') if os.environ.get('DATABASE_URL') else 'sqlite:///clicks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db_sql = SQLAlchemy(app)

class Click(db_sql.Model):
    id = db_sql.Column(db_sql.Integer, primary_key=True)
    button = db_sql.Column(db_sql.String(50), nullable=False)
    seq = db_sql.Column(db_sql.Integer, nullable=False)
    date = db_sql.Column(db_sql.String(20), nullable=False)
    date_iso = db_sql.Column(db_sql.String(20), nullable=False)
    time = db_sql.Column(db_sql.String(10), nullable=False)
    timestamp = db_sql.Column(db_sql.DateTime, nullable=False)

with app.app_context():
    db_sql.create_all()

ALLOWED_BUTTONS = {"Botão 1", "Botão 2", "Botão 3", "Botão 4"}

META_LAST_DATE_KEY = "meta:last_date"
META_COUNTER_KEY = "meta:counter"


def _db_get(key: str, default=None):
    try:
        val = db[key]
        if isinstance(val, (dict, list)):
            import json
            # A quick way to convert Replit DB Observed types to plain types
            # or just recursive conversion
            def _to_plain(obj):
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
                if isinstance(obj, dict):
                    return {k: _to_plain(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_to_plain(x) for x in obj]
                return obj
            return _to_plain(val)
        return val
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
        # Reset counter for all buttons each day
        for btn in ALLOWED_BUTTONS:
            db[f"meta:counter:{btn}"] = 0


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def api_status():
    _, today_iso, today_display, _ = _now_parts()
    _ensure_today_counter(today_iso)

    # Total daily clicks (sum of all buttons)
    total_today = sum(int(_db_get(f"meta:counter:{btn}", 0) or 0) for btn in ALLOWED_BUTTONS)
    
    day_key = f"clicks:{today_iso}"
    clicks_today = _db_get(day_key, []) or []

    last_click = clicks_today[-1] if clicks_today else None
    
    # Total clicks in PostgreSQL
    total_sql = Click.query.count()

    return jsonify(
        {
            "date": today_display,
            "dateIso": today_iso,
            "counter": total_today,
            "clicksToday": len(clicks_today),
            "lastClick": last_click,
            "totalClicksSql": total_sql
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

    # Sequence unique per button
    button_counter_key = f"meta:counter:{button}"
    counter = int(_db_get(button_counter_key, 0) or 0) + 1
    db[button_counter_key] = counter

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

    # Record in PostgreSQL
    new_click = Click(
        button=button,
        seq=counter,
        date=today_display,
        date_iso=today_iso,
        time=time_hm,
        timestamp=now
    )
    db_sql.session.add(new_click)
    db_sql.session.commit()

    return jsonify(record)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
