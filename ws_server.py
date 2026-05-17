"""
Lightweight WebSocket server bridging frontend ↔ voice_agent tools.
Run: python ws_server.py
"""
import asyncio, json, sys, os, re, traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def load_env_file(path=".env"):
    if not os.path.exists(path): return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key:
                # Overwrite if missing OR if currently empty string
                if key not in os.environ or not os.environ[key].strip():
                    os.environ[key] = value

load_env_file()

# ─── Langfuse Observability ───
from observability import obs, observe_v4

import psycopg2
from psycopg2.extras import Json

def get_db_conn():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(db_url)

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("⚠️  DATABASE_URL not set — memory will not persist this session.")
        return
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    history JSONB NOT NULL,
                    CHECK (id = 1)
                )
            """)
        conn.commit()
    print("✅ PostgreSQL memory initialized.")

def load_memory():
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT history FROM memory WHERE id = 1")
                row = cur.fetchone()
                if row:
                    history = row[0]
                    if not history or history[0].get("role") != "system":
                        history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
                    return history
    except Exception as e:
        print(f"⚠️ DB load error: {e}")
    return [{"role": "system", "content": SYSTEM_PROMPT}]

def save_memory(history):
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO memory (id, history) VALUES (1, %s)
                    ON CONFLICT (id) DO UPDATE SET history = EXCLUDED.history
                """, (Json(history),))
            conn.commit()
    except Exception as e:
        print(f"⚠️ DB save error: {e}")


SYSTEM_PROMPT = """You are a helpful AI voice assistant for Indian users.

STRICT LANGUAGE RULES:
1. If the user speaks in English, you MUST reply in 100% English. No Hindi words at all.
2. If the user speaks in Hindi or Hinglish, reply in Hinglish (natural mix).
3. Always match the user's tone and language style.

VOICE-FRIENDLY OUTPUT:
- Do NOT use markdown symbols like ** or #. 
- Do NOT use bolding or bullet points. 
- Write in plain paragraphs.
- Do NOT use math symbols like $, _, ^, or \\text{}.
- Write chemical formulas in plain text (e.g. H2O).
- Keep replies SHORT (2-3 sentences max).

Be warm and friendly like a helpful dost.
Do NOT use any emojis.
You remember the full conversation history. If a user tells you a new name, update your belief immediately.
"""


OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:31b-cloud")
CALC_MODEL   = os.environ.get("CALC_MODEL", "qwen3.5:122b")
OLLAMA_HOST  = os.environ.get("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
WAKE_WORD    = "boss"
WS_PORT      = int(os.environ.get("WS_PORT", "8765"))
SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "duckduckgo")
TAVILY_API_KEY  = os.environ.get("TAVILY_API_KEY")
SERPER_API_KEY  = os.environ.get("SERPER_API_KEY")
SEARCH_API_KEY  = TAVILY_API_KEY if SEARCH_PROVIDER == "tavily" else SERPER_API_KEY
SEARCH_RESULTS  = int(os.environ.get("SEARCH_RESULTS", "5"))
RAG_DOCS_DIR = os.environ.get("RAG_DOCS_DIR", "./rag_docs")
RAG_INDEX_DIR = os.environ.get("RAG_INDEX_DIR", "./rag_index")

# ─── Lazy tool imports (avoid heavy loading at startup) ───
def _run_weather(city):
    from weather_tool import get_weather
    return get_weather(city)

def _run_datetime(text):
    from datetime_tool import get_date_time
    return get_date_time(text)

def _run_list_alarms():
    from alarm_tool import list_alarms
    return list_alarms()

def _run_set_alarm(minutes=None, hour=None, minute=0, label="Alarm"):
    from alarm_tool import set_alarm
    return set_alarm(minutes=minutes, hour=hour, minute=minute, label=label)

def _run_news(text):
    from news_tool import get_news_items
    q = re.sub(r"\b(latest|news|headlines|khabar|samachar|न्यूज़|न्यूज|हैडलाइंस|खबर|समाचार|tell|me|about|the)\b", " ", text, flags=re.IGNORECASE).strip()
    items = get_news_items(country="India", language="en", max_items=3, query=q if q else None)
    return "Top headlines: " + "; ".join(items) if items else "Could not fetch news."

