import { Mic, Play, X } from "lucide-react";
import { Visualizer } from "./Visualizer";
import { ToolGrid } from "./ToolGrid";
import { ObservationLog } from "./ObservationLog";
import { Terminal } from "./Terminal";

export function MainWorkspace() {
  return (
    <div className="flex-1 flex flex-col overflow-hidden min-w-0">
      {/* Tabs */}
      <div className="h-10 bg-sidebar-bg border-b border-border-main flex items-center px-2 gap-0.5 shrink-0">
        <Tab name="voice_agent.py" active />
        <Tab name="rag_tool.py" />
        <Tab name="weather_tool.py" />
      </div>

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Main editor area */}
        <div className="flex-1 flex flex-col overflow-y-auto scroll-thin border-r border-border-main">
          <div className="max-w-4xl w-full mx-auto px-8 py-10 space-y-10">
            {/* Header */}
            <div className="flex items-end justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 text-[11px] font-mono text-text-dim mb-3 uppercase tracking-widest">
                  <span className="size-1.5 rounded-full bg-success animate-pulse" />
                  Session live · 00:03:42
                </div>
                <h1 className="text-3xl font-semibold tracking-tight">
                  Aura<span className="text-text-dim">·01</span>{" "}
                  <span className="text-primary">Voice Agent</span>
                </h1>
                <p className="text-text-dim mt-2 text-sm">
                  Hindi · English · Hinglish · 9 tools registered ·{" "}
                  <span className="font-mono text-zinc-300">faster-whisper → llama3.2 → edge-tts</span>
                </p>
              </div>
              <div className="flex gap-2">
                <button className="px-3.5 py-2 bg-zinc-800/80 hover:bg-zinc-800 ring-1 ring-border-main rounded-md text-xs font-medium flex items-center gap-2 transition-colors">
                  <X className="size-3.5" /> Stop
                </button>
                <button className="px-3.5 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-xs font-semibold flex items-center gap-2 transition-colors">
                  <Play className="size-3.5 fill-current" /> Deploy agent
                </button>
              </div>
            </div>

            <Visualizer />

            {/* Mic control */}
            <div className="flex items-center justify-between rounded-xl border border-border-main bg-zinc-900/40 p-4">
              <div className="flex items-center gap-4">
                <button className="size-12 rounded-full bg-primary text-primary-foreground grid place-items-center shadow-lg shadow-primary/20 ring-4 ring-primary/10 active:scale-95 transition-transform">
                  <Mic className="size-5" strokeWidth={2} />
                </button>
                <div>
                  <div className="text-sm font-medium">Listening for "hey agent"</div>
                  <div className="text-[11px] font-mono text-text-dim mt-0.5">
                    Hold to push-to-talk · or tap to toggle continuous mode
                  </div>
                </div>
              </div>
              <div className="hidden sm:flex items-center gap-2">
                <Pill label="HI" />
                <Pill label="EN" active />
                <Pill label="Hinglish" active />
              </div>
            </div>

            <ToolGrid />

            {/* Integration map */}
            <section className="space-y-4">
              <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-dim">
                Where the frontend plugs in
              </h3>
              <div className="rounded-xl border border-border-main bg-zinc-900/40 overflow-hidden">
                <div className="grid sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-border-main">
                  <Cell n="01" title="Add transport in voice_agent.py" mono="ws = websockets.serve(handler, 0.0.0.0, 8765)" desc="Expose a WebSocket that streams transcripts + tool events." />
                  <Cell n="02" title="Point UI at the socket" mono="VITE_AGENT_WS=ws://localhost:8765" desc="Read it in src/lib/agent-client.ts and replace mocked events." />
                  <Cell n="03" title="Render tool outputs" mono="src/components/voice-agent/*" desc="Each tool already has a card here — feed real JSON in." />
                </div>
              </div>
            </section>
          </div>

          <Terminal />
        </div>

        <ObservationLog />
      </div>
    </div>
  );
}

function Tab({ name, active }: { name: string; active?: boolean }) {
  return (
    <div
      className={
        "px-3 py-1.5 text-[12px] font-mono flex items-center gap-2 rounded-t-md border-t-2 " +
        (active
          ? "bg-panel border-primary text-zinc-100"
          : "border-transparent text-text-dim hover:text-zinc-300")
      }
    >
      {name}
      <X className="size-3 opacity-50" />
    </div>
  );
}

function Pill({ label, active }: { label: string; active?: boolean }) {
  return (
    <span
      className={
        "text-[10px] px-2 py-0.5 rounded ring-1 font-mono " +
        (active ? "bg-primary/10 text-primary ring-primary/30" : "bg-zinc-900 text-text-dim ring-border-main")
      }
    >
      {label}
    </span>
  );
}

function Cell({ n, title, mono, desc }: { n: string; title: string; mono: string; desc: string }) {
  return (
    <div className="p-5">
      <div className="text-[10px] font-mono text-primary tracking-widest">{n}</div>
      <div className="mt-1 text-sm font-medium text-zinc-100">{title}</div>
      <code className="block mt-3 text-[11px] font-mono bg-black/40 ring-1 ring-border-main rounded-md p-2 text-zinc-300 break-all">
        {mono}
      </code>
      <p className="mt-2 text-[11px] text-text-dim leading-relaxed">{desc}</p>
    </div>
  );
}
