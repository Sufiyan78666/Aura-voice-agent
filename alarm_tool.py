"""
alarm_tool.py — Voice Agent Alarm Tool
Supports: set alarm, list alarms, cancel alarm
Compatible with: faster-whisper STT | Ollama gemma3 LLM | edge_tts TTS
"""

import threading
import time
import json
import os
import asyncio
import tempfile
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except OSError:
    AUDIO_AVAILABLE = False
try:
    import soundfile as sf
    SF_AVAILABLE = True
except Exception:
    SF_AVAILABLE = False
import edge_tts
from datetime import datetime, timedelta

# ── Persistent alarm storage ────────────────────────────────────────────────
ALARMS_FILE = "alarms.json"


def _load_alarms() -> list:
    if os.path.exists(ALARMS_FILE):
        with open(ALARMS_FILE, "r") as f:
            return json.load(f)
    return []


def _save_alarms(alarms: list):
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f, indent=2)


# ── In-memory alarm registry ────────────────────────────────────────────────
_active_timers: dict[str, threading.Timer] = {}


# ── TTS using edge_tts (same as voice_agent.py) ─────────────────────────────
def _speak(text: str, voice: str = "en-IN-NeerjaNeural"):
    try:
        asyncio.run(_speak_async(text, voice))
    except RuntimeError:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, _speak_async(text, voice))

async def _speak_async(text: str, voice: str):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_path = tmp.name
    tmp.close()
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_path)
    data, samplerate = sf.read(tmp_path)
    sd.play(data, samplerate)
    sd.wait()
    os.remove(tmp_path)


# ── Core alarm logic ────────────────────────────────────────────────────────
def _trigger_alarm(label: str):
    message = f"Alarm! {label}!" if label and label.lower() != "alarm" else "Your alarm is ringing!"
    print(f"\n🔔 ALARM FIRED: {label}")
    for _ in range(3):
        _speak(message)
        time.sleep(1.5)
    alarms = _load_alarms()
    alarms = [a for a in alarms if a["label"] != label]
    _save_alarms(alarms)
    _active_timers.pop(label, None)


def set_alarm(minutes: float = None, label: str = "Alarm",
              hour: int = None, minute: int = None) -> str:
    now = datetime.now()
    if minutes is not None:
        fire_at = now + timedelta(minutes=minutes)
        delay_sec = minutes * 60
        time_str = f"in {int(minutes)} minute{'s' if minutes != 1 else ''}"
    elif hour is not None and minute is not None:
        fire_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if fire_at <= now:
            fire_at += timedelta(days=1)
        delay_sec = (fire_at - now).total_seconds()
        time_str = f"at {fire_at.strftime('%I:%M %p')}"
    else:
        return "Please specify either minutes from now or an exact hour and minute."

    if label in _active_timers:
        _active_timers[label].cancel()

    timer = threading.Timer(delay_sec, _trigger_alarm, args=[label])
    timer.daemon = True
    timer.start()
    _active_timers[label] = timer

    alarms = _load_alarms()
    alarms = [a for a in alarms if a["label"] != label]
    alarms.append({"label": label, "fire_at": fire_at.isoformat()})
    _save_alarms(alarms)
    return f"Alarm set {time_str} for {label}."


def cancel_alarm(label: str = "Alarm") -> str:
    if label in _active_timers:
        _active_timers[label].cancel()
        _active_timers.pop(label)
        alarms = _load_alarms()
        alarms = [a for a in alarms if a["label"] != label]
        _save_alarms(alarms)
        return f"Alarm '{label}' cancelled."
    return f"No active alarm named '{label}' found."


def list_alarms() -> str:
    alarms = _load_alarms()
    if not alarms:
        return "You have no alarms set."
    parts = []
    for a in alarms:
        fire_at = datetime.fromisoformat(a["fire_at"])
        parts.append(f"{a['label']} at {fire_at.strftime('%I:%M %p')}")
    return "Your alarms are: " + ", ".join(parts) + "."


def restore_alarms():
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
    if restored:
        print(f"[alarm_tool] Restored {restored} alarm(s) from disk.")
