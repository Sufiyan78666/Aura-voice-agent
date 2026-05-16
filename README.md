# 🎙️ Aura Voice Agent

A premium, real-time voice-controlled AI assistant designed for a seamless, "Siri-like" experience on the web. Built with **React**, **Python**, and **Ollama**.

![Aura Dashboard](./dashboard_preview.png)

## ✨ Features

- **🧠 Persistent Memory**: Remembers your name, preferences, and past conversations across sessions.
- **🌐 Real-time Web Search**: Integrated with Tavily/Serper for up-to-date information (Stock prices, News, etc.).
- **📂 RAG (Document Intelligence)**: Chat with your local PDFs and documents using vector search.
- **📧 Email & Communication**: Draft and send emails using voice commands.
- **🧮 Smart Tool Routing**: Automatically detects when to use a Calculator, Weather tool, or Alarms.
- **🗣️ Multilingual Support**: Optimized for English, Hindi, and Hinglish with smart language matching.
- **📊 Observability**: Full execution tracing and token monitoring via Langfuse.

## 🛠️ Tech Stack

- **Frontend**: React, TanStack Start, TailwindCSS, Lucide Icons.
- **Backend**: Python (Async WebSocket Server).
- **AI Brain**: Ollama (Ollama Gemma 4 & Qwen 3.5).
- **STT/TTS**: Web Speech API / Faster-Whisper.

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/aura-voice-agent.git
cd aura-voice-agent

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # Or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Install Frontend dependencies
npm install
```

### 2. Configure Environment
Create a `.env` file in the root and add your keys:
```env
OLLAMA_MODEL=gemma4:31b-cloud
TAVILY_API_KEY=your_key_here
LANGFUSE_PUBLIC_KEY=your_key_here
LANGFUSE_SECRET_KEY=your_key_here
```

### 3. Run Locally
```bash
# Start Backend
python ws_server.py

# Start Frontend (In a new terminal)
npm run dev
```

## 📝 License
Apache 2.0 License. Feel free to use and modify!
