import { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic, MicOff, Power, PowerOff, Volume2, VolumeX,
  CloudSun, AlarmClock, FolderOpen, Newspaper, Globe, BookOpen,
  Mail, Calculator, Clock, Activity, Zap, Upload, Square,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type AgentStatus = "idle" | "listening" | "processing" | "speaking" | "ingesting";
type ToolStatus = "ready" | "active" | "offline";

interface LogEntry { id: string; timestamp: string; kind: "info"|"user"|"tool"|"agent"|"error"; text: string; sub?: string; }
interface ToolInfo { icon: LucideIcon; name: string; file: string; desc: string; status: ToolStatus; }
interface AgentConfig { model: string; calcModel: string; host: string; wakeWord: string; }

const DEFAULT_CONFIG: AgentConfig = { model: "gemma4:31b-cloud", calcModel: "qwen3.5:122b", host: "https://ollama.com", wakeWord: "boss" };

const TOOLS: ToolInfo[] = [
  { icon: CloudSun, name: "Weather", file: "weather_tool.py", desc: "Live conditions by city", status: "ready" },
  { icon: AlarmClock, name: "Alarms", file: "alarm_tool.py", desc: "Set & manage alarms", status: "ready" },
  { icon: FolderOpen, name: "File Opener", file: "file_opener_tool.py", desc: "Open local files", status: "ready" },
  { icon: Newspaper, name: "News", file: "news_tool.py", desc: "Headlines & articles", status: "ready" },
  { icon: Globe, name: "Web Search", file: "websearch_tool.py", desc: "Real-time browsing", status: "ready" },
  { icon: BookOpen, name: "RAG", file: "rag_tool.py", desc: "Query your documents", status: "ready" },
  { icon: Mail, name: "Email", file: "email_tool.py", desc: "Read & send email", status: "ready" },
  { icon: Calculator, name: "Calculator", file: "calculator_tool.py", desc: "Math & conversions", status: "ready" },
  { icon: Clock, name: "Date / Time", file: "datetime_tool.py", desc: "Current date & time", status: "ready" },
];

const TOOL_MAP: Record<string, string> = {
  weather_tool: "Weather", alarm_tool: "Alarms", datetime_tool: "Date / Time",
  news_tool: "News", email_tool: "Email", websearch_tool: "Web Search",
  rag_tool: "RAG", calculator_tool: "Calculator", file_opener_tool: "File Opener",
};

function timeStr() { return new Date().toLocaleTimeString("en-IN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }); }
function uid() { return Math.random().toString(36).slice(2, 10); }
function fmtTime(s: number) { const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60; return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`; }

export function Dashboard() {
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [isRunning, setIsRunning] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [sessionTime, setSessionTime] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tools, setTools] = useState(TOOLS);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [wsConnected, setWsConnected] = useState(false);
  const [audioLevels, setAudioLevels] = useState<number[]>(new Array(32).fill(5));
  const logEndRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<ReturnType<typeof setInterval>|null>(null);
  const wsRef = useRef<WebSocket|null>(null);
  const audioCtxRef = useRef<AudioContext|null>(null);
  const analyserRef = useRef<AnalyserNode|null>(null);
  const streamRef = useRef<MediaStream|null>(null);
  const rafRef = useRef<number>(0);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ttsQueueRef = useRef<string[]>([]);
  const ttsBufferRef = useRef<string>("");
  const isSpeakingRef = useRef<boolean>(false);
  const currentAgentLogIdRef = useRef<string | null>(null);
  const currentUttRef = useRef<SpeechSynthesisUtterance | null>(null);
  const lastMicTapRef = useRef<number>(0);

  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  useEffect(() => {
    if (isRunning) { sessionRef.current = setInterval(() => setSessionTime(t => t+1), 1000); }
    else { if (sessionRef.current) clearInterval(sessionRef.current); }
    return () => { if (sessionRef.current) clearInterval(sessionRef.current); };
  }, [isRunning]);

  const addLog = useCallback((kind: LogEntry["kind"], text: string, sub?: string) => {
    setLogs(prev => [...prev, { id: uid(), timestamp: timeStr(), kind, text, sub }]);
  }, []);

  const setToolActive = useCallback((toolKey: string, active: boolean) => {
    const uiName = TOOL_MAP[toolKey];
    if (!uiName) return;
    setTools(prev => prev.map(t => t.name === uiName ? { ...t, status: active ? "active" : "ready" } : t));
  }, []);

  // ─── WebSocket ──────────────────────────────────
  const connectWs = useCallback(() => {
    const ws = new WebSocket("wss://aura-voice-agent-production.up.railway.app");
    ws.onopen = () => { setWsConnected(true); addLog("info", "Connected to Python backend", "wss://aura-voice-agent-production.up.railway.app"); };
    ws.onclose = () => { setWsConnected(false); addLog("info", "Backend disconnected"); };
    ws.onerror = () => { addLog("error", "Cannot connect to backend", "Run: python ws_server.py"); };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "config") {
          setConfig(msg.data);
          addLog("info", `Model: ${msg.data.model}`, `Wake word: "${msg.data.wakeWord}"`);
        } else if (msg.type === "tool_detected") {
          addLog("tool", `tool_detect → ${msg.tool}`);
          setToolActive(msg.tool, true);
        } else if (msg.type === "response") {
          addLog("agent", msg.text);
          if (msg.tool) setToolActive(msg.tool, false);
          if (!isMuted) {
            ttsQueueRef.current.push(msg.text);
            processTTSQueue();
          } else {
            setStatus("idle");
          }
        } else if (msg.type === "response_chunk") {
          if (!currentAgentLogIdRef.current) {
            const newId = uid();
            currentAgentLogIdRef.current = newId;
            setLogs(prev => [...prev, { id: newId, timestamp: timeStr(), kind: "agent", text: msg.text }]);
          } else {
            setLogs(prev => prev.map(l => l.id === currentAgentLogIdRef.current ? { ...l, text: l.text + msg.text } : l));
          }
          if (!isMuted) queueTTS(msg.text);
        } else if (msg.type === "response_end") {
          currentAgentLogIdRef.current = null;
          if (msg.tool) setToolActive(msg.tool, false);
          if (!isMuted) {
            queueTTS("", true);
          } else {
            setStatus("idle");
          }
        } else if (msg.type === "status") {
          if (msg.status === "processing") setStatus("processing");
          else if (msg.status === "idle") {
            if (!isSpeakingRef.current && ttsQueueRef.current.length === 0) {
              setStatus("idle");
            }
          }
        } else if (msg.type === "alarm") {
             const label = msg.label || "Alarm";
             addLog("info", `🔔 Alarm: ${label}`);
            // Play alarm sound via Web Audio API — reuse existing context
             const ctx = audioCtxRef.current || new AudioContext();
             audioCtxRef.current = ctx;
             if (ctx.state === "suspended") ctx.resume();
          const playBeep = (time: number) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.frequency.value = 880;
            osc.type = "sine";
            gain.gain.setValueAtTime(0.8, time);
            gain.gain.exponentialRampToValueAtTime(0.001, time + 0.4);
            osc.start(time);
            osc.stop(time + 0.4);
          };
          // Play 3 beeps
          playBeep(ctx.currentTime);
          playBeep(ctx.currentTime + 0.5);
          playBeep(ctx.currentTime + 1.0);
          // Also speak via TTS
          if (!isMuted) {
            ttsQueueRef.current.push(`Alarm! ${label}!`);
            processTTSQueue();
          }
        } else if (msg.type === "error") {
          addLog("error", msg.text);
          setStatus("idle");
        }
      } catch {}
    };
    wsRef.current = ws;
  }, [addLog, setToolActive, isMuted]);

  // ─── TTS via browser ───────────────────────────
  const processTTSQueue = useCallback(() => {
    if (isSpeakingRef.current || ttsQueueRef.current.length === 0 || isMuted) return;
    const text = ttsQueueRef.current.shift();
    if (!text) return;
    isSpeakingRef.current = true;
    setStatus("speaking");
    
    // Strip emojis and markdown symbols so they aren't read aloud
    const cleanText = text.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDC00-\uDFFF])/g, '')
                          .replace(/[*#_~`]/g, ''); // Strip markdown symbols
    
    const utt = new SpeechSynthesisUtterance(cleanText);
    currentUttRef.current = utt;
    
    // Try to find a better Hindi voice if available (Google voices are usually better)
    const voices = window.speechSynthesis.getVoices();
    const hiVoice = voices.find(v => v.lang.includes("hi-IN") && v.name.includes("Google")) || 
                    voices.find(v => v.lang.includes("hi-IN"));
    
    if (hiVoice) utt.voice = hiVoice;
    utt.lang = "hi-IN";
    utt.rate = 1.0;
    utt.onend = () => {
      if (currentUttRef.current !== utt) return;
      isSpeakingRef.current = false;
      if (ttsQueueRef.current.length === 0) {
        setStatus("idle");
      } else {
        processTTSQueue();
      }
    };
    window.speechSynthesis.speak(utt);
  }, [isMuted]);

  const queueTTS = useCallback((chunk: string, end: boolean = false) => {
    ttsBufferRef.current += chunk;
    const sentences = ttsBufferRef.current.match(/[^.!?\n]+[.!?\n]+/g);
    if (sentences) {
      for (const s of sentences) {
        ttsQueueRef.current.push(s.trim());
      }
      ttsBufferRef.current = ttsBufferRef.current.substring(sentences.join("").length);
      processTTSQueue();
    }
    if (end && ttsBufferRef.current.trim().length > 0) {
      ttsQueueRef.current.push(ttsBufferRef.current.trim());
      ttsBufferRef.current = "";
    }
    if (end) {
      processTTSQueue();
      if (!isSpeakingRef.current && ttsQueueRef.current.length === 0) {
        setStatus("idle");
      }
    }
  }, [processTTSQueue]);

  const stopAudio = useCallback(() => {
    window.speechSynthesis.pause();
    window.speechSynthesis.cancel();
    currentUttRef.current = null;
    ttsQueueRef.current = [];
    ttsBufferRef.current = "";
    isSpeakingRef.current = false;
    setStatus("idle");
    addLog("info", "Audio stopped by user");
  }, [addLog]);

  // ─── Microphone Access ─────────────────────────
  const startMic = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
      audioCtxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      src.connect(analyser);
      analyserRef.current = analyser;
      const buf = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(buf);
        setAudioLevels(Array.from(buf).map(v => (v / 255) * 100));
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch { addLog("error", "Microphone access denied"); }
  }, [addLog]);

  const stopMic = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach(t => t.stop());
    audioCtxRef.current?.close();
    setAudioLevels(new Array(32).fill(5));
  }, []);

  // ─── Speech Recognition ────────────────────────
  const startListening = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { addLog("error", "Speech recognition not supported in this browser"); return; }
    const recognition = new SR();
    recognition.lang = "en-IN";
    recognition.interimResults = false; // ← back to false, simpler
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    let sent = false; // prevent double-sending
    let autoStopTimer: ReturnType<typeof setTimeout> | null = null;

    // Auto-stop after 10 seconds no matter what
    autoStopTimer = setTimeout(() => {
      try { recognition.stop(); } catch {}
      if (!sent) { setStatus("idle"); }
    }, 10000);

    const sendText = (text: string) => {
      if (sent) return;
      sent = true;
      if (autoStopTimer) clearTimeout(autoStopTimer);

      const t = text.toLowerCase().trim();
      addLog("user", `"${text}"`);

      if (t === "stop" || t === "stop it" || t === "shut up" || t === "ruk jao" || t === "quiet" || t === "silence") {
        stopAudio();
        return;
      }

      setStatus("processing");
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "speech", text, lang: "hinglish" }));
      } else {
        addLog("error", "Backend not connected");
        setStatus("idle");
      }
    };

    recognition.onresult = (e: any) => {
      // Grab the best result immediately
      let text = "";
      for (let i = 0; i < e.results.length; i++) {
        if (e.results[i].isFinal || e.results[i][0].transcript) {
          text += e.results[i][0].transcript;
        }
      }
      if (text.trim()) {
        sendText(text.trim());
        try { recognition.stop(); } catch {}
      }
    };

    recognition.onend = () => {
      if (autoStopTimer) clearTimeout(autoStopTimer);
      if (!sent) setStatus("idle");
    };

    recognition.onerror = (e: any) => {
      if (autoStopTimer) clearTimeout(autoStopTimer);
      if (e.error !== "aborted" && e.error !== "no-speech") {
        addLog("error", `Speech error: ${e.error}`);
      }
      if (!sent) setStatus("idle");
    };

    recognition.start();
    recognitionRef.current = recognition;
  }, [addLog, stopAudio]);

  // ─── Start/Stop Agent ──────────────────────────
  const handleStart = useCallback(() => {
    setIsRunning(true); setSessionTime(0); setLogs([]); setStatus("idle");
    setTools(TOOLS.map(t => ({ ...t, status: "ready" as ToolStatus })));
    addLog("info", "Agent starting...");
    connectWs();
    startMic();
    setTimeout(() => addLog("info", "STT engine ready", "Web Speech API · hi-IN"), 500);
    setTimeout(() => addLog("info", `All ${TOOLS.length} tools registered`, "Ready for voice commands"), 1000);
  }, [addLog, connectWs, startMic]);

  const handleStop = useCallback(() => {
    setIsRunning(false); setStatus("idle");
    wsRef.current?.close(); stopMic();
    recognitionRef.current?.abort();
    window.speechSynthesis.cancel();
    addLog("info", "Agent stopped");
  }, [addLog, stopMic]);

  // ─── Mic Toggle ────────────────────────────────
  const handleMicToggle = useCallback(() => {
    if (!isRunning) return;
    const now = Date.now();
    if (now - lastMicTapRef.current < 1000) return; // debounce 1 second
    lastMicTapRef.current = now;
    if (status === "speaking") {
      window.speechSynthesis.cancel();
      setStatus("idle");
      addLog("info", "Speech interrupted");
      return;
    }
    if (status === "listening") {
      recognitionRef.current?.stop();
      setStatus("idle");
    } else {
      setStatus("listening");
      addLog("info", "Listening...", "Speak now");
      startListening();
    }
  }, [isRunning, status, addLog, startListening]);

  const handleIngest = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ingest_docs" }));
      setStatus("ingesting");
      addLog("info", "Syncing documents...");
    } else {
      addLog("error", "Backend not connected");
    }
  }, [addLog]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1];
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "upload_doc", name: file.name, data: base64 }));
        setStatus("ingesting");
        addLog("info", `Uploading ${file.name}...`);
      } else {
        addLog("error", "Backend not connected");
      }
    };
    reader.readAsDataURL(file);
    e.target.value = ""; // reset
  }, [addLog]);

  // Cleanup
  useEffect(() => { return () => { wsRef.current?.close(); stopMic(); }; }, [stopMic]);

  const isActive = status === "listening" || status === "speaking";

  return (
    <div className="h-screen w-full flex flex-col bg-background text-foreground overflow-hidden">
      {/* Top Bar */}
      <header className="h-14 shrink-0 border-b border-border-main bg-panel/80 backdrop-blur-md flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className={cn("size-3 rounded-full transition-colors", isRunning ? "bg-success status-blink" : "bg-zinc-600")} />
          <h1 className="text-lg font-semibold tracking-tight">Aura<span className="text-text-dim font-normal">·01</span> <span className="text-primary">Voice Agent</span></h1>
          <span className="text-xs text-text-dim font-mono ml-2">Hindi · English · Hinglish</span>
        </div>
        <div className="flex items-center gap-3">
          {isRunning && <span className="text-xs font-mono text-text-dim px-3 py-1 rounded-full bg-secondary">{fmtTime(sessionTime)}</span>}
          <span className={cn("text-[10px] font-mono px-2 py-0.5 rounded-full", wsConnected ? "bg-success/15 text-success" : "bg-zinc-800 text-zinc-500")}>
            {wsConnected ? "● connected" : "○ offline"}
          </span>
        </div>
      </header>

      <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-0">
        {/* Main Panel */}
        <main className="flex-1 flex flex-col overflow-hidden p-4 md:p-6 gap-4 md:gap-5">
          {/* Controls */}
          <div className="flex items-center justify-between gap-4 shrink-0">
            <div className="flex items-center gap-3">
              {!isRunning ? (
                <button onClick={handleStart} className="px-5 py-2.5 bg-success hover:bg-success/90 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95 cursor-pointer shadow-lg shadow-success/20">
                  <Power className="size-4" /> Start Agent
                </button>
              ) : (
                <div className="flex gap-2">
                  <button onClick={handleStop} className="px-5 py-2.5 bg-destructive hover:bg-destructive/90 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95 cursor-pointer shadow-lg shadow-destructive/20">
                    <PowerOff className="size-4" /> Stop Agent
                  </button>
                  <button onClick={handleIngest} disabled={status === "ingesting"} className="px-5 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95 cursor-pointer hidden md:flex">
                    <BookOpen className="size-4" /> Sync
                  </button>
                  <button onClick={() => fileInputRef.current?.click()} disabled={status === "ingesting"} className="px-5 py-2.5 bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95 cursor-pointer">
                    <Upload className="size-4" /> Upload Doc
                  </button>
                  <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.md,.docx,.pptx" />
                </div>
              )}
              <button onClick={() => setIsMuted(m => !m)} className={cn("p-2.5 rounded-lg transition-all cursor-pointer", isMuted ? "bg-destructive/15 text-destructive" : "bg-secondary text-text-dim hover:text-foreground")}>
                {isMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
              </button>
            </div>
            <StatusPill status={status} isRunning={isRunning} />
          </div>

          {/* Visualizer + Mic */}
          <div className="glass-card rounded-2xl p-8 flex flex-col items-center gap-6 shrink-0">
            {/* Audio Bars */}
            <div className="w-full h-20 md:h-28 relative rounded-xl overflow-hidden bg-black/20">
              <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)", backgroundSize: "20px 20px" }} />
              <div className="absolute inset-0 grid place-items-center">
                <div className="flex items-end gap-[3px] h-20">
                  {audioLevels.map((h, i) => (
                    <div key={i} className={cn("w-[3px] rounded-full transition-all duration-75", isActive ? status === "listening" ? "bg-success" : "bg-primary" : "bg-zinc-700")}
                      style={{ height: `${Math.max(isActive ? h : 5, 3)}%`, opacity: isActive ? 0.4 + (h/100)*0.6 : 0.3 }} />
                  ))}
                </div>
              </div>
              <div className="absolute bottom-2 left-3 flex items-center gap-2">
                <span className={cn("size-1.5 rounded-full", isActive ? "bg-success status-blink" : "bg-zinc-600")} />
                <span className="text-[9px] font-mono text-text-dim uppercase tracking-widest">{isActive ? "Audio active · 16 kHz" : "Audio paused"}</span>
              </div>
            </div>

            {/* Mic Button & Stop Audio */}
            <div className="flex items-center gap-4">
              <button onClick={handleMicToggle} disabled={!isRunning}
                className={cn("size-16 md:size-20 rounded-full grid place-items-center transition-all duration-300 cursor-pointer",
                  !isRunning && "opacity-40 cursor-not-allowed",
                  status === "listening" ? "bg-success text-white orb-listening glow-success scale-110" : "bg-primary text-primary-foreground orb-pulse glow-primary hover:scale-105 active:scale-95")}>
                {status === "listening" ? <MicOff className="size-8" strokeWidth={1.8} /> : <Mic className="size-8" strokeWidth={1.8} />}
              </button>
              
              {status === "speaking" && (
                <button onClick={stopAudio}
                  className="size-14 rounded-full bg-destructive text-white grid place-items-center transition-all duration-300 cursor-pointer hover:scale-105 active:scale-95 shadow-lg shadow-destructive/20 animate-in fade-in zoom-in">
                  <Square className="size-6" fill="currentColor" />
                </button>
              )}
            </div>
            <p className="text-xs text-text-dim font-mono text-center">
              {!isRunning ? "Start the agent to begin" : status === "listening" ? "Listening... speak now" : status === "processing" ? "Processing..." : status === "speaking" ? "Speaking... (Tap to stop)" : status === "ingesting" ? "Syncing Documents..." : `Tap mic or say "${config.wakeWord}"`}
            </p>
          </div>

          {/* Tools Grid */}
          <div className="flex-1 overflow-y-auto scroll-thin min-h-0">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-dim mb-3 flex items-center gap-2">
              <Zap className="size-3.5" /> Registered Tools <span className="ml-auto font-mono">{tools.length} loaded</span>
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
              {tools.map(t => <ToolCard key={t.name} tool={t} />)}
            </div>
          </div>
        </main>

        {/* Right: Observation Log */}
        <aside className="w-full md:w-96 bg-panel border-t md:border-t-0 md:border-l border-border-main flex flex-col shrink-0 max-h-64 md:max-h-none">
          <div className="h-12 flex items-center justify-between px-5 border-b border-border-main shrink-0">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-text-dim flex items-center gap-2"><Activity className="size-3.5" /> Observation Log</h3>
            {isRunning && <span className="flex items-center gap-1.5 text-[10px] font-mono text-success"><span className="size-1.5 rounded-full bg-success status-blink" /> live</span>}
          </div>
          <div className="flex-1 overflow-y-auto scroll-thin px-4 py-4 space-y-1">
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-text-dim">
                <Activity className="size-8 mb-3 opacity-30" />
                <p className="text-xs text-center">No activity yet.<br/>Start the agent to begin.</p>
              </div>
            ) : logs.map(log => <LogLine key={log.id} entry={log} />)}
            <div ref={logEndRef} />
          </div>
          <div className="border-t border-border-main p-4 space-y-2 text-xs shrink-0">
            <CfgRow label="Wake Word" value={config.wakeWord} />
            <CfgRow label="STT" value="Web Speech API (hi-IN)" />
            <CfgRow label="TTS" value="Browser Speech Synthesis" />
            <CfgRow label="LLM" value={`ollama · ${config.model}`} />
          </div>
        </aside>
      </div>
    </div>
  );
}

