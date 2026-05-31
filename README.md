# 🎙️ Aura Voice Agent


A premium, real-time voice-controlled AI assistant for the web. Seamless "Siri-like" experience with Hindi, English, and Hinglish support. Built with React (TanStack Start), Python, and Ollama Cloud.

👉 **Live Demo:** [aura-voice-agent.sufiyankhan7339.workers.dev](https://aura-voice-agent.sufiyankhan7339.workers.dev/)

---
![Aura Dashboard](./dashboard_preview.png)

## 🖥️ Dashboard & Interface

The dashboard provides:

- 🎙️ **Voice Visualizer**: Real-time audio input display.
- 🛠️ **ToolGrid**: Status for all registered tools (Weather, Alarms, File Opener, News, Web Search, RAG, Email, Calculator, Date/Time).
- 📜 **Observation Log**: Live agent, tool, and user events.
- 🗂️ **File Explorer**: Visualizes backend tool files and data.
- 🖥️ **Terminal**: Shows backend logs and tool registration.
- ⚙️ **Status Bar**: Shows environment, connection, and agent state.

## ✨ Features

- 🧠 **Persistent Memory**: Remembers your name, preferences, and conversation history (JSON file or PostgreSQL).
- 👤 **User Profile**: Auto-detects and stores your name.
- 🌐 **Web Search**: Real-time search via Tavily or Serper APIs.
- 📂 **RAG (Document Intelligence)**: Chat with your PDFs and docs using HuggingFace/ChromaDB.
- 📧 **Email**: Read/send emails via Gmail API (OAuth2).
- ⏰ **Alarms**: Set/list/cancel alarms by voice (persistent, PostgreSQL-backed).
- 🧮 **Calculator**: Math and unit calculations, LLM fallback for parsing.
- 🗣️ **Multilingual**: English, Hindi, Hinglish with language tag detection.
- 📊 **Observability**: Execution tracing and token monitoring (Langfuse).

## 🛠️ Tech Stack

| Layer         | Technology |
|-------------- |-----------|
| **Frontend**  | React (TanStack Start), TailwindCSS, Lucide Icons |
| **Backend**   | Python (WebSocket server, tool modules) |
| **Database**  | PostgreSQL (alarms, memory, docs) or local JSON |
| **AI Models** | Ollama Cloud (Gemma 4, Qwen 3.5), HuggingFace embeddings |
| **STT**       | faster-whisper (offline), Web Speech API |
| **TTS**       | edge-tts, browser Speech Synthesis |
| **Email**     | Gmail API (OAuth2) |
| **Web Search**| Tavily API, Serper API |
| **Observability** | Langfuse |

## 🧩 Registered Tools

| Tool         | File                | Description                                 |
|--------------|---------------------|---------------------------------------------|
| Weather      | weather_tool.py     | Live weather by city                        |
| Alarms       | alarm_tool.py       | Set/list/cancel alarms (persistent)         |
| File Opener  | file_opener_tool.py | Open/close local files by name              |
| News         | news_tool.py        | Latest headlines (Google News RSS)          |
| Web Search   | websearch_tool.py   | Real-time search (Tavily/Serper)            |
| RAG          | rag_tool.py         | Query and rebuild document index            |
| Email        | email_tool.py       | Read/search/send mail (Gmail API)           |
| Calculator   | calculator_tool.py  | Math/unit calculations                      |
| Date/Time    | datetime_tool.py    | Current date, time, weekday                 |

---

## 🚀 Architecture

```mermaid
flowchart TD
	subgraph Browser
		A[React Frontend] -- WebSocket --> B[Python Backend]
		A -- REST/WS --> B

	# 🎙️ Aura Voice Agent

	A premium, real-time voice-controlled AI assistant for the web. Seamless "Siri-like" experience with Hindi, English, and Hinglish support. Built with React (TanStack Start), Python, and Ollama Cloud.

	👉 **Live Demo:** [aura-voice-agent.sufiyankhan7339.workers.dev](https://aura-voice-agent.sufiyankhan7339.workers.dev/)

	---
	![Aura Dashboard](./dashboard_preview.png)

	## 🖥️ Dashboard & Interface

	The dashboard provides:

	- 🎙️ **Voice Visualizer**: Real-time audio input display.
	- 🛠️ **ToolGrid**: Status for all registered tools (Weather, Alarms, File Opener, News, Web Search, RAG, Email, Calculator, Date/Time).
	- 📜 **Observation Log**: Live agent, tool, and user events.
	- ⚙️ **Status Bar**: Shows environment, connection, and agent state.

	## ✨ Features

	- 🧠 **Persistent Memory**: Remembers your name, preferences, and conversation history (PostgreSQL via Supabase).
	- 👤 **User Profile**: Auto-detects and permanently stores your name across sessions.
	- 🌐 **Web Search**: Real-time search via Tavily API.
	- 📂 **RAG (Document Intelligence)**: Upload and chat with your PDFs using HuggingFace embeddings and ChromaDB. Documents persist in PostgreSQL.
	- 📧 **Email**: Read/send emails via Gmail API (OAuth2). No SMTP — works on cloud.
	- ⏰ **Alarms**: Set/list/cancel alarms by voice. Persistent in PostgreSQL, fires browser beep + TTS.
	- 🧮 **Calculator**: Math and unit calculations via LLM.
	- 🗣️ **Multilingual**: English, Hindi, Hinglish with smart language detection.
	- 📊 **Observability**: Execution tracing and token monitoring via Langfuse.

	## 🛠️ Tech Stack

	| Layer | Technology |
	|-------|-----------|
	| **Frontend** | React (TanStack Start), TailwindCSS, Lucide Icons |
	| **Frontend Hosting** | Cloudflare Pages |
	| **Backend** | Python (Async WebSocket Server) |
	| **Backend Hosting** | Google Cloud Run |
	| **Database** | Supabase PostgreSQL (memory, alarms, docs, user profile) |
	| **AI Models** | Ollama Cloud (Gemma 4 31B, Qwen 3.5 122B) |
	| **Embeddings** | HuggingFace BAAI/bge-small-en-v1.5 |
	| **STT** | Web Speech API (hi-IN) |
	| **TTS** | Browser Speech Synthesis |
	| **Email** | Gmail API (OAuth2) |
	| **Web Search** | Tavily API |
	| **Observability** | Langfuse |

	## 🧩 Registered Tools

	| Tool | File | Description |
	|------|------|-------------|
	| Weather | weather_tool.py | Live weather by city |
	| Alarms | alarm_tool.py | Set/list/cancel alarms (persistent, PostgreSQL) |
	| File Opener | file_opener_tool.py | Open local files by name |
	| News | news_tool.py | Latest headlines (Google News RSS) |
	| Web Search | websearch_tool.py | Real-time search (Tavily) |
	| RAG | rag_tool.py | Query uploaded documents (HuggingFace + ChromaDB) |
	| Email | email_tool.py | Read/send mail via Gmail API |
	| Calculator | calculator_tool.py | Math/unit calculations |
	| Date/Time | datetime_tool.py | Current date, time, weekday (IST) |

	---

	## 🚀 Architecture
	```

	User Browser
	│
	├──► Cloudflare Pages (React Frontend)
	│         │
	│         └──► WebSocket (wss://)
	│                    │
	└──────────────► Google Cloud Run (Python Backend)
	│
	├──► Supabase PostgreSQL
	│     ├── memory (conversation history)
	│     ├── user_profile (name, preferences)
	│     ├── alarms (persistent alarms)
	│     └── documents (uploaded PDFs)
	│
	├──► Ollama Cloud (LLM)
	├──► Tavily API (Web Search)
	├──► Gmail API (Email)
	└──► Langfuse (Observability)

	```
	---

	## 🚦 Quick Start (Local Development)

	### 1. Clone & Install

	```bash
	git clone https://github.com/Sufiyan78666/Aura-voice-agent.git
	cd Aura-voice-agent

	# Python backend
	python -m venv venv
	venv\Scripts\activate  # Windows
	pip install -r requirements.txt

	# Frontend
	npm install
	```

	### 2. Configure Environment

	Create a `.env` file in the root:

	```env
	# Ollama Cloud
	OLLAMA_HOST=https://ollama.com
	OLLAMA_API_KEY=your_key_here
	OLLAMA_MODEL=gemma4:31b-cloud
	CALC_MODEL=qwen3.5:122b

	# Database (Supabase)
	DATABASE_URL=postgresql://postgres.xxxx:password@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres

	# Web Search
	SEARCH_PROVIDER=tavily
	TAVILY_API_KEY=your_key_here

	# Email (Gmail API)
	EMAIL_ADDRESS=your@gmail.com
	GMAIL_TOKEN={"token": "...", "refresh_token": "..."}

	# RAG
	RAG_EMBED_BACKEND=huggingface
	RAG_EMBED_MODEL=BAAI/bge-small-en-v1.5
	RAG_DOCS_DIR=./rag_docs
	RAG_INDEX_DIR=./rag_index
	```

	### 3. Run Locally

	```bash
	# Start Backend
	python ws_server.py

	# Start Frontend (in a new terminal)
	npm run dev
	```

	---

	## ☁️ Production Deployment

	### Backend (Google Cloud Run)
	1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install
	2. Run `gcloud init` and select your project
	3. Deploy: `gcloud run deploy aura-voice-agent --source . --region us-central1 --platform managed --allow-unauthenticated --port 8765 --memory 2Gi --timeout 3600`
	4. Set environment variables via `gcloud run services update` or `--env-vars-file`

	### Database (Supabase)
	1. Create free project at https://supabase.com
	2. Get Session Pooler connection string from Connect → Direct → Session pooler
	3. Set as `DATABASE_URL` in Cloud Run env vars
	4. Tables are created automatically on first startup

	### Frontend (Cloudflare Pages)
	1. Connect your GitHub repo to Cloudflare Pages
	2. Build command: `npm run build`
	3. Output directory: `dist`
	4. Auto-deploys on every `git push`

	---

	## 📝 License

	Apache 2.0 License. Feel free to use and modify!