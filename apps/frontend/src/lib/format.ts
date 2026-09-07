/** Presentation helpers shared across views. */

const DATE_TIME = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

const DATE_ONLY = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const CURRENCY = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function parse(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parse(value);
  return date ? DATE_TIME.format(date) : "—";
}

export function formatDate(value: string | null | undefined): string {
  const date = parse(value);
  return date ? DATE_ONLY.format(date) : "—";
}

/** "há 3 dias" / "em 2 horas", for timestamps where the exact instant is noise. */
export function formatRelative(value: string | null | undefined): string {
  const date = parse(value);
  if (!date) return "—";

  const diffMs = date.getTime() - Date.now();
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 365 * 24 * 60 * 60 * 1000],
    ["month", 30 * 24 * 60 * 60 * 1000],
    ["day", 24 * 60 * 60 * 1000],
    ["hour", 60 * 60 * 1000],
    ["minute", 60 * 1000],
  ];
  const formatter = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

  for (const [unit, ms] of units) {
    if (Math.abs(diffMs) >= ms) return formatter.format(Math.round(diffMs / ms), unit);
  }
  return "agora";
}

export function formatSalaryRange(min: number | null, max: number | null): string {
  if (!min && !max) return "";
  if (min && max) return `${CURRENCY.format(min)} – ${CURRENCY.format(max)}`;
  return CURRENCY.format((min ?? max) as number);
}

/** "technical_interview" → "Entrevista técnica". */
export function humanizeStatus(status: string): string {
  return STATUS_LABELS[status] ?? status.replace(/_/g, " ");
}

export const STATUS_LABELS: Record<string, string> = {
  applied: "Candidatado",
  under_review: "Em análise",
  technical_test: "Teste técnico",
  hr_interview: "Entrevista RH",
  technical_interview: "Entrevista técnica",
  offer: "Proposta",
  rejected: "Rejeitado",
};

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts.at(-1)?.[0] ?? "")).toUpperCase();
}
