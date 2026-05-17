# 🎙️ Aura Voice Agent

A premium, real-time voice-controlled AI assistant designed for a seamless, "Siri-like" experience on the web. Built with React, Python, PostgreSQL, and Ollama Cloud.

---
![Aura Dashboard](./dashboard_preview.png)
## 🖥️ Dashboard & Interface

The Aura Dashboard provides a real-time overview of the agent's state and capabilities:

- 🎙️ **Core Interaction**: Large central voice visualization and a "Start Agent" toggle.
- 🛠️ **Registered Tools**: Real-time status indicators for all integrated tools (Weather, Alarms, RAG, Email, etc.).
- 📜 **Observation Log**: Live telemetry and execution tracing of the agent's thoughts and actions.
- ⚙️ **System Info**: Quick glance at the current stack (Web Speech API, Gemma 4, Qwen 3.5).

---

## ✨ Features

- 🧠 **Persistent Memory**: Remembers your name, preferences, and full conversation history across sessions using PostgreSQL.
- 👤 **User Profile**: Automatically detects and permanently stores your name — survives restarts and redeployments.
- 🌐 **Real-time Web Search**: Integrated with Tavily for up-to-date information (gold prices, news, stock prices, etc.).
- 📂 **RAG (Document Intelligence)**: Upload and chat with your PDFs using HuggingFace embeddings and ChromaDB vector search. Documents are stored in PostgreSQL and restored on every restart.
- 📧 **Email & Communication**: Read and send emails using voice commands via Gmail API (OAuth2).
- ⏰ **Smart Alarms**: Set alarms by voice — fires browser beep + TTS notification. Alarm state persists in PostgreSQL.
- 🧮 **Smart Tool Routing**: Automatically detects when to use Calculator, Weather, Alarms, News, Web Search, or RAG.
- 🗣️ **Multilingual Support**: Optimized for English, Hindi, and Hinglish with smart language matching.
- 📊 **Observability**: Full execution tracing and token monitoring via Langfuse.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React, TanStack Start, TailwindCSS, Lucide Icons |
| **Frontend Hosting** | Cloudflare Pages |
| **Backend** | Python (Async WebSocket Server) |
| **Backend Hosting** | Railway |
| **Database** | PostgreSQL (Railway) — memory, alarms, documents, user profile |
| **AI Brain** | Ollama Cloud (Gemma 4 31B, Qwen 3.5 122B) |
| **Embeddings** | HuggingFace BAAI/bge-small-en-v1.5 |
| **STT** | Web Speech API (hi-IN) |
| **TTS** | Browser Speech Synthesis |
| **Email** | Gmail API (OAuth2) |
| **Web Search** | Tavily API |
| **Observability** | Langfuse |

---

## 🚀 Deployment Architecture
User Browser
│
├──► Cloudflare Pages (React Frontend)
│         │
│         └──► WebSocket (wss://)
│                    │
└──────────────► Railway (Python Backend)
│
├──► PostgreSQL (Railway)
│     ├── memory (conversation history)
│     ├── user_profile (name, preferences)
│     ├── alarms (persistent alarms)
│     └── documents (uploaded PDFs)
│
├──► Ollama Cloud (LLM)
├──► Tavily API (Web Search)
├──► Gmail API (Email)
└──► Langfuse (Observability)


---

## 🚀 Quick Start (Local Development)

### 1. Clone & Install

```bash
git clone https://github.com/Sufiyan78666/Aura-voice-agent.git
cd Aura-voice-agent

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Install Frontend dependencies
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

# Database
DATABASE_URL=postgresql://user:password@host:5432/railway

# Web Search
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=your_key_here

# Email (Gmail API)
EMAIL_ADDRESS=your@gmail.com
GMAIL_TOKEN={"token": "...", "refresh_token": "..."}

# Observability
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
LANGFUSE_BASE_URL=https://cloud.langfuse.com

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

### Backend (Railway)
1. Connect your GitHub repo to Railway
2. Add PostgreSQL database — Railway auto-links `DATABASE_URL`
3. Set all environment variables in Railway Variables tab
4. Railway auto-deploys on every `git push`

### Frontend (Cloudflare Pages)
1. Connect your GitHub repo to Cloudflare Pages
2. Build command: `npm run build`
3. Output directory: `dist`
4. Auto-deploys on every `git push`

---

## 📝 License

Apache 2.0 License. Feel free to use and modify!