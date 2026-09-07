"use client";

import { CalendarDays, Clock, MapPin, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, Field, SectionHeader } from "@/components/ui";
import { formatDateTime, formatRelative } from "@/lib/format";
import type { CalendarEvent } from "@/lib/types";

export interface EventDraft {
  title: string;
  event_type: string;
  date: string;
  notes: string;
  location: string;
}

export const EMPTY_EVENT_DRAFT: EventDraft = {
  title: "",
  event_type: "interview",
  date: "",
  notes: "",
  location: "",
};

const TYPE_META: Record<string, { label: string; color: string }> = {
  interview: { label: "Entrevista", color: "var(--accent)" },
  deadline: { label: "Prazo", color: "var(--rose)" },
  reminder: { label: "Lembrete", color: "var(--sky)" },
};

const STATUS_OPTIONS = [
  { value: "scheduled", label: "Agendado" },
  { value: "completed", label: "Realizado" },
  { value: "cancelled", label: "Cancelado" },
];

export function CalendarView({
  events,
  draft,
  onDraftChange,
  onCreate,
  onDelete,
  onUpdateStatus,
  creating,
}: {
  events: CalendarEvent[];
  draft: EventDraft;
  onDraftChange: (draft: EventDraft) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onUpdateStatus: (id: string, status: string) => void;
  creating: boolean;
}) {
  const [showForm, setShowForm] = useState(false);

  // Upcoming first: a calendar sorted by creation order buries the next
  // interview under events that already happened.
  const sorted = [...events].sort((a, b) => {
    const left = a.date ? new Date(a.date).getTime() : Number.MAX_SAFE_INTEGER;
    const right = b.date ? new Date(b.date).getTime() : Number.MAX_SAFE_INTEGER;
    return left - right;
  });

  return (
    <Card className="p-5">
      <SectionHeader
        icon={CalendarDays}
        title="Agenda"
        description="Entrevistas, prazos e lembretes"
        action={
          <Button
            size="sm"
            variant={showForm ? "secondary" : "primary"}
            icon={showForm ? X : Plus}
            onClick={() => setShowForm((value) => !value)}
          >
            {showForm ? "Cancelar" : "Novo evento"}
          </Button>
        }
      />

      {showForm && (
        <div className="surface-inset mb-5 space-y-3 p-4 animate-slide-down">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Título">
              <input
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder="Entrevista técnica — Nubank"
                className="field"
              />
            </Field>
            <Field label="Tipo">
              <select
                value={draft.event_type}
                onChange={(event) => onDraftChange({ ...draft, event_type: event.target.value })}
                className="field"
              >
                {Object.entries(TYPE_META).map(([value, meta]) => (
                  <option key={value} value={value}>
                    {meta.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Data e hora">
              <input
                type="datetime-local"
                value={draft.date}
                onChange={(event) => onDraftChange({ ...draft, date: event.target.value })}
                className="field"
              />
            </Field>
            <Field label="Local ou link">
              <input
                value={draft.location}
                onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
                placeholder="Google Meet, endereço…"
                className="field"
              />
            </Field>
          </div>
          <Field label="Anotações">
            <textarea
              value={draft.notes}
              onChange={(event) => onDraftChange({ ...draft, notes: event.target.value })}
              rows={2}
              placeholder="Preparar perguntas sobre o time, revisar sistemas distribuídos…"
              className="field resize-y"
            />
          </Field>
          <Button size="sm" onClick={onCreate} loading={creating}>
            Salvar evento
          </Button>
        </div>
      )}

      {sorted.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="Agenda vazia"
          description="Cadastre entrevistas e prazos para não perder nenhum retorno."
        />
      ) : (
        <ul className="space-y-3 stagger">
          {sorted.map((event) => {
            const meta = TYPE_META[event.event_type] ?? {
              label: event.event_type,
              color: "var(--text-muted)",
            };
            const past = event.date ? new Date(event.date).getTime() < Date.now() : false;

            return (
              <li
                key={event.id}
                className="surface-inset flex items-start justify-between gap-3 p-4"
                style={{ borderLeft: `3px solid ${meta.color}`, opacity: past ? 0.7 : 1 }}
              >
                <div className="min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="neutral">{meta.label}</Badge>
                    <h3 className="text-sm font-medium">{event.title}</h3>
                  </div>
                  {event.date && (
                    <p className="flex items-center gap-1.5 text-xs text-dim">
                      <Clock size={11} /> {formatDateTime(event.date)}
                      <span className="text-faint">· {formatRelative(event.date)}</span>
                    </p>
                  )}
                  {event.location && (
                    <p className="flex items-center gap-1.5 text-xs text-faint">
                      <MapPin size={11} /> {event.location}
                    </p>
                  )}
                  {event.notes && <p className="text-xs text-faint">{event.notes}</p>}
                </div>

                <div className="flex shrink-0 items-center gap-1.5">
                  <select
                    value={event.status}
                    onChange={(change) => onUpdateStatus(event.id, change.target.value)}
                    aria-label={`Status de ${event.title}`}
                    className="field !w-auto !py-1 !text-xs"
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={Trash2}
                    onClick={() => onDelete(event.id)}
                    aria-label={`Excluir ${event.title}`}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