function StatusPill({ status, isRunning }: { status: AgentStatus; isRunning: boolean }) {
  const map = { idle: { l: "Idle", c: "bg-zinc-600/20 text-zinc-400 ring-zinc-600/30" }, listening: { l: "Listening", c: "bg-success/15 text-success ring-success/30" }, processing: { l: "Processing", c: "bg-warning/15 text-warning ring-warning/30" }, speaking: { l: "Speaking", c: "bg-primary/15 text-primary ring-primary/30" }, ingesting: { l: "Ingesting", c: "bg-purple-500/15 text-purple-400 ring-purple-500/30" } };
  const v = isRunning ? map[status] : { l: "Offline", c: "bg-zinc-800 text-zinc-500 ring-zinc-700" };
  return <span className={cn("text-xs font-mono px-3 py-1.5 rounded-full ring-1 flex items-center gap-2", v.c)}>{v.l}</span>;
}

function ToolCard({ tool }: { tool: ToolInfo }) {
  const sc: Record<ToolStatus,string> = { ready: "bg-success/10 text-success ring-success/20", active: "bg-primary/10 text-primary ring-primary/30", offline: "bg-zinc-500/10 text-zinc-500 ring-zinc-500/20" };
  return (
    <div className={cn("group p-3.5 rounded-xl glass-card transition-all duration-300 hover:border-primary/30 hover:scale-[1.02]", tool.status === "active" && "border-primary/40 glow-primary")}>
      <div className="flex items-start justify-between">
        <div className={cn("size-9 rounded-lg grid place-items-center", tool.status === "active" ? "bg-primary/15" : "bg-black/30 ring-1 ring-border-main")}>
          <tool.icon className={cn("size-4", tool.status === "active" ? "text-primary" : "text-zinc-400")} strokeWidth={1.6} />
        </div>
        <span className={cn("text-[9px] font-mono px-1.5 py-0.5 rounded ring-1 uppercase", sc[tool.status])}>{tool.status}</span>
      </div>
      <h4 className="mt-2.5 text-sm font-medium">{tool.name}</h4>
      <p className="text-[11px] text-text-dim mt-0.5">{tool.desc}</p>
    </div>
  );
}

function LogLine({ entry }: { entry: LogEntry }) {
  const kc: Record<string,string> = { info: "text-success", user: "text-primary", tool: "text-warning", agent: "text-emerald-300", error: "text-destructive" };
  return (
    <div className="fade-in font-mono text-[11px] leading-relaxed py-1.5 border-b border-border-main/30 last:border-0">
      <span className={kc[entry.kind] || "text-text-dim"}>[{entry.timestamp}]</span>{" "}
      <span className={entry.kind === "user" ? "italic text-zinc-100" : "text-zinc-300"}>{entry.text}</span>
      {entry.sub && <div className="text-zinc-500 ml-5 mt-0.5 text-[10px]">{entry.sub}</div>}
    </div>
  );
}

function CfgRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between"><span className="text-text-dim">{label}</span><span className="font-mono text-zinc-200">{value}</span></div>;
}