def _run_email_count():
    from email_tool import get_email_count
    return get_email_count()

def _run_email_unread():
    from email_tool import get_unread_emails
    return get_unread_emails()

def _run_send_email(text):
    from ollama import Client
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None
    client = Client(host=OLLAMA_HOST, headers=headers)
    prompt = f"Extract recipient email, subject, and body from the text. Return JSON only: {{\"to\": \"...\", \"subject\": \"...\", \"body\": \"...\"}}. Text: {text}"
    try:
        res = client.chat(model=OLLAMA_MODEL, messages=[{"role":"user", "content":prompt}])
        match = re.search(r'\{.*\}', res['message']['content'], re.DOTALL)
        if not match: return None, "I couldn't parse the email details. Please say who to send it to and what to say."
        data = json.loads(match.group())
        to_addr = data['to'].strip().lower()
        if "@" not in to_addr:
            clean_name = re.sub(r'\s+', '', to_addr)
            if any(char.isdigit() for char in clean_name) or len(clean_name) > 5:
                to_addr = f"{clean_name}@gmail.com"
            else:
                return None, f"I found the recipient '{data['to']}' but it's not a valid email address. Please provide the full email."
        
        data['to'] = to_addr
        return data, f"I've prepared an email to {to_addr} with subject '{data['subject']}'. Should I send it? Say 'Confirm' to proceed."
    except Exception as e:
        return None, f"Failed to process email request: {e}"

def _run_file_opener(filename):
    from file_opener_tool import open_file_by_name
    return open_file_by_name(filename, search_roots=[r"C:\Users\asus\Desktop", r"C:\Users\asus\Documents", r"C:\Users\asus\Downloads"])

def _run_calculator(expression):
    from calculator_tool import calculate_expression
    return calculate_expression(expression, model=CALC_MODEL, host=OLLAMA_HOST, api_key=OLLAMA_API_KEY)

def _run_websearch(query):
    from websearch_tool import web_search
    return web_search(query=query, api_key=SEARCH_API_KEY, num_results=SEARCH_RESULTS, provider=SEARCH_PROVIDER)

def _run_rag(question):
    from rag_tool import query_rag
    return query_rag(question=question, ollama_host=OLLAMA_HOST, ollama_model=OLLAMA_MODEL,
                     api_key=OLLAMA_API_KEY, docs_dir=RAG_DOCS_DIR, index_dir=RAG_INDEX_DIR)

CITIES = ["mumbai","delhi","bangalore","bengaluru","hyderabad","chennai","kolkata","pune","ahmedabad","jaipur","lucknow","goa","surat","nagpur","indore","bhopal","patna","noida","gurgaon","london","new york","dubai","singapore","tokyo","paris"]

def extract_city(text):
    t = text.lower()
    for c in CITIES:
        if c in t: return c.title()
    for m in [" in "," for "," of "," mein "," ka "]:
        if m in t:
            w = t.split(m,1)[1].strip().split()[0].rstrip("?.!,")
            if len(w) > 2: return w.title()
    return None

