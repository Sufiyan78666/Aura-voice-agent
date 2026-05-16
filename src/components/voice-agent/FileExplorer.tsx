import { ChevronDown, ChevronRight, FileCode2, FileJson, FileCog, Folder } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

type Node =
  | { type: "folder"; name: string; children: Node[] }
  | { type: "py"; name: string; active?: boolean; integrate?: string }
  | { type: "json"; name: string }
  | { type: "env"; name: string };

const tree: Node = {
  type: "folder",
  name: "voice_agent",
  children: [
    { type: "folder", name: "rag_docs", children: [] },
    { type: "folder", name: "rag_index", children: [] },
    { type: "folder", name: "scratch", children: [] },
    { type: "py", name: "voice_agent.py", active: true, integrate: "Main entrypoint — wire frontend here" },
    { type: "py", name: "alarm_tool.py" },
    { type: "py", name: "calculator_tool.py" },
    { type: "py", name: "check_rag_docs.py" },
    { type: "py", name: "datetime_tool.py" },
    { type: "py", name: "email_tool.py" },
    { type: "py", name: "file_opener_tool.py" },
    { type: "py", name: "guardrails.py" },
    { type: "py", name: "hinglish_stt.py" },
    { type: "py", name: "news_tool.py" },
    { type: "py", name: "observability.py" },
    { type: "py", name: "rag_tool.py" },
    { type: "py", name: "weather_tool.py" },
    { type: "py", name: "websearch_tool.py" },
    { type: "json", name: "alarms.json" },
    { type: "json", name: "memory.json" },
    { type: "env", name: ".env" },
  ],
};

function iconFor(n: Node) {
  if (n.type === "folder") return Folder;
  if (n.type === "json") return FileJson;
  if (n.type === "env") return FileCog;
  return FileCode2;
}

function NodeRow({ node, depth = 0 }: { node: Node; depth?: number }) {
  const [open, setOpen] = useState(true);
  const Icon = iconFor(node);
  const padding = { paddingLeft: 8 + depth * 12 };

  if (node.type === "folder") {
    return (
      <div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center gap-1.5 py-1 pr-2 text-text-dim hover:bg-white/[0.03] rounded text-left"
          style={padding}
        >
          {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          <Folder className="size-3.5" />
          <span className="text-[12px]">{node.name}</span>
        </button>
        {open && (
          <div>
            {node.children.map((c) => (
              <NodeRow key={c.name} node={c} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const active = "active" in node && node.active;
  return (
    <div
      className={cn(
        "group flex items-center gap-2 py-1 pr-2 rounded cursor-pointer hover:bg-white/[0.03]",
        active && "bg-primary/10 text-primary border-r-2 border-primary"
      )}
      style={padding}
    >
      <span className="w-3.5" />
      <Icon className={cn("size-3.5 shrink-0", active ? "text-primary" : "text-text-dim")} />
      <span className={cn("text-[12px] truncate", !active && "text-zinc-300")}>{node.name}</span>
    </div>
  );
}

export function FileExplorer() {
  return (
    <div className="w-64 bg-sidebar-bg border-r border-border-main flex flex-col shrink-0">
      <div className="h-12 flex items-center px-4 text-[11px] font-semibold uppercase tracking-wider text-text-dim border-b border-border-main">
        Explorer · voice_agent
      </div>
      <div className="flex-1 overflow-y-auto scroll-thin font-mono py-2 px-1">
        <NodeRow node={tree} />
      </div>
      <div className="p-3 border-t border-border-main">
        <p className="text-[10px] font-mono uppercase tracking-widest text-text-dim mb-2">Integration Hook</p>
        <code className="block text-[11px] font-mono text-zinc-300 bg-black/30 rounded-md p-2 ring-1 ring-border-main">
          python voice_agent.py
        </code>
        <p className="text-[10px] text-text-dim mt-2 leading-relaxed">
          Expose a WebSocket / REST endpoint from <span className="text-primary">voice_agent.py</span> and point this UI's transport layer at it.
        </p>
      </div>
    </div>
  );
}
