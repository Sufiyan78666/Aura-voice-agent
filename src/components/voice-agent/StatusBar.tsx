import { GitBranch, Bell, Wifi } from "lucide-react";

export function StatusBar() {
  return (
    <div className="h-6 bg-primary/90 text-primary-foreground text-[11px] font-mono flex items-center px-3 gap-4 shrink-0">
      <span className="flex items-center gap-1.5"><GitBranch className="size-3" /> main</span>
      <span>UTF-8</span>
      <span>Python 3.11.6</span>
      <span>venv: voice_agent</span>
      <div className="ml-auto flex items-center gap-4">
        <span className="flex items-center gap-1.5"><Wifi className="size-3" /> ws://localhost:8765</span>
        <span className="flex items-center gap-1.5"><Bell className="size-3" /> 0</span>
        <span>Ln 168, Col 24</span>
      </div>
    </div>
  );
}