def detect_tool(text):
    t = text.lower().strip()
    if any(k in t for k in ["weather","mausam","temperature","temp","barish","rain","forecast","वेदर","मौसम","तापमान","बारिश","टेंपरेचर"]):
        city = extract_city(t)
        if city:
            return "weather_tool", _run_weather(city)
        return "weather_tool", "Please tell me the city name."
    if any(k in t for k in ["time","date","day","today","samay","baje","clock","समय","तारीख","टाइम"]):
        # Exclude common conversational greetings that use "today" or "time"
        if any(greet in t for greet in ["how are you", "how are u", "who are you", "what are you", "how's it going", "aap kaise ho"]):
            pass # fall through to LLM chat
        else:
            return "datetime_tool", _run_datetime(text)
    if any(k in t for k in ["alarm","timer","remind","अलार्म"]):
        if any(k in t for k in ["list","show","all","my"]): return "alarm_tool", _run_list_alarms()
        m1 = re.search(r'(\d+)\s*(minute|min)', t)
        m2 = re.search(r'(\d+)\s*(hour|hr)', t)
        m3 = re.search(r'(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)', t)
        if m3:
            hr = int(m3.group(1))
            mn = int(m3.group(2))
            if "p" in m3.group(3).lower() and hr < 12: hr += 12
            if "a" in m3.group(3).lower() and hr == 12: hr = 0
            return "alarm_tool", _run_set_alarm(hour=hr, minute=mn)
        if m1: return "alarm_tool", _run_set_alarm(minutes=int(m1.group(1)))
        if m2: return "alarm_tool", _run_set_alarm(minutes=int(m2.group(1)) * 60)
        return "alarm_tool", "I can set alarms by minutes or hours, or by specific time like 'at 1:50 p.m.'."
    if any(k in t for k in ["news","headlines","khabar","samachar","न्यूज़","न्यूज","हैडलाइंस","खबर","समाचार"]):
        return "news_tool", _run_news(t)
    if any(k in t for k in ["email","mail","inbox","ईमेल"]):
        if any(k in t for k in ["send", "write", "भेजो", "draft"]): return "email_tool", _run_send_email(t)
        if any(k in t for k in ["count","how many"]): return "email_tool", _run_email_count()
        return "email_tool", _run_email_unread()
    if any(k in t for k in ["my document","my pdf","my book","my notes","my doc","document mein","from my doc","माय डॉक","डॉक्यूमेंट","मेरी फाइल","search my doc", "search in my"]):
        # Remove "search " if present so RAG gets the real query
        clean_q = re.sub(r"\b(search|find)\b"," ",t,flags=re.IGNORECASE).strip()
        return "rag_tool", _run_rag(clean_q)
    if any(k in t for k in ["calculate","plus","minus","times","divided","multiply","multiplied"]) or re.search(r'\d+\s*[\+\-\*\/x]\s*\d+', t):
        return "calculator_tool", _run_calculator(t)
    if any(k in t for k in ["search","google","find","lookup","सर्च","गूगल","price","rate","प्राइस","रेट","gold","गोल्ड","score","स्कोर"]):
        q = re.sub(r"\b(search|google|find|lookup|for|about)\b"," ",t,flags=re.IGNORECASE).strip()
        if q: return "websearch_tool", _run_websearch(q)
    if any(k in t for k in ["open file", "open pdf", "open document", "ओपन फाइल", "ओपन", "open"]):
        # basic extraction of filename
        filename = re.sub(r"\b(open|please|can you|the)\b", " ", t, flags=re.IGNORECASE).strip()
        if filename:
            return "file_opener_tool", _run_file_opener(filename)
        return "file_opener_tool", "Please specify the file name to open."
    return None, None

@observe_v4(name="summarize_search", as_type="generation")
def summarize_search(query, results, lang="en", history=None):
    """Use LLM to clean up noisy search results with conversation context."""
    from ollama import Client
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None
    client = Client(host=OLLAMA_HOST, headers=headers)
    
    messages = history or []
    # Identify the user's name from history if available to help the summarizer
    prompt = (
        f"CONTEXT: You are the same assistant as in the conversation history above. "
        f"The user just asked: '{query}'.\n"
        f"SEARCH RESULTS: {results}\n\n"
        f"INSTRUCTION: Use the Search Results to answer the factual part. "
        f"Match the user's language (if they asked in English, reply in English; if Hindi/Hinglish, reply in Hinglish). "
        f"Provide a concise 1-2 sentence answer."
    )
    
    temp_messages = list(messages)
    # Inject strict rules at the end to ensure they are followed
    temp_messages.append({"role": "system", "content": 
        "STRICT: Match the user's language. If they ask in English, reply in 100% English. "
        "VOICE: Do NOT use LaTeX, $, _, or math symbols. Use plain text only (e.g. H2O)."
    })
    temp_messages.append({"role": "user", "content": prompt})
    
    try:
        res = client.chat(model=OLLAMA_MODEL, messages=temp_messages)
        answer = res['message']['content'].strip()
        # Log usage to Langfuse
        if "prompt_eval_count" in res:
            obs.update_usage(res['prompt_eval_count'], res['eval_count'], model=OLLAMA_MODEL)
        return answer
    except Exception as e:
        return f"Error summarizing search: {e}"

