export function Visualizer({ active = true }: { active?: boolean }) {
  const bars = [18, 36, 58, 82, 64, 42, 96, 70, 30, 50, 78, 44, 22, 60, 88, 38];
  return (
    <div className="relative h-56 bg-zinc-900/40 rounded-2xl border border-border-main overflow-hidden">
      {/* faint grid */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      />
      <div className="absolute inset-0 grid place-items-center">
        <div className="flex items-end gap-1.5 h-32">
          {bars.map((h, i) => (
            <div
              key={i}
              className="w-1.5 rounded-full bg-primary"
              style={{
                height: `${h}%`,
                opacity: 0.35 + (h / 100) * 0.65,
                animation: active ? `bar-bounce ${0.9 + (i % 5) * 0.12}s ease-in-out ${i * 0.04}s infinite` : "none",
                transformOrigin: "bottom",
              }}
            />
          ))}
        </div>
      </div>
      <div className="absolute bottom-3 left-4 flex items-center gap-2">
        <span className="size-1.5 rounded-full bg-success" />
        <span className="text-[10px] font-mono text-text-dim uppercase tracking-[0.18em]">
          Real-time audio input · 16 kHz mono
        </span>
      </div>
      <div className="absolute bottom-3 right-4 text-[10px] font-mono text-text-dim">
        VAD <span className="text-foreground">0.84</span> · RMS <span className="text-foreground">−14 dB</span>
      </div>
    </div>
  );
}
