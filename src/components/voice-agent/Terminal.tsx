import { Plus, Trash2 } from "lucide-react";

export function Terminal() {
  return (
    <div className="h-40 bg-sidebar-bg border-t border-border-main flex flex-col shrink-0">
      <div className="h-8 flex items-center px-4 gap-5 border-b border-border-main text-[10px] font-semibold uppercase tracking-widest">
        <span className="text-primary border-b border-primary h-full flex items-center px-1">Terminal</span>
        <span className="text-text-dim hover:text-foreground cursor-pointer">Debug</span>
        <span className="text-text-dim hover:text-foreground cursor-pointer">Output</span>
        <span className="text-text-dim hover:text-foreground cursor-pointer">Problems</span>
        <div className="ml-auto flex items-center gap-3 text-text-dim normal-case tracking-normal text-[11px] font-mono">
          <span>powershell</span>
          <Plus className="size-3.5" />
          <Trash2 className="size-3.5" />
        </div>
      </div>
      <div className="flex-1 p-3 font-mono text-[12px] overflow-y-auto scroll-thin text-zinc-400 leading-relaxed">
        <div>
          <span className="text-success">PS C:\Users\asus\Desktop\voice_agent&gt;</span>{" "}
          <span className="text-zinc-100">python voice_agent.py</span>
        </div>
        <div className="text-zinc-500 mt-1">
          [obs] initializing virtual environment ... ok
          <br />
          [stt] faster-whisper loaded (medium · int8)
          <br />
          [rag] index loaded · 1240 chunks
          <br />
          [tools] registered: weather, alarm, file_opener, news, websearch, rag, email, calculator, datetime
          <br />
          [agent] wake word active · "hey agent"
          <span className="caret text-zinc-100">▍</span>
        </div>
      </div>
    </div>
  );
}
