"use client";

import {
  Bot,
  Building2,
  ClipboardList,
  FileEdit,
  Gauge,
  Mail,
  Target,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { Badge, Button, Card, EmptyState, SectionHeader, Skeleton } from "@/components/ui";
import { COVER_LETTER_LANGUAGES, COVER_LETTER_TONES, PIPELINE_STATUSES } from "@/lib/constants";
import { formatRelative, humanizeStatus } from "@/lib/format";
import type { Application, CoverLetter } from "@/lib/types";

const STATUS_TONE: Record<string, "neutral" | "info" | "warning" | "success" | "danger"> = {
  applied: "neutral",
  under_review: "info",
  technical_test: "info",
  hr_interview: "warning",
  technical_interview: "warning",
  offer: "success",
  rejected: "danger",
};

interface AiAction {
  id: string;
  label: string;
  busyLabel: string;
  icon: LucideIcon;
  color: string;
}

const AI_ACTIONS: AiAction[] = [
  { id: "match", label: "Compatibilidade", busyLabel: "Analisando…", icon: Target, color: "var(--sky)" },
  { id: "ats", label: "ATS Score", busyLabel: "Analisando…", icon: Gauge, color: "var(--violet)" },
  { id: "cover", label: "Carta", busyLabel: "Gerando…", icon: Mail, color: "var(--amber)" },
  { id: "tailor", label: "Currículo", busyLabel: "Gerando…", icon: FileEdit, color: "var(--accent)" },
  { id: "auto", label: "Auto Apply", busyLabel: "Aplicando…", icon: Bot, color: "var(--rose)" },
];

export function ApplicationsView({
  applications,
  loading,
  busyAction,
  onRunAction,
  onUpdateStatus,
  language,
  onLanguageChange,
  tone,
  onToneChange,
  coverLetters,
  showHistory,
  onToggleHistory,
  onViewCoverLetter,
  onDeleteCoverLetter,
}: {
  applications: Application[];
  loading: boolean;
  /** "<actionId>:<applicationId>" while a request is in flight, else "". */
  busyAction: string;
  onRunAction: (actionId: string, application: Application) => void;
  onUpdateStatus: (id: string, status: string) => void;
  language: string;
  onLanguageChange: (value: string) => void;
  tone: string;
  onToneChange: (value: string) => void;
  coverLetters: CoverLetter[];
  showHistory: boolean;
  onToggleHistory: () => void;
  onViewCoverLetter: (letter: CoverLetter) => void;
  onDeleteCoverLetter: (id: string) => void;
}) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="h-40" />
        ))}
      </div>
    );
  }

  return (
    <Card className="p-5">
      <SectionHeader
        icon={ClipboardList}
        title="Candidaturas"
        description={`${applications.length} no seu pipeline`}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={language}
              onChange={(event) => onLanguageChange(event.target.value)}
              aria-label="Idioma da carta de apresentação"
              className="field !w-auto !py-1.5 !text-xs"
            >
              {COVER_LETTER_LANGUAGES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <select
              value={tone}
              onChange={(event) => onToneChange(event.target.value)}
              aria-label="Tom da carta de apresentação"
              className="field !w-auto !py-1.5 !text-xs"
            >
              {COVER_LETTER_TONES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Button variant="secondary" size="sm" icon={Mail} onClick={onToggleHistory}>
              Cartas
            </Button>
          </div>
        }
      />

      {showHistory && (
        <div className="surface-inset mb-5 space-y-2 p-4 animate-slide-down">
          <h3 className="text-xs font-semibold text-dim">Cartas geradas</h3>
          {coverLetters.length === 0 ? (
            <p className="text-xs text-faint">Nenhuma carta gerada ainda.</p>
          ) : (
            coverLetters.map((letter) => (
              <div
                key={letter.id}
                className="flex items-center justify-between gap-2 rounded-lg bg-card px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium">{letter.title || "Carta sem título"}</p>
                  <p className="text-[11px] text-faint">
                    {formatRelative(letter.created_at)} · {letter.language} · {letter.tone}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="secondary" size="sm" onClick={() => onViewCoverLetter(letter)}>
                    Ver
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={Trash2}
                    onClick={() => onDeleteCoverLetter(letter.id)}
                    aria-label="Excluir carta"
                  />
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {applications.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="Nenhuma candidatura ainda"
          description="Use o Auto Apply na aba Vagas, ou registre uma candidatura manualmente."
        />
      ) : (
        <ul className="space-y-3 stagger">
          {applications.map((application) => (
            <li key={application.id} className="surface-inset space-y-3 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <h3 className="truncate text-sm font-medium">
                    {application.job_title || "Vaga removida"}
                  </h3>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-dim">
                    {application.company && (
                      <span className="flex items-center gap-1">
                        <Building2 size={11} /> {application.company}
                      </span>
                    )}
                    <span className="text-faint">
                      {formatRelative(application.applied_at ?? application.created_at)}
                    </span>
                  </div>
                </div>
                <Badge tone={STATUS_TONE[application.status] ?? "neutral"}>
                  {humanizeStatus(application.status)}
                </Badge>
              </div>

              <div className="flex flex-wrap gap-1">
                {PIPELINE_STATUSES.map((status) => {
                  const active = application.status === status;
                  return (
                    <button
                      key={status}
                      onClick={() => onUpdateStatus(application.id, status)}
                      aria-pressed={active}
                      className={`rounded-md px-2 py-1 text-[11px] ${
                        active
                          ? "bg-[var(--accent)] text-[var(--accent-contrast)]"
                          : "bg-[var(--bg-input)] text-dim hover:text-body"
                      }`}
                    >
                      {humanizeStatus(status)}
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2 border-t border-hair pt-3">
                {AI_ACTIONS.map((action) => {
                  const busy = busyAction === `${action.id}:${application.id}`;
                  return (
                    <button
                      key={action.id}
                      onClick={() => onRunAction(action.id, application)}
                      disabled={Boolean(busyAction)}
                      className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                      style={{
                        background: `color-mix(in srgb, ${action.color} 14%, transparent)`,
                        color: action.color,
                      }}
                    >
                      <action.icon size={12} />
                      {busy ? action.busyLabel : action.label}
                    </button>
                  );
                })}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
