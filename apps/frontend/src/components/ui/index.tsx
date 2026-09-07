"use client";

import { AlertTriangle, CheckCircle2, Info, Loader2, X, type LucideIcon } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/* ── Primitives ──────────────────────────────────────────────────── */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--accent)] text-[var(--accent-contrast)] hover:bg-[var(--accent-strong)] shadow-[0_4px_16px_-6px_var(--ring)]",
  secondary:
    "bg-[var(--bg-input)] text-body border border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-card-hover)]",
  ghost: "text-dim hover:text-body hover:bg-[var(--bg-card-hover)]",
  danger: "bg-transparent text-[var(--danger)] hover:bg-[color-mix(in_srgb,var(--danger)_14%,transparent)]",
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-xs gap-1.5 rounded-lg",
  md: "px-4 py-2.5 text-sm gap-2 rounded-xl",
};

export function Button({
  children,
  variant = "primary",
  size = "md",
  icon: Icon,
  loading = false,
  className = "",
  disabled,
  ...props
}: {
  children?: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: LucideIcon;
  loading?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center font-medium disabled:opacity-50 disabled:cursor-not-allowed ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
    >
      {loading ? (
        <Loader2 size={size === "sm" ? 13 : 15} className="spin-slow" />
      ) : (
        Icon && <Icon size={size === "sm" ? 13 : 15} strokeWidth={2.2} />
      )}
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
  interactive = false,
}: {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
}) {
  return (
    <div className={`surface ${interactive ? "interactive" : ""} ${className}`}>{children}</div>
  );
}

export function SectionHeader({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 flex-wrap mb-5">
      <div className="min-w-0">
        <h2 className="flex items-center gap-2 font-display text-base font-semibold tracking-tight">
          {Icon && (
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
              <Icon size={15} strokeWidth={2.2} />
            </span>
          )}
          {title}
        </h2>
        {description && <p className="mt-1 text-xs text-faint">{description}</p>}
      </div>
      {action}
    </div>
  );
}

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const TONE_STYLES: Record<Tone, string> = {
  neutral: "bg-[var(--bg-input)] text-dim",
  accent: "bg-accent-soft text-accent",
  success: "bg-[color-mix(in_srgb,var(--success)_14%,transparent)] text-[var(--success)]",
  warning: "bg-[color-mix(in_srgb,var(--warning)_14%,transparent)] text-[var(--warning)]",
  danger: "bg-[color-mix(in_srgb,var(--danger)_14%,transparent)] text-[var(--danger)]",
  info: "bg-[color-mix(in_srgb,var(--sky)_14%,transparent)] text-[var(--sky)]",
};

export function Badge({
  children,
  tone = "neutral",
  icon: Icon,
}: {
  children: ReactNode;
  tone?: Tone;
  icon?: LucideIcon;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${TONE_STYLES[tone]}`}
    >
      {Icon && <Icon size={11} />}
      {children}
    </span>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-medium text-dim">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-faint">{hint}</span>}
    </label>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--bg-input)] text-faint">
        <Icon size={20} />
      </span>
      <div className="space-y-1">
        <p className="text-sm font-medium text-body">{title}</p>
        {description && <p className="mx-auto max-w-sm text-xs text-faint">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

/* ── Score visualisations ────────────────────────────────────────── */

function scoreTone(score: number): { color: string; tone: Tone } {
  if (score >= 70) return { color: "var(--success)", tone: "success" };
  if (score >= 40) return { color: "var(--warning)", tone: "warning" };
  return { color: "var(--danger)", tone: "danger" };
}

/** Circular gauge. Reads faster than a bare number for a 0–100 score. */
export function ScoreRing({
  score,
  label,
  size = 108,
}: {
  score: number;
  label: string;
  size?: number;
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const { color } = scoreTone(clamped);

  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--bg-input)"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference * (1 - clamped / 100)}
            style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-2xl font-semibold" style={{ color }}>
            {Math.round(clamped)}
          </span>
          <span className="text-[10px] text-faint">/ 100</span>
        </div>
      </div>
      <p className="text-sm text-dim">{label}</p>
    </div>
  );
}

export function Meter({ value, max = 100 }: { value: number; max?: number }) {
  const percent = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="meter" role="presentation">
      <span style={{ width: `${percent}%` }} />
    </div>
  );
}

/* ── Overlays ────────────────────────────────────────────────────── */

/** Slide-over panel used for every long-form result (letters, resumes, analyses). */
export function Drawer({
  open,
  title,
  icon: Icon,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  icon?: LucideIcon;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    // Focus moves into the panel so keyboard and screen-reader users are not
    // left behind on the page underneath.
    panelRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-pop"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="relative flex h-full w-full max-w-xl flex-col bg-elevated border-l border-hair shadow-2xl animate-slide-down focus:outline-none"
      >
        <header className="flex items-center justify-between gap-3 border-b border-hair px-5 py-4">
          <h2 className="flex items-center gap-2 font-display text-sm font-semibold">
            {Icon && <Icon size={16} className="text-accent" />}
            {title}
          </h2>
          <Button variant="ghost" size="sm" icon={X} onClick={onClose} aria-label="Fechar" />
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-5">{children}</div>
        {footer && <footer className="border-t border-hair px-5 py-3">{footer}</footer>}
      </div>
    </div>
  );
}

/* ── Toasts ──────────────────────────────────────────────────────── */

export type ToastKind = "success" | "error" | "info";

const TOAST_ICON: Record<ToastKind, LucideIcon> = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
};

const TOAST_TONE: Record<ToastKind, Tone> = {
  success: "success",
  error: "danger",
  info: "info",
};

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: { id: number; kind: ToastKind; message: string }[];
  onDismiss: (id: number) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[60] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
      role="status"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const Icon = TOAST_ICON[toast.kind];
        return (
          <div
            key={toast.id}
            className={`surface flex items-start gap-2.5 px-4 py-3 text-sm animate-rise ${TONE_STYLES[TOAST_TONE[toast.kind]]}`}
          >
            <Icon size={15} className="mt-0.5 shrink-0" />
            <p className="flex-1 leading-snug">{toast.message}</p>
            <button
              onClick={() => onDismiss(toast.id)}
              aria-label="Dispensar aviso"
              className="shrink-0 opacity-60 hover:opacity-100"
            >
              <X size={13} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
