import { Rocket } from "lucide-react";

export function Logo({ size = "md" }: { size?: "md" | "lg" }) {
  const box = size === "lg" ? "h-12 w-12 rounded-2xl" : "h-8 w-8 rounded-xl";
  const glyph = size === "lg" ? 22 : 16;
  const text = size === "lg" ? "text-2xl" : "text-[15px]";

  return (
    <div className="flex items-center gap-2.5">
      <span
        className={`inline-flex items-center justify-center ${box} text-[var(--accent-contrast)] shadow-[0_6px_20px_-8px_var(--ring)]`}
        style={{ background: "linear-gradient(135deg, var(--accent), var(--sky))" }}
      >
        <Rocket size={glyph} strokeWidth={2.4} />
      </span>
      <span className={`font-display font-semibold tracking-tight ${text}`}>
        JobPilot <span className="text-gradient">AI</span>
      </span>
    </div>
  );
}
