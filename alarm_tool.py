"""
alarm_tool.py — Voice Agent Alarm Tool (WebSocket notification version)
"""

import threading
import time
import json
import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json

# ── DB connection ────────────────────────────────────────────
def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def _init_alarms_table():
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS alarms (
                        label TEXT PRIMARY KEY,
                        fire_at TIMESTAMP NOT NULL
                    )
                """)
            conn.commit()
    except Exception as e:
        print(f"⚠️ Alarm DB init error: {e}")

def _load_alarms() -> list:
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT label, fire_at FROM alarms")
                return [{"label": r[0], "fire_at": r[1].isoformat()} for r in cur.fetchall()]
    except:
        return []

def _save_alarm(label: str, fire_at: datetime):
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO alarms (label, fire_at) VALUES (%s, %s)
                    ON CONFLICT (label) DO UPDATE SET fire_at = EXCLUDED.fire_at
                """, (label, fire_at))
            conn.commit()
    except Exception as e:
        print(f"⚠️ Alarm save error: {e}")

def _delete_alarm(label: str):
    try:
        with _get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM alarms WHERE label = %s", (label,))
            conn.commit()
    except Exception as e:
        print(f"⚠️ Alarm delete error: {e}")

# ── WebSocket callback ───────────────────────────────────────
_ws_clients: set = set()

def register_ws(ws):
    _ws_clients.add(ws)

def unregister_ws(ws):
    _ws_clients.discard(ws)

# ── In-memory timer registry ─────────────────────────────────
_active_timers: dict[str, threading.Timer] = {}

# ── Alarm trigger ────────────────────────────────────────────
def _trigger_alarm(label: str):
    print(f"\n🔔 ALARM FIRED: {label}")
    import asyncio

    # Use a friendly display name (strip the unique suffix for TTS)
    display = label.split("_")[0] if "_" in label else label

    message = json.dumps({"type": "alarm", "label": display})

    async def _notify():
        dead = set()
        for ws in list(_ws_clients):
            try:
                await ws.send(message)
            except:
                dead.add(ws)
        _ws_clients.difference_update(dead)

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_notify())
        loop.close()
    except Exception as e:
        print(f"⚠️ Alarm notify error: {e}")

    _delete_alarm(label)
    _active_timers.pop(label, None)

# ── Public API ───────────────────────────────────────────────
def set_alarm(minutes: float = None, label: str = "Alarm",
              hour: int = None, minute: int = None) -> str:
    now = datetime.now()

    if minutes is not None:
        # Unique label using timestamp so multiple minute-based alarms don't clash
        unique_label = f"Alarm_{int(time.time())}"
        fire_at = now + timedelta(minutes=minutes)
        delay_sec = minutes * 60
        time_str = f"in {int(minutes)} minute{'s' if minutes != 1 else ''}"

    elif hour is not None and minute is not None:
        # Unique label using HH:MM so same time can't be double-set
        unique_label = f"Alarm_{hour:02d}{minute:02d}"
        fire_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if fire_at <= now:
            fire_at += timedelta(days=1)
        delay_sec = (fire_at - now).total_seconds()
        time_str = f"at {fire_at.strftime('%I:%M %p')}"

    else:
        return "Please specify either minutes from now or an exact hour and minute."

    # Cancel existing timer with same label if any
    if unique_label in _active_timers:
        _active_timers[unique_label].cancel()

    timer = threading.Timer(delay_sec, _trigger_alarm, args=[unique_label])
    timer.daemon = True
    timer.start()
    _active_timers[unique_label] = timer
    _save_alarm(unique_label, fire_at)

    return f"Alarm set {time_str}."

def cancel_alarm(label: str = "Alarm") -> str:
    # Try exact match first
    if label in _active_timers:
        _active_timers[label].cancel()
        _active_timers.pop(label)
        _delete_alarm(label)
        return f"Alarm cancelled."
    # Try prefix match (e.g. user says "cancel alarm" without exact label)
    matches = [k for k in _active_timers if k.startswith("Alarm_")]
    if matches:
        for k in matches:
            _active_timers[k].cancel()
            _delete_alarm(k)
        _active_timers.clear()
        return f"All alarms cancelled."
    return "No active alarms found."

def list_alarms() -> str:
    alarms = _load_alarms()
    if not alarms:
        return "You have no alarms set."
    parts = []
    for a in alarms:
        fire_at = datetime.fromisoformat(a["fire_at"])
        # Show friendly time only, not the internal label
        parts.append(fire_at.strftime('%I:%M %p'))
    return "Your alarms are set for: " + ", ".join(parts) + "."

def restore_alarms():
    _init_alarms_table()
    alarms = _load_alarms()
    now = datetime.now()
    restored = 0
    for a in alarms:
        fire_at = datetime.fromisoformat(a["fire_at"])
        delay_sec = (fire_at - now).total_seconds()
        if delay_sec > 0:
            timer = threading.Timer(delay_sec, _trigger_alarm, args=[a["label"]])
            timer.daemon = True
            timer.start()
            _active_timers[a["label"]] = timer
            restored += 1
        else:
            # Alarm time already passed — clean it up
            _delete_alarm(a["label"])
    if restored:
        print(f"[alarm_tool] Restored {restored} alarm(s) from DB.")