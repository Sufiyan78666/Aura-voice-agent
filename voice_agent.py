# voice_agent.py
# Hindi + English + Hinglish Voice Agent
# ✅ Weather + Alarm + File Opener + News + Web Search + RAG integrated

# Fix Windows cp1252 console — must be before any emoji print
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from faster_whisper import WhisperModel
import sounddevice as sd
import soundfile as sf
import numpy as np
from ollama import Client
import os, traceback, re, time
import json
import edge_tts
import asyncio
import tempfile
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# ENV LOADING
# ─────────────────────────────────────────────────────────────
import os
def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

load_env_file()

# ─────────────────────────────────────────────────────────────
# TOOLS IMPORT
# ─────────────────────────────────────────────────────────────
from weather_tool import get_weather
from alarm_tool import restore_alarms, set_alarm, cancel_alarm, list_alarms
from file_opener_tool import open_file_by_name, close_file_by_name
from datetime_tool import get_date_time
from news_tool import get_news, get_news_items
from websearch_tool import web_search
from rag_tool import query_rag, rebuild_index, build_index
from email_tool import (
    get_unread_emails,
    read_latest_email,
    search_emails,
    send_email,
    get_email_count,
)

from observability import obs, observe_v4
from guardrails import guard



# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
WHISPER_MODEL     = "small"
OLLAMA_MODEL      = os.environ.get("OLLAMA_MODEL", "gemma4:31b-cloud")
CALC_MODEL        = os.environ.get("CALC_MODEL", "gpt-oss:latest")
EMAIL_PARSE_MODEL = os.environ.get("EMAIL_PARSE_MODEL", CALC_MODEL)
OLLAMA_HOST       = os.environ.get("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY    = os.environ.get("OLLAMA_API_KEY")
SERPER_API_KEY    = os.environ.get("SERPER_API_KEY")
TAVILY_API_KEY    = os.environ.get("TAVILY_API_KEY")
FILE_SEARCH_ROOTS = os.environ.get("FILE_SEARCH_ROOTS", "")
RAG_DOCS_DIR      = os.environ.get("RAG_DOCS_DIR",  "./rag_docs")
RAG_INDEX_DIR     = os.environ.get("RAG_INDEX_DIR", "./rag_index")
RECORD_SECONDS    = 6
SAMPLE_RATE       = 16000
SILENCE_THRESHOLD = float(os.environ.get("SILENCE_THRESHOLD", "0.005"))
WAKE_WORD         = "boss"
NEWS_LANGUAGE     = os.environ.get("NEWS_LANGUAGE", "en")
NEWS_ITEMS        = int(os.environ.get("NEWS_ITEMS", "3"))
STREAM_DELAY_MS   = int(os.environ.get("STREAM_DELAY_MS", "10"))
SEARCH_RESULTS    = int(os.environ.get("SEARCH_RESULTS", "5"))
SEARCH_PROVIDER   = os.environ.get("SEARCH_PROVIDER", "duckduckgo")
SEARCH_API_KEY    = TAVILY_API_KEY if SEARCH_PROVIDER == "tavily" else SERPER_API_KEY
LANGFUSE_ENABLED  = os.environ.get("LANGFUSE_ENABLED", "1").lower() in ("1", "true", "yes")
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST       = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")

# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful voice assistant for Indian users.

CRITICAL LANGUAGE RULE — follow this exactly:
- Each user message begins with [LANG: en], [LANG: hi], or [LANG: hinglish].
- [LANG: en]       → Reply ONLY in English. No Hindi words at all.
- [LANG: hi]       → Reply ONLY in Hindi. No English words at all.
- [LANG: hinglish] → Reply naturally mixing Hindi and English, like Indians do in daily conversation.
- Never switch language unless the tag changes.

Keep replies SHORT (2-3 sentences max) — your reply will be spoken aloud.
Be warm and friendly like a helpful dost (friend).
You remember the full conversation history.
"""

# ─────────────────────────────────────────────────────────────
# LOAD WHISPER
# ─────────────────────────────────────────────────────────────
print("Loading Whisper model...")
stt_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
print("Whisper ready!")

if not OLLAMA_API_KEY:
    raise RuntimeError("OLLAMA_API_KEY is not set in your .env file.")

llm_client = Client(
    host=OLLAMA_HOST,
    headers={"Authorization": "Bearer " + OLLAMA_API_KEY}
)

# ─────────────────────────────────────────────────────────────
# LANGFUSE (OPTIONAL)
# ─────────────────────────────────────────────────────────────
# Removed internal langfuse logic - now handled in observability.py


# Removed internal log/flush functions



# ─────────────────────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────────────────────
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not history or history[0].get("role") != "system":
                history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
            return history
    return [{"role": "system", "content": SYSTEM_PROMPT}]

def save_memory(history):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

conversation_history = load_memory()


# ─────────────────────────────────────────────────────────────
# 🔧 TOOL DETECTION
# ─────────────────────────────────────────────────────────────
def strip_wake_word(text: str) -> str:
    return re.sub(rf"^{WAKE_WORD}[,\s]+", "", text, flags=re.IGNORECASE).strip()


@observe_v4(name="tool_detection")
def detect_and_run_tool(text: str, lang_tag: str) -> str | None:
    t = text.lower().strip()

    # ── EMAIL ─────────────────────────────────────────────────
    email_keywords = ["email", "emails", "mail", "inbox"]
    if any(re.search(rf"\b{kw}\b", t) for kw in email_keywords):
        if any(re.search(rf"\b{w}\b", t) for w in ["send", "write", "compose", "bhejo"]):
            print("📧  Tool: send_email (Parsing details with LLM...)")
            prompt = (
                "Extract the email details from the user's request.\n"
                "Output ONLY a valid JSON object with keys: 'to', 'subject', 'body'.\n"
                "If 'subject' or 'body' is missing, make up something brief but appropriate.\n"
                "Format 'to' as a proper email address (e.g. at -> @, dot -> .). Strip spaces from the email address.\n"
                f"User request: {text}\n"
                "JSON:"
            )
            try:
                try:
                    response = llm_client.chat(
                        model=EMAIL_PARSE_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                    )
                except Exception as e:
                    if "not found" in str(e).lower() and EMAIL_PARSE_MODEL != OLLAMA_MODEL:
                        response = llm_client.chat(
                            model=OLLAMA_MODEL,
                            messages=[{"role": "user", "content": prompt}],
                        )
                    else:
                        raise
                raw_json = response.message.content.strip()
                m = re.search(r"\{.*\}", raw_json, re.DOTALL)
                if m:
                    data = json.loads(m.group(0))
                    to = normalize_spelled_email(data.get("to", ""))
                    if to:
                        if "@" not in to:
                            to = f"{to}@gmail.com"
                        elif to.lower().endswith("@example.com"):
                            local = to.split("@", 1)[0]
                            to = f"{local}@gmail.com"
                    subject = data.get("subject", "Voice Email")
                    body = data.get("body", "Sent from Voice Agent")
                    if to:
                        confirm = confirm_email_address(to, lang_tag)
                        if confirm == "no":
                            speak("Please spell the email address slowly.", lang_tag)
                            audio = record_audio(max_seconds=10, silence_duration=1.2)
                            if has_speech(audio):
                                spelled_text, _, _ = transcribe(audio)
                                to = normalize_spelled_email(spelled_text)
                            else:
                                return "I did not catch the email address. Please try again and spell it out."

                            if not to:
                                return "I could not parse the email address. Please try again."

                            confirm = confirm_email_address(to, lang_tag)
                            if confirm != "yes":
                                return "Okay, I will not send the email."

                        elif confirm == "unclear":
                            return "I did not catch a clear yes or no. Please try again."

                        print(f"📧  Sending to {to} | Subject: {subject}")
                        return send_email(to, subject, body)
                return "I couldn't figure out the email details from your request."
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                return "Sorry, I had trouble parsing the email details."
        elif any(re.search(rf"\b{w}\b", t) for w in ["search", "find", "dhundo", "from"]):
            query = t
            for kw in ["search", "find", "dhundo", "emails", "email", "mail", "inbox", "from", "for", "about", "my"]:
                query = re.sub(rf"\b{kw}\b", " ", query, flags=re.IGNORECASE)
            query = re.sub(r"\s+", " ", query).strip(" ?.,")
            if query:
                print(f"📧  Tool: search_emails → query='{query}'")
                return search_emails(query=query)
            else:
                return "Who or what should I search for in your emails?"
        elif any(re.search(rf"\b{w}\b", t) for w in ["latest", "last", "aakhri", "recent", "newest"]):
            print("📧  Tool: read_latest_email")
            return read_latest_email()
        elif any(re.search(rf"\b{w}\b", t) for w in ["count", "how many", "kitne", "any unread", "do i have"]):
            print("📧  Tool: get_email_count")
            return get_email_count()
        else:
            print("📧  Tool: get_unread_emails")
            return get_unread_emails()

    # ── LIVE / REAL-TIME DATA ─────────────────────────────────
    _price_intent = any(re.search(rf"\b{w}\b", t) for w in [
        "price", "rate", "cost", "current", "today", "kitna", "kitne",
        "kya hai", "abhi", "aaj", "carat", "live",
    ])
    _live_metal  = any(re.search(rf"\b{w}\b", t) for w in ["gold", "silver", "platinum"])
    _live_always = [
        "score", "ipl", "match", "cricket", "nba", "football", "result",
        "petrol", "diesel", "fuel",
        "stock price", "share price", "nifty", "sensex",
        "bitcoin", "crypto", "btc", "eth",
        "exchange rate", "dollar rate", "usd", "rupee rate",
        # Hindi/Hinglish Phonetics & Script
        "स्कोर", "मैच", "क्रिकेट", "रिजल्ट", "आईपीएल", "भाव", "कीमत", "रेट",
        "jeeta", "hara", "kaun", "kab", "kya chal raha", "score kya",
        "मेज", "एल्श्ची", "चीस्के", "वर्सस", "बनाम",
    ]

    if (_live_metal and _price_intent) or any(re.search(rf"\b{kw}\b", t) for kw in _live_always) or any(kw in t for kw in ["मैच", "स्कोर", "आईपीएल"]):
        query   = extract_search_query(text) or text
        query   = normalize_live_query(query)
        
        # Boost sports queries
        if any(re.search(rf"\b{kw}\b", query.lower()) for kw in ["ipl", "cricket", "match", "score", "मैच", "स्कोर", "मेज"]):
            query = boost_live_sports_query(query)
            
        print(f"📡  Tool: live_data → web_search → query='{query}'")
        results = web_search(query=query, api_key=SEARCH_API_KEY,
                             num_results=SEARCH_RESULTS, provider=SEARCH_PROVIDER)
        if _should_retry_live_search(text, results):
            fallback_query = build_gold_price_query(text)
            if fallback_query and fallback_query != query:
                print(f"📡  Tool: live_data → fallback → query='{fallback_query}'")
                fallback = web_search(query=fallback_query, api_key=SEARCH_API_KEY,
                                      num_results=SEARCH_RESULTS, provider=SEARCH_PROVIDER)
                results = _merge_search_results(results, fallback)
        return summarize_live_data_answer(text, lang_tag, results)

    # ── WEATHER ──────────────────────────────────────────────
    weather_keywords = ["weather", "mausam", "temperature", "temp",
                        "barish", "rain", "forecast", "मौसम", "तापमान", "बारिश"]
    if any(kw in t for kw in weather_keywords):
        city = extract_city(t)
        if city:
            print(f"🌤  Tool: weather → city='{city}'")
            return get_weather(city)
        return "Please tell me the city name. For example, say: weather in Mumbai."

    # ── DATE/TIME ────────────────────────────────────────────
    dt_keywords = ["time", "date", "day", "today", "samay", "baje", "clock",
                   "aaj", "din", "tareekh", "tarikh", "समय", "तारीख", "बजे", "दिन", "आज"]
    if any(k in t for k in dt_keywords):
        print("🕒  Tool: datetime")
        return get_date_time(text)

    # ── NEWS ─────────────────────────────────────────────────
    news_keywords = ["news", "headlines", "headline", "breaking", "khabar", "samachar"]
    if any(kw in t for kw in news_keywords):
        country = extract_country(t)
        state   = extract_state(t)
        if not country and not state:
            return "Which country or state news do you want? Say worldwide, India, or a state like Goa."
        if state:
            print(f"🗞  Tool: news → state='{state}'")
            headlines = get_news_items(country="India", language=NEWS_LANGUAGE,
                                       max_items=NEWS_ITEMS, query=f"{state} news")
            label = f"for {state}"
        else:
            print(f"🗞  Tool: news → country='{country}'")
            headlines = get_news_items(country=country, language=NEWS_LANGUAGE,
                                       max_items=NEWS_ITEMS)
            label = "worldwide" if country.lower() in (
                "worldwide", "global", "international", "world") else f"for {country}"
        if not headlines:
            return "Sorry, I could not fetch the latest news right now."
        for idx, title in enumerate(headlines, 1):
            print(f"   {idx}. {title}")
        return f"Top headlines {label}: {'; '.join(headlines)}."

    # ── RAG — search my documents (BEFORE web search) ────────
    rag_triggers = [
        # English
        "my document", "my pdf", "my book", "my notes", "my report", "my file",
        "in my doc", "from my doc", "in the book", "from the book",
        "search document", "search the document", "search my doc",
        "find in document", "look in document", "check document",
        "what does the book", "what does my doc", "what is in my doc",
        "tell me from", "read from my", "according to my",
        # Hindi/Hinglish
        "mere document", "meri file", "mera pdf", "meri book",
        "document mein", "file mein", "book mein",
        "rebuild index", "reindex", "re-index",
    ]
    if any(kw in t for kw in rag_triggers):
        if "rebuild" in t or "reindex" in t or "re-index" in t:
            print("📚  Tool: rag_rebuild")
            return rebuild_index(docs_dir=RAG_DOCS_DIR, index_dir=RAG_INDEX_DIR)
        # Strip trigger phrases to get the actual question
        question = re.sub(
            r"(search|find|look up|check|tell me|read|what does|what is|"
            r"in my|my document|my doc|my file|my pdf|my book|my notes|"
            r"from my|from the|in the|according to|document mein|"
            r"mere document|meri file|mera pdf|file mein|book mein)",
            " ", text, flags=re.IGNORECASE
        )
        question = re.sub(r"\s+", " ", question).strip(" ?.,")
        if not question or len(question) < 3:
            question = text
        print(f"📚  Tool: rag_query → '{question}'")
        return query_rag(
            question=question,
            ollama_host=OLLAMA_HOST,
            ollama_model=OLLAMA_MODEL,
            api_key=OLLAMA_API_KEY,
            docs_dir=RAG_DOCS_DIR,
            index_dir=RAG_INDEX_DIR,
        )

    # ── WEB SEARCH ───────────────────────────────────────────
    search_keywords = ["search", "web search", "google", "find", "lookup"]
    if any(kw in t for kw in search_keywords):
        query = extract_search_query(text)
        if not query:
            return "What should I search for?"
        print(f"🔎  Tool: web_search → query='{query}'")
        return web_search(query=query, api_key=SEARCH_API_KEY,
                          num_results=SEARCH_RESULTS, provider=SEARCH_PROVIDER)

    # ── FILE CLOSER ───────────────────────────────────────────
    _close_triggers = ["close", "shut", "band karo", "band kar"]
    if any(w in t for w in _close_triggers):
        roots = ([p.strip() for p in FILE_SEARCH_ROOTS.split(";") if p.strip()]
                 if FILE_SEARCH_ROOTS else [os.getcwd()])
        print("📂  Tool: file_closer")
        return close_file_by_name(user_text=text, search_roots=roots,
                                  model=CALC_MODEL, host=OLLAMA_HOST, api_key=OLLAMA_API_KEY)

    # ── FILE OPENER ───────────────────────────────────────────
    _file_triggers = ["open", "launch", "kholna", "khol"]
    _file_keywords = ["file", "resume", "cv", "document", "pdf", "doc",
                      "docx", "ppt", "pptx", "xls", "xlsx"]
    _has_trigger = any(w in t.split() for w in _file_triggers)
    _has_keyword = any(k in t for k in _file_keywords)
    _has_ext     = bool(re.search(r"\b[\w\-]+\.(pdf|doc|docx|txt|md|ppt|pptx|xls|xlsx)\b", t))
    _remaining   = re.sub(r"\b(open|launch|kholna|khol)\b", "", t).strip()
    _has_named   = _has_trigger and len(_remaining) >= 2 and bool(re.search(r"[a-zA-Z]", _remaining))

    if _has_ext or (_has_trigger and _has_keyword) or _has_named:
        roots = ([p.strip() for p in FILE_SEARCH_ROOTS.split(";") if p.strip()]
                 if FILE_SEARCH_ROOTS else [os.getcwd()])
        print("📂  Tool: file_opener")
        return open_file_by_name(user_text=text, search_roots=roots,
                                 model=CALC_MODEL, host=OLLAMA_HOST, api_key=OLLAMA_API_KEY)

    # ── ALARM ─────────────────────────────────────────────────
    has_alarm_word = any(w in t for w in
        ["alarm", "alarms", "timer", "remind", "laga", "lagao", "yaad dilao"])
    if has_alarm_word:
        list_triggers   = ["list", "show", "display", "kitne", "kaunse", "all",
                           "what", "mere", "mera", "my", "bata", "batao"]
        cancel_triggers = ["cancel", "band", "hatao", "stop", "delete", "remove", "clear"]
        set_triggers    = ["set", "laga", "lagao", "create", "add", "remind", "start"]
        time_words      = ["minute", "min", "mins", "hour", "ghante", "baje", "seconds", "sec"]

        has_list   = any(w in t for w in list_triggers)
        has_cancel = any(w in t for w in cancel_triggers)
        has_set    = any(w in t for w in set_triggers)
        has_time   = (any(w in t for w in time_words)
                      or bool(extract_minutes(t))
                      or extract_time(t)[0] is not None)

        if has_cancel and not has_set:
            label = extract_label(t) or "Alarm"
            print(f"⏰  Tool: cancel_alarm → label='{label}'")
            return cancel_alarm(label=label)
        elif has_time or has_set:
            minutes = extract_minutes(t)
            hour, minute = extract_time(t)
            if minutes:
                label = extract_label(t) or "Alarm"
                print(f"⏰  Tool: set_alarm → minutes={minutes}, label='{label}'")
                return set_alarm(minutes=minutes, label=label)
            elif hour is not None:
                label = extract_label(t) or "Alarm"
                print(f"⏰  Tool: set_alarm → time={hour}:{minute:02d}, label='{label}'")
                return set_alarm(hour=hour, minute=minute, label=label)
            else:
                return "Kitne minute mein alarm chahiye? For example: set alarm for 10 minutes."
        elif has_list:
            print("⏰  Tool: list_alarms")
            return list_alarms()
        else:
            print("⏰  Tool: list_alarms (default)")
            return list_alarms()

    return None   # no tool matched → go to LLM

    return None   # no tool matched → go to LLM


# ─────────────────────────────────────────────────────────────
# LIVE DATA HELPERS
# ─────────────────────────────────────────────────────────────
def normalize_live_query(query: str) -> str:
    q = query.strip()
    q = re.sub(r"^\d+\s+", "", q)
    q = re.sub(r"\bthe\s+latest\b", "latest", q, flags=re.IGNORECASE)
    q = re.sub(r"\blse\b", "lsg", q, flags=re.IGNORECASE)
    q = re.sub(r"\blhg\b", "lsg", q, flags=re.IGNORECASE)
    q = re.sub(r"\blife\s+score\b", "live score", q, flags=re.IGNORECASE)
    if re.search(r"\bscore\b", q, re.IGNORECASE):
        q = re.sub(r"\blife\b", "live", q, flags=re.IGNORECASE)
    wants_latest = bool(re.search(r"\b(latest|today|current|live|abhi|aaj)\b", q, re.IGNORECASE))
    wants_yesterday = bool(re.search(r"\b(yesterday|kal|last night)\b", q, re.IGNORECASE))
    if wants_latest and not wants_yesterday and not re.search(r"\btoday\b", q, re.IGNORECASE):
        # Only add 'today' if it's not already there and if it's late in the day (rough heuristic)
        # For now, let's just make it 'latest' to avoid midnight confusion
        if "latest" not in q.lower():
            q = f"latest {q}"
    if re.search(r"\bgold\b", q, re.IGNORECASE):
        q = re.sub(r"\bprize\b", "price", q, flags=re.IGNORECASE)
        if not re.search(r"\bprice\b|\brate\b|\bcost\b", q, re.IGNORECASE):
            q = f"{q} price"
    if re.search(r"\bipl\b", q, re.IGNORECASE) and not re.search(r"\blive\b", q, re.IGNORECASE):
        q = f"live {q}"
    return q


def boost_live_sports_query(query: str) -> str:
    q = query
    if not re.search(r"\b(today|latest|live|aaj|abhi|आज|अभी|लेट़च्)\b", q, re.IGNORECASE):
        q = f"{q} latest"
    if not re.search(r"\b(scorecard|result)\b", q, re.IGNORECASE):
        q = f"{q} scorecard"
    trusted = "(site:espncricinfo.com OR site:cricbuzz.com OR site:iplt20.com)"
    if "site:" not in q:
        q = f"{q} {trusted}"
    return q


@observe_v4(name="live_data_summary", as_type="generation")
def summarize_live_data_answer(user_text: str, lang_tag: str, search_results: str) -> str:
    if _search_failed(search_results):
        return _live_data_fallback(lang_tag)
    system_prompt = (
        "You are a helpful voice assistant for Indian users. "
        "Answer using the requested language tag only. Keep it to 1-2 sentences. "
        "Use the search results to answer the question. "
        "If the results do not contain a specific live value, say you could not find it "
        "and suggest checking a reliable app or website. Do not list multiple results."
    )
    user_prompt = (
        f"[LANG: {lang_tag}]\nQuestion: {user_text}\n\nSearch results:\n{search_results}"
    )
    try:
        response = llm_client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user",   "content": user_prompt}],
        )
        answer = response.message.content.strip()
        if hasattr(response, 'prompt_eval_count') and response.prompt_eval_count:
            obs.update_usage(response.prompt_eval_count, response.eval_count, model=OLLAMA_MODEL)
        
        obs.add_score(name="summary_success", value=1.0)
        return answer if answer else _live_data_fallback(lang_tag)
    except Exception:
        return _live_data_fallback(lang_tag)


def _search_failed(s: str) -> bool:
    if not s: return True
    return any(p in s.lower() for p in [
        "no results found", "search api key is missing",
        "could not reach the search service",
        "could not parse the search results", "search service error",
    ])


def _live_data_fallback(lang_tag: str) -> str:
    if lang_tag == "hi":
        return "माफ कीजिए, मैं अभी लाइव कीमत नहीं ला पाया। कृपया किसी भरोसेमंद ऐप पर देखें।"
    if lang_tag == "hinglish":
        return "Sorry, abhi live value nahi mil pa rahi. Please kisi trusted app par check kar lo."
    return "Sorry, I could not fetch the live value right now. Please check a trusted app."


def extract_gold_karat(text: str) -> str | None:
    t = text.lower()
    for k in ["24", "22", "18", "14", "10", "23"]:
        if re.search(rf"\b{k}\b|{k}k|{k}\s*carat|{k}\s*karat", t):
            return f"{k}k"
    return None


def format_gold_price_response(gold_data: dict, lang_tag: str) -> str:
    karat   = gold_data.get("karat", "24k").upper()
    per_g   = gold_data.get("per_gram")
    per_10g = gold_data.get("per_10g")
    if lang_tag == "hi":
        if per_g and per_10g:
            return f"भारत में {karat} सोने का भाव ₹{per_g} प्रति ग्राम (₹{per_10g} प्रति 10 ग्राम) है।"
        return "माफ कीजिए, अभी सटीक सोने का भाव नहीं मिला।"
    if lang_tag == "hinglish":
        if per_g and per_10g:
            return f"India mein {karat} gold ka rate ₹{per_g} per gram (₹{per_10g} per 10 gram) hai."
        return "Sorry, abhi exact gold rate nahi mila."
    if per_g and per_10g:
        return f"In India, {karat} gold is ₹{per_g} per gram (₹{per_10g} per 10 grams)."
    return "Sorry, I could not fetch the exact gold rate right now."


def build_gold_price_query(user_text: str) -> str | None:
    t = user_text.lower()
    if "gold" not in t: return None
    karat = "24k"
    if re.search(r"\b22\b|22k|22\s*carat", t): karat = "22k"
    return f"{karat} gold rate India per 10 gram today"


def _should_retry_live_search(user_text: str, results: str) -> bool:
    if "gold" not in user_text.lower(): return False
    return _search_failed(results) or not _results_have_price_value(results)


def _results_have_price_value(s: str) -> bool:
    return any(re.search(p, s.lower()) for p in [
        r"₹\s*\d", r"\brs\.?\s*\d", r"\binr\s*\d",
        r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b",
    ])


def _merge_search_results(primary: str, fallback: str) -> str:
    if not primary: return fallback
    if not fallback: return primary
    return f"{primary}\nFallback: {fallback}"


# ─────────────────────────────────────────────────────────────
# 🔍 HELPER EXTRACTORS
# ─────────────────────────────────────────────────────────────
CITIES = [
    "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "pune", "ahmedabad", "jaipur", "surat", "lucknow", "kanpur",
    "nagpur", "visakhapatnam", "bhopal", "patna", "vadodara", "ludhiana",
    "agra", "nashik", "meerut", "rajkot", "varanasi", "amritsar", "aurangabad",
    "navi mumbai", "thane", "gurgaon", "gurugram", "noida", "indore",
    "london", "new york", "paris", "dubai", "singapore", "tokyo", "sydney",
]

EXCLUDE_CITY_WORDS = [
    "weather", "mausam", "temperature", "temp", "today", "aaj", "kaisa", 
    "score", "match", "news", "khabar", "headlines", "latest", "time", 
    "batao", "boliye", "bataiye", "how", "what", "where"
]

COUNTRIES = {
    "worldwide": "worldwide", "world": "worldwide", "global": "worldwide",
    "international": "worldwide", "india": "India", "bharat": "India",
    "usa": "United States", "us": "United States", "united states": "United States",
    "america": "United States", "uk": "United Kingdom", "united kingdom": "United Kingdom",
    "england": "United Kingdom", "uae": "UAE", "dubai": "UAE",
    "canada": "Canada", "australia": "Australia", "singapore": "Singapore",
    "japan": "Japan", "france": "France", "germany": "Germany",
}

STATES = {
    "goa": "Goa", "maharashtra": "Maharashtra", "karnataka": "Karnataka",
    "kerala": "Kerala", "tamil nadu": "Tamil Nadu", "delhi": "Delhi",
    "uttar pradesh": "Uttar Pradesh", "gujarat": "Gujarat",
    "rajasthan": "Rajasthan", "west bengal": "West Bengal",
    "telangana": "Telangana", "andhra pradesh": "Andhra Pradesh",
    "madhya pradesh": "Madhya Pradesh", "punjab": "Punjab", "bihar": "Bihar",
    "odisha": "Odisha", "assam": "Assam", "haryana": "Haryana",
    "jharkhand": "Jharkhand", "chhattisgarh": "Chhattisgarh",
    "uttarakhand": "Uttarakhand", "himachal pradesh": "Himachal Pradesh",
    "jammu and kashmir": "Jammu and Kashmir",
}

def extract_city(text: str) -> str | None:
    t = text.lower()
    for city in CITIES:
        if city in t: return city.title()
    for marker in [" in ", " for ", " of ", " mein ", " ka ", " ki "]:
        if marker in t:
            after = t.split(marker, 1)[1].strip()
            word  = after.split()[0].rstrip("?.!,")
            if len(word) > 2 and word.lower() not in EXCLUDE_CITY_WORDS: 
                return word.title()
    return None

def extract_country(text: str) -> str | None:
    t = text.lower()
    for key, name in COUNTRIES.items():
        if key in t: return name
    return None

def extract_state(text: str) -> str | None:
    t = text.lower()
    for key, name in STATES.items():
        if key in t: return name
    return None

def extract_search_query(text: str) -> str:
    t = text.strip()
    t = re.sub(rf"\b{re.escape(WAKE_WORD)}\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(web\s*search|search|google|find|lookup)\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(for|about|on|online)\b", " ", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip(" ?!.,")

def extract_minutes(text: str) -> float | None:
    hindi_nums = {
        "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
        "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "pandrah": 15, "bees": 20, "tees": 30,
    }
    t = text.lower()
    for word, val in hindi_nums.items():
        if word in t and ("minute" in t or "min" in t): return float(val)
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:minute|min|mins)", t)
    if m: return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hour|hr|ghante)", t)
    if m: return float(m.group(1)) * 60
    return None

def extract_time(text: str) -> tuple[int | None, int]:
    t = re.sub(r"\b([ap])\s*\.?\s*m\.?\b", r"\1m", text.lower())
    m = re.search(r"(\d{1,2})[:\.](\d{2})\s*(am|pm)?", t)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        mer = m.group(3) or ("pm" if "pm" in t else ("am" if "am" in t else None))
        if mer == "pm" and h != 12: h += 12
        if mer == "am" and h == 12: h = 0
        return h % 24, mn
    m = re.search(r"(\d{1,2})\s+(\d{2})\s*(am|pm)", t)
    if m:
        h, mn, mer = int(m.group(1)), int(m.group(2)), m.group(3)
        if mer == "pm" and h != 12: h += 12
        if mer == "am" and h == 12: h = 0
        return h % 24, mn
    m = re.search(r"(\d{1,2})\s*(am|pm|baje|o'?clock)", t)
    if m:
        h, mer = int(m.group(1)), m.group(2)
        if mer == "pm" and h != 12: h += 12
        if mer == "am" and h == 12: h = 0
        return h % 24, 0
    return None, 0

def extract_label(text: str) -> str | None:
    t = text.lower()
    for marker in [" for ", " named ", " called ", " label "]:
        if marker in t:
            after = t.split(marker, 1)[1].strip()
            label = after.split()[0].rstrip("?.!,")
            if label not in ("alarm", "timer", "remind", "minute", "min", "hour"):
                return label.capitalize()
    return None


def normalize_spelled_email(spoken: str) -> str:
    t = spoken.lower().strip()
    t = re.sub(r"\bat\b", "@", t)
    t = re.sub(r"\bdot\b", ".", t)
    t = re.sub(r"\bunderscore\b", "_", t)
    t = re.sub(r"\bhyphen\b|\bdash\b", "-", t)
    t = re.sub(r"\bspace\b", "", t)

    digits = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "oh": "0",
    }

    def _expand_repeat(match: re.Match) -> str:
        word = match.group(1)
        d = digits.get(word, word)
        return d * 2

    def _expand_triple(match: re.Match) -> str:
        word = match.group(1)
        d = digits.get(word, word)
        return d * 3

    t = re.sub(r"double\s*([0-9]|zero|one|two|three|four|five|six|seven|eight|nine|oh)", _expand_repeat, t)
    t = re.sub(r"triple\s*([0-9]|zero|one|two|three|four|five|six|seven|eight|nine|oh)", _expand_triple, t)

    for word, d in digits.items():
        t = re.sub(rf"\b{word}\b", d, t)

    t = re.sub(r"\s+", "", t)
    t = t.replace("gmailcom", "gmail.com")

    # If user spelled letters like s-u-f-i, collapse those hyphens.
    if re.search(r"(?:[a-z]-){2,}[a-z]", t):
        t = re.sub(r"(?<=[a-z])-(?=[a-z])", "", t)

    # Keep only valid email characters after normalization
    t = re.sub(r"[^a-z0-9@._-]", "", t)

    if t and "@" not in t:
        t = f"{t}@gmail.com"
    return t


def confirm_email_address(email_addr: str, lang_tag: str) -> str:
    yes_words = ["yes", "yeah", "yep", "send", "ok", "okay", "haan", "han", "ha"]
    no_words = ["no", "nope", "nah", "nahi", "mat", "cancel", "stop"]

    for attempt in range(2):
        if lang_tag == "hi":
            prompt = f"Main is email par bheju: {email_addr}? Haan ya nahi."
        elif lang_tag == "hinglish":
            prompt = f"Main is email par bheju: {email_addr}? Haan ya no boliye."
        else:
            prompt = f"I got {email_addr}. Should I send it? Say yes or no."

        if attempt == 1:
            if lang_tag == "hi":
                prompt = "Kripya sirf haan ya nahi boliye."
            elif lang_tag == "hinglish":
                prompt = "Please sirf haan ya no boliye."
            else:
                prompt = "Please say only yes or no."

        speak(prompt, lang_tag)
        audio = record_audio(max_seconds=6, silence_duration=1.2)
        if not has_speech(audio):
            continue
        response_text, _, _ = transcribe(audio)
        r = response_text.lower()
        tokens = re.findall(r"[a-z']+", r)
        yes_hit = any(re.search(rf"\b{re.escape(w)}\b", r) for w in yes_words)
        no_hit = any(re.search(rf"\b{re.escape(w)}\b", r) for w in no_words)
        if yes_hit and not no_hit:
            return "yes"
        if no_hit and not yes_hit and len(tokens) <= 3:
            return "no"

    return "unclear"


# ─────────────────────────────────────────────────────────────
# AUDIO FUNCTIONS
# ─────────────────────────────────────────────────────────────
def record_audio(max_seconds=15, silence_duration=1.5):
    print(f"\n🎙  Bol! Listening (will stop after {silence_duration}s of silence)...")
    frames = []
    chunk_size = int(SAMPLE_RATE * 0.1)
    silence_chunks = 0
    max_silence_chunks = int(silence_duration / 0.1)
    has_spoken = False
    
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            for _ in range(int(max_seconds / 0.1)):
                data, overflowed = stream.read(chunk_size)
                frames.append(data.copy())
                
                rms = np.sqrt(np.mean(data ** 2))
                if rms > SILENCE_THRESHOLD:
                    has_spoken = True
                    silence_chunks = 0
                else:
                    if has_spoken:
                        silence_chunks += 1
                        
                if has_spoken and silence_chunks >= max_silence_chunks:
                    break
    except Exception as e:
        print(f"Recording error: {e}")
        
    print("Recording complete.")
    if frames:
        audio = np.concatenate(frames, axis=0)
        overall_rms = np.sqrt(np.mean(audio ** 2))
        print(f"🔈 RMS level: {overall_rms:.5f} (threshold: {SILENCE_THRESHOLD})")
        return audio.flatten()
    return np.array([])

def has_speech(audio_array) -> bool:
    return np.sqrt(np.mean(audio_array ** 2)) > SILENCE_THRESHOLD

def transcribe(audio_array):
    temp_file = "temp_recording.wav"
    sf.write(temp_file, audio_array, SAMPLE_RATE)
    segments, info = stt_model.transcribe(
        temp_file, language=None, task="transcribe", beam_size=5, vad_filter=True)
    text = " ".join([seg.text for seg in segments]).strip()
    os.remove(temp_file)
    return text, info.language, info.language_probability

def is_valid_transcript(text, raw_lang, confidence):
    if not text: return False, "no text"
    if raw_lang not in ("hi", "en"): return False, f"detected as '{raw_lang}'"
    if len(text.split()) <= 2 and confidence < 0.60:
        return False, f"too short + low confidence ({confidence:.0%})"
    return True, ""

def get_lang_tag(detected_lang, confidence):
    if detected_lang == "hi":
        return ("hi", f"Hindi ({confidence:.0%})") if confidence >= 0.75 \
               else ("hinglish", f"Hinglish ({confidence:.0%})")
    return ("en", f"English ({confidence:.0%})") if confidence >= 0.50 \
           else ("hinglish", f"Hinglish ({confidence:.0%})")


# ─────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────
@observe_v4(name="chat_generation", as_type="generation")
def ask_llm(user_text, lang_tag):
    # 1. Input Guardrail
    is_safe, reason = guard.check_input(user_text)
    if not is_safe:
        obs.add_score(name="safety_score", value=0.0, comment=f"Input rejected: {reason}")
        obs.flush()
        return f"I'm sorry, I cannot process this request as it violates safety guidelines: {reason}"

    tagged_text = f"[LANG: {lang_tag}] {user_text}"
    conversation_history.append({"role": "user", "content": tagged_text})
    reply_parts = []
    print("🤖 Agent (stream): ", end="", flush=True)
    start_time = time.time()
    stream_error = None
    try:
        stream    = llm_client.chat(model=OLLAMA_MODEL, messages=conversation_history, stream=True)
        got_token = False
        for chunk in stream:
            token = getattr(chunk, "message", None)
            if token and getattr(token, "content", None):
                reply_parts.append(token.content)
                got_token = True
                _print_stream(token.content, STREAM_DELAY_MS)
            
            # Ollama sends usage in the final chunk
            if hasattr(chunk, 'prompt_eval_count') and chunk.prompt_eval_count:
                obs.update_usage(chunk.prompt_eval_count, chunk.eval_count, model=OLLAMA_MODEL)
                
        if not got_token:
            raise RuntimeError("No stream tokens")
    except Exception as exc:
        stream_error = exc
        try:
            response = llm_client.chat(model=OLLAMA_MODEL, messages=conversation_history)
            _print_stream(response.message.content, STREAM_DELAY_MS)
            reply_parts.append(response.message.content)
            # Capture usage from non-stream response
            if hasattr(response, 'prompt_eval_count') and response.prompt_eval_count:
                obs.update_usage(response.prompt_eval_count, response.eval_count, model=OLLAMA_MODEL)
        except Exception as fallback_exc:
            # Fallback error logging removed (handled by decorator)
            raise
    print()
    reply = "".join(reply_parts).strip()
    
    # 2. Output Guardrail
    is_safe_out, reason_out = guard.check_output(reply)
    if not is_safe_out:
        obs.add_score(name="safety_score", value=0.0, comment=f"Output rejected: {reason_out}")
        obs.flush()
        return "I'm sorry, but I generated a response that violates my safety guidelines. Let me try to be more helpful."

    conversation_history.append({"role": "assistant", "content": reply})
    save_memory(conversation_history)
    
    # Add a success score and a safety score
    obs.add_score(name="response_success", value=1.0, comment="Successful LLM generation")
    obs.add_score(name="safety_score", value=1.0, comment="Passed safety checks")
    obs.flush()
    return reply

def _print_stream(text: str, delay_ms: int = 0) -> None:
    if delay_ms <= 0:
        print(text, end="", flush=True)
        return
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay_ms / 1000.0)


# ─────────────────────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────────────────────
def speak(text, lang_tag="en"):
    import emoji
    voice = {"hi": "hi-IN-SwaraNeural", "hinglish": "hi-IN-MadhurNeural"}.get(
        lang_tag, "en-IN-NeerjaNeural")
    
    # Strip markdown symbols so TTS doesn't say "asterisk" out loud
    clean_text = text.replace("*", "").replace("#", "")
    
    # Print it to console WITH the emoji
    print(f"🔊 Speaking: {clean_text}")
    
    # Strip emojis entirely before sending to TTS so it doesn't say "dog face"
    tts_text = emoji.replace_emoji(clean_text, replace="")
    
    asyncio.run(_speak_async(tts_text, voice))

async def _speak_async(text, voice):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_path = tmp.name
    tmp.close()
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_path)
    data, samplerate = sf.read(tmp_path)
    sd.play(data, samplerate)
    sd.wait()
    os.remove(tmp_path)


# ─────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*56)
    print("   🤖 Hindi + English + Hinglish Voice Agent")
    print(f"   Model    : {OLLAMA_MODEL}")
    print(f"   STT      : Whisper {WHISPER_MODEL}")
    print(f"   Memory   : {len(conversation_history)-1} past messages loaded")
    print("   Tools    : 🌤 Weather  ⏰ Alarm  📂 Files  🗞 News  🔎 Search  📚 RAG")
    print(f"   Wake Word: '{WAKE_WORD.upper()}'")
    print(f"   Tool LLM : {CALC_MODEL}")
    print("="*56)
    print("Ctrl+C to quit\n")

    restore_alarms()

    # RAG — lazy load (only loads from disk if index exists, builds on first query)
    build_index(docs_dir=RAG_DOCS_DIR, index_dir=RAG_INDEX_DIR, lazy=True)

    turn = 1
    while True:
        try:
            print(f"─── Turn {turn} ───────────────────────────")
            audio = record_audio()

            if not has_speech(audio):
                print("🔇 Silence — please speak clearly.")
                continue

            user_text, raw_lang, confidence = transcribe(audio)
            valid, reason = is_valid_transcript(user_text, raw_lang, confidence)
            if not valid:
                print(f"🚫 Invalid ({reason}) — please speak in Hindi or English.")
                continue

            lang_tag, lang_label = get_lang_tag(raw_lang, confidence)

            # Strip wake word if present
            clean_text = strip_wake_word(user_text)
            if clean_text != user_text:
                print(f"👤 You [{lang_label}] (Boss): {user_text}")
                user_text = clean_text
            else:
                print(f"👤 You [{lang_label}]: {user_text}")

            tool_response = detect_and_run_tool(user_text, lang_tag)

            if tool_response:
                print("🔧 Tool response (stream): ", end="", flush=True)
                _print_stream(tool_response, STREAM_DELAY_MS)
                print()
                conversation_history.append({"role": "user",      "content": f"[LANG: {lang_tag}] {user_text}"})
                conversation_history.append({"role": "assistant",  "content": tool_response})
                save_memory(conversation_history)
                obs.flush()
                speak(tool_response, lang_tag)
            else:
                reply = ask_llm(user_text, lang_tag)
                speak(reply, lang_tag)

            print(f"   [Memory: {len(conversation_history)} messages]")
            turn += 1
            print()

            again = input("Press Enter to speak again, 'q' to quit: ")
            if again.strip().lower() == "q":
                print("Alvida! Goodbye!")
                break

        except KeyboardInterrupt:
            print("\n\nAlvida! Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            traceback.print_exc()
            turn += 1
            input("Press Enter to retry...")


if __name__ == "__main__":
    main()