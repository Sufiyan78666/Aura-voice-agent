import { Folder, Search, Mic, Wrench, Settings, User } from "lucide-react";
import { cn } from "@/lib/utils";

const top = [
  { icon: Folder, key: "files" },
  { icon: Search, key: "search" },
  { icon: Mic, key: "agent", active: true },
  { icon: Wrench, key: "tools" },
];
const bottom = [
  { icon: Settings, key: "settings" },
  { icon: User, key: "user" },
];

export function ActivityBar() {
  return (
    <div className="w-14 bg-sidebar-bg border-r border-border-main flex flex-col items-center py-4 gap-2 shrink-0">
      <div className="size-8 rounded-lg border border-primary/30 bg-primary/15 grid place-items-center mb-2">
        <div className="size-2.5 rounded-full bg-primary animate-pulse" />
      </div>
      {top.map(({ icon: Icon, key, active }) => (
        <button
          key={key}
          className={cn(
            "relative p-2.5 rounded-md text-text-dim hover:text-foreground transition-colors",
            active && "text-primary"
          )}
        >
          {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-primary rounded-r" />}
          <Icon className="size-[18px]" strokeWidth={1.6} />
        </button>
      ))}
      <div className="mt-auto flex flex-col items-center gap-1">
        {bottom.map(({ icon: Icon, key }) => (
          <button key={key} className="p-2.5 rounded-md text-text-dim hover:text-foreground transition-colors">
            <Icon className="size-[18px]" strokeWidth={1.6} />
          </button>
        ))}
      </div>
    </div>
  );
}
