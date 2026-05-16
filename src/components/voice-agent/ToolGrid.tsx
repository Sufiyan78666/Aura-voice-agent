import {
  CloudSun, AlarmClock, FolderOpen, Newspaper, Globe, BookOpen,
  Mail, Calculator, Clock, type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Status = "ready" | "active" | "offline";

interface Tool {
  icon: LucideIcon;
  name: string;
  file: string;
  desc: string;
  status: Status;
}

const tools: Tool[] = [
  { icon: CloudSun, name: "Weather", file: "weather_tool.py", desc: "Live conditions and forecast by city.", status: "ready" },
  { icon: AlarmClock, name: "Alarms", file: "alarm_tool.py", desc: "Set, list and cancel scheduled alarms.", status: "active" },
  { icon: FolderOpen, name: "File Opener", file: "file_opener_tool.py", desc: "Launch or close local files by name.", status: "ready" },
  { icon: Newspaper, name: "News", file: "news_tool.py", desc: "Headlines and structured news items.", status: "ready" },
  { icon: Globe, name: "Web Search", file: "websearch_tool.py", desc: "Real-time browsing for fresh facts.", status: "ready" },
  { icon: BookOpen, name: "RAG", file: "rag_tool.py", desc: "Query and rebuild local document index.", status: "active" },
  { icon: Mail, name: "Email", file: "email_tool.py", desc: "Read, search and send mail via IMAP / SMTP.", status: "offline" },
  { icon: Calculator, name: "Calculator", file: "calculator_tool.py", desc: "Arithmetic and unit calculations.", status: "ready" },
  { icon: Clock, name: "Date / Time", file: "datetime_tool.py", desc: "Current date, time, weekday answers.", status: "ready" },
];

const statusStyles: Record<Status, string> = {
  ready: "bg-success/10 text-success ring-success/20",
  active: "bg-primary/10 text-primary ring-primary/30",
  offline: "bg-zinc-500/10 text-zinc-400 ring-zinc-500/20",
};

const statusLabel: Record<Status, string> = {
  ready: "READY",
  active: "ACTIVE",
  offline: "OFFLINE",
};

export function ToolGrid() {
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-dim">
          Tools registered in voice_agent.py
        </h3>
        <span className="text-[11px] font-mono text-text-dim">{tools.length} loaded</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {tools.map((t) => (
          <div
            key={t.name}
            className={cn(
              "group relative p-4 bg-zinc-900/40 border border-border-main rounded-xl",
              "transition-colors hover:border-primary/40",
              t.status === "offline" && "opacity-60"
            )}
          >
            <div className="flex items-start justify-between">
              <div className="size-9 rounded-lg bg-zinc-900 ring-1 ring-border-main grid place-items-center">
                <t.icon className="size-4 text-zinc-200" strokeWidth={1.6} />
              </div>
              <span className={cn("text-[10px] font-mono px-1.5 py-0.5 rounded ring-1", statusStyles[t.status])}>
                {statusLabel[t.status]}
              </span>
            </div>
            <h4 className="mt-3 text-sm font-medium text-foreground">{t.name}</h4>
            <p className="text-xs text-text-dim mt-1 leading-relaxed">{t.desc}</p>
            <p className="mt-3 text-[10px] font-mono text-zinc-500 truncate">{t.file}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