@observe_v4(name="llm_chat", as_type="generation")
def llm_chat(text, lang="en", history=None):
    try:
        from ollama import Client
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None
        client = Client(host=OLLAMA_HOST, headers=headers)
        
        # history already contains the latest user message from handler()
        messages = list(history)
        # Inject strict formatting/language rules as a last-second reminder
        messages.append({"role": "system", "content": 
            "STRICT: Reply in 100% English if user spoke English. "
            "VOICE: No LaTeX or math symbols. Use plain text (e.g. H2O, 6CO2)."
        })
        
        r = client.chat(model=OLLAMA_MODEL, messages=messages, stream=True)
        for chunk in r:
            yield chunk['message']['content']
        
    except Exception as e:
        yield f"LLM error: {e}"

# ─── WebSocket ────────────────────────────────────────────
import websockets

@observe_v4(name="websocket_session")
async def handler(ws):
    print(f"🔌 Client connected")
    await ws.send(json.dumps({"type":"config","data":{"model":OLLAMA_MODEL,"calcModel":CALC_MODEL,"host":OLLAMA_HOST,"wakeWord":WAKE_WORD}}))
    
    history = load_memory()
    pending_email = None
    awaiting_spelling = False
    try:
        async for message in ws:
            try:
                msg = json.loads(message)
                if msg.get("type") == "speech":
                    text = msg.get("text","")
                    lang = msg.get("lang","en")
                    print(f"🎤 \"{text}\" [lang={lang}]")
                    
                    t = text.lower().strip()
                    
                    if awaiting_spelling:
                        from ollama import Client
                        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None
                        client = Client(host=OLLAMA_HOST, headers=headers)
                        prompt = f"The user just spelled out an email address letter by letter: '{text}'. Convert it into a valid email address string. Return ONLY the email address. Example: 's u f i y a n' -> 'sufiyan'. If domain is missing, add @gmail.com."
                        await ws.send(json.dumps({"type":"status","status":"processing"}))
                        res = await asyncio.to_thread(client.chat, model=OLLAMA_MODEL, messages=[{"role":"user", "content":prompt}])
                        new_email = res['message']['content'].strip().lower()
                        # Simple extraction if LLM adds chatter
                        m = re.search(r'[a-z0-9\._%+-]+@[a-z0-9\.-]+\.[a-z]{2,}', new_email)
                        if m: new_email = m.group()
                        
                        if pending_email:
                            pending_email['to'] = new_email
                            await ws.send(json.dumps({"type":"response","tool":"email_tool","text":f"Updated recipient to {new_email}. Should I send it now?"}))
                        else:
                            # Start new draft with this email
                            pending_email = {"to": new_email, "subject": "No Subject", "body": "No Body"}
                            await ws.send(json.dumps({"type":"response","tool":"email_tool","text":f"Got it: {new_email}. Please tell me the subject and message."}))
                        
                        awaiting_spelling = False
                        await ws.send(json.dumps({"type":"status","status":"idle"}))
                        continue

                    if pending_email and any(k in t for k in ["confirm", "yes", "send", "proceed", "haan", "bhejo"]):
                        from email_tool import send_email
                        await ws.send(json.dumps({"type":"status","status":"processing"}))
                        res = await asyncio.to_thread(send_email, to=pending_email['to'], subject=pending_email['subject'], body=pending_email['body'])
                        await ws.send(json.dumps({"type":"response","tool":"email_tool","text":res}))
                        pending_email = None
                        await ws.send(json.dumps({"type":"status","status":"idle"}))
                        continue
                    elif pending_email and any(k in t for k in ["cancel", "no", "don't", "stop", "na", "nahi"]):
                        awaiting_spelling = True
                        await ws.send(json.dumps({"type":"response","text":"Email draft paused. Please spell out the correct email address letter by letter."}))
                        continue

                    await ws.send(json.dumps({"type":"status","status":"processing"}))
                    tool, result_or_gen = await asyncio.to_thread(detect_tool, text)
                    
                    # Add user query to history (no more [LANG: ...] tags)
                    history.append({"role": "user", "content": text})
                    
                    if tool == "email_tool" and isinstance(result_or_gen, tuple):
                        pending_email, msg_text = result_or_gen
                        await ws.send(json.dumps({"type":"tool_detected","tool":tool}))
                        await ws.send(json.dumps({"type":"response","tool":tool,"text":msg_text}))
                        history.append({"role": "assistant", "content": msg_text})
                        await ws.send(json.dumps({"type":"status","status":"idle"}))
                        continue

                    if tool:
                        print(f"🔧 {tool}")
                        await ws.send(json.dumps({"type":"tool_detected","tool":tool}))
                        if hasattr(result_or_gen, '__iter__') and not isinstance(result_or_gen, str):
                            # It's a synchronous generator
                            def get_next():
                                try:
                                    return next(result_or_gen)
                                except StopIteration:
                                    return None
                            full_tool_res = ""
                            while True:
                                chunk = await asyncio.to_thread(get_next)
                                if chunk is None:
                                    break
                                full_tool_res += chunk
                                await ws.send(json.dumps({"type":"response_chunk","tool":tool,"text":chunk}))
                            await ws.send(json.dumps({"type":"response_end","tool":tool}))
                            history.append({"role": "assistant", "content": full_tool_res})
                        else:
                            final_text = str(result_or_gen)
                            # If it's a web search, summarize it!
                            if tool == "websearch_tool" and len(final_text) > 200:
                                await ws.send(json.dumps({"type":"status","status":"processing"}))
                                final_text = await asyncio.to_thread(summarize_search, text, final_text, lang, history)
                            
                            await ws.send(json.dumps({"type":"response","tool":tool,"text":final_text}))
                            history.append({"role": "assistant", "content": final_text})
                    else:
                        await ws.send(json.dumps({"type":"tool_detected","tool":"llm_chat"}))
                        gen = llm_chat(text, lang, history)
                        full_llm_res = ""
                        def get_next_llm():
                            try:
                                return next(gen)
                            except StopIteration:
                                return None
                        while True:
                            chunk = await asyncio.to_thread(get_next_llm)
                            if chunk is None:
                                break
                            full_llm_res += chunk
                            await ws.send(json.dumps({"type":"response_chunk","tool":"llm_chat","text":chunk}))
                        await ws.send(json.dumps({"type":"response_end","tool":"llm_chat"}))
                        history.append({"role": "assistant", "content": full_llm_res})
                    
                    if len(history) > 21:
                        history = [history[0]] + history[-20:]
                    save_memory(history)
                    await ws.send(json.dumps({"type":"status","status":"idle"}))
                elif msg.get("type") == "upload_doc":
                    name = msg.get("name")
                    data = msg.get("data")
                    import base64
                    os.makedirs(RAG_DOCS_DIR, exist_ok=True)
                    filepath = os.path.join(RAG_DOCS_DIR, name)
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(data))
                    print(f"📥 Saved uploaded document: {name}")
                    from rag_tool import build_index
                    await asyncio.to_thread(build_index, RAG_DOCS_DIR, RAG_INDEX_DIR)
                    await ws.send(json.dumps({"type":"response","tool":"rag_tool","text":f"Document {name} uploaded and indexed successfully!"}))
                elif msg.get("type") == "ingest_docs":
                    print("📚 Ingesting documents...")
                    from rag_tool import build_index
                    await asyncio.to_thread(build_index, RAG_DOCS_DIR, RAG_INDEX_DIR)
                    await ws.send(json.dumps({"type":"response","tool":"rag_tool","text":"Documents ingested successfully!"}))
                elif msg.get("type") == "ping":
                    await ws.send(json.dumps({"type":"pong"}))
            except Exception as e:
                traceback.print_exc()
                await ws.send(json.dumps({"type":"error","text":str(e)}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"🔌 Client disconnected")
        obs.flush()

async def main():
    init_db()
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  Aura Voice Agent · WebSocket Server     ║")
    print(f"  ║  Model: {OLLAMA_MODEL:<32s}║")
    print(f"  ║  Port:  ws://localhost:{WS_PORT:<18d}║")
    print(f"  ╚══════════════════════════════════════════╝\n")
    async with websockets.serve(handler, "0.0.0.0", WS_PORT, max_size=50_000_000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
