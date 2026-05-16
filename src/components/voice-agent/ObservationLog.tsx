import { CloudSun } from "lucide-react";

interface LogLine {
  t: string;
  kind: "info" | "user" | "tool" | "agent";
  text: string;
  sub?: string;
}

const lines: LogLine[] = [
  { t: "14:22:01", kind: "info", text: "Agent initialized · model = llama3.2", sub: "Wake word: 'hey agent'" },
  { t: "14:22:05", kind: "info", text: "Loading rag_tool.py", sub: "Embedding index verified · 1,240 docs" },
  { t: "14:22:09", kind: "info", text: "All 9 tools registered" },
  { t: "14:23:45", kind: "user", text: '"Mumbai ka weather batao aur 7 baje alarm laga do."' },
  { t: "14:23:46", kind: "tool", text: "tool_detect → weather_tool" },
  { t: "14:23:46", kind: "tool", text: "tool_detect → alarm_tool" },
  { t: "14:23:47", kind: "agent", text: "Streaming TTS · edge-tts hi-IN-MadhurNeural" },
];

const kindColor = {
  info: "text-success",
  user: "text-primary",
  tool: "text-amber-400",
  agent: "text-emerald-300",
};

export function ObservationLog() {
  return (
    <aside className="w-80 bg-sidebar-bg border-l border-border-main flex flex-col shrink-0">
      <div className="h-12 flex items-center justify-between px-4 border-b border-border-main">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-text-dim">Observation Log</h3>
        <span className="text-[10px] font-mono text-text-dim">live</span>
      </div>

      <div className="flex-1 overflow-y-auto scroll-thin px-4 py-4 font-mono text-[11px] leading-relaxed space-y-3">
        {lines.map((l, i) => (
          <div key={i}>
            <span className={kindColor[l.kind]}>[{l.t}]</span>{" "}
            <span className={l.kind === "user" ? "italic text-zinc-100" : "text-zinc-300"}>{l.text}</span>
            {l.sub && <div className="text-zinc-500 ml-5 mt-0.5">{l.sub}</div>}
          </div>
        ))}

        <div className="mt-2 rounded-lg ring-1 ring-border-main bg-zinc-900/60 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-widest text-text-dim">weather_tool · output</span>
            <span className="size-1.5 rounded-full bg-success" />
          </div>
          <div className="flex items-center gap-3">
            <div className="size-10 rounded-lg bg-zinc-950 ring-1 ring-border-main grid place-items-center">
              <CloudSun className="size-5 text-amber-300" strokeWidth={1.6} />
            </div>
            <div>
              <div className="font-sans text-xl text-zinc-100 leading-none">28°C</div>
              <div className="text-[11px] text-text-dim mt-1">Mumbai · partly cloudy · humidity 71%</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg ring-1 ring-border-main bg-zinc-900/60 p-3">
          <div className="text-[10px] uppercase tracking-widest text-text-dim mb-1.5">alarm_tool · output</div>
          <div className="text-zinc-200 text-[12px]">Alarm set · tomorrow 07:00 AM</div>
          <div className="text-text-dim text-[11px] mt-0.5">written to alarms.json</div>
        </div>
      </div>

      <div className="border-t border-border-main p-4 space-y-3 text-[11px]">
        <Row k="Wake word" v="hey agent" />
        <Row k="STT" v="faster-whisper · medium" />
        <Row k="TTS" v="edge-tts · hi-IN" />
        <Row k="LLM" v="ollama · llama3.2" />
      </div>
    </aside>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-text-dim">{k}</span>
      <span className="font-mono text-zinc-200">{v}</span>
    </div>
  );
}
