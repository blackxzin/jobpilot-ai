"use client";

import {
  Briefcase,
  Building2,
  ExternalLink,
  MapPin,
  Plus,
  Search,
  WifiOff,
  X,
} from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, EmptyState, SectionHeader, Skeleton } from "@/components/ui";
import { JOB_SOURCES, QUICK_FILTERS } from "@/lib/constants";
import { formatSalaryRange } from "@/lib/format";
import type { ExternalJob, Job } from "@/lib/types";

export interface NewJobDraft {
  title: string;
  company_name: string;
  location: string;
  location_type: string;
  is_remote: boolean;
  apply_url: string;
  description: string;
}

export const EMPTY_JOB_DRAFT: NewJobDraft = {
  title: "",
  company_name: "",
  location: "",
  location_type: "",
  is_remote: false,
  apply_url: "",
  description: "",
};

/** External boards and the local database return different shapes. */
function normalize(job: Job | ExternalJob) {
  const external = job as ExternalJob;
  const local = job as Job;
  return {
    title: external.position || external.title || external.name || "Vaga sem título",
    company: external.company || external.company_name || "",
    location: job.location || "",
    description: job.description || "",
    url: external.url || external.apply_url || "",
    remote: Boolean(job.is_remote),
    salary: formatSalaryRange(local.salary_min ?? null, local.salary_max ?? null),
  };
}

function JobCard({ job }: { job: Job | ExternalJob }) {
  const item = normalize(job);

  return (
    <Card interactive className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1.5">
          <h3 className="truncate font-medium">{item.title}</h3>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-dim">
            {item.company && (
              <span className="flex items-center gap-1">
                <Building2 size={11} /> {item.company}
              </span>
            )}
            {item.location && (
              <span className="flex items-center gap-1">
                <MapPin size={11} /> {item.location}
              </span>
            )}
          </div>
          {item.description && (
            <p className="line-clamp-2 text-xs text-faint">{item.description}</p>
          )}
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {item.remote && <Badge tone="accent">Remoto</Badge>}
            {item.salary && <Badge tone="info">{item.salary}</Badge>}
          </div>
        </div>

        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex shrink-0 items-center gap-1 rounded-lg bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent hover:bg-[color-mix(in_srgb,var(--accent)_22%,transparent)]"
          >
            Candidatar <ExternalLink size={11} />
          </a>
        )}
      </div>
    </Card>
  );
}

export function JobsView({
  source,
  onSourceChange,
  query,
  onQueryChange,
  filters,
  onToggleFilter,
  onSearch,
  searching,
  results,
  sourceAvailable,
  searched,
  draft,
  onDraftChange,
  onCreateJob,
  creating,
}: {
  source: string;
  onSourceChange: (source: string) => void;
  query: string;
  onQueryChange: (query: string) => void;
  filters: string[];
  onToggleFilter: (filter: string) => void;
  onSearch: () => void;
  searching: boolean;
  results: (Job | ExternalJob)[];
  sourceAvailable: boolean;
  searched: boolean;
  draft: NewJobDraft;
  onDraftChange: (draft: NewJobDraft) => void;
  onCreateJob: () => void;
  creating: boolean;
}) {
  const [showForm, setShowForm] = useState(false);
  const activeSource = JOB_SOURCES.find((item) => item.id === source);

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <SectionHeader
          icon={Search}
          title="Buscar vagas"
          description={activeSource?.description}
          action={
            <Button
              variant="secondary"
              size="sm"
              icon={showForm ? X : Plus}
              onClick={() => setShowForm((value) => !value)}
            >
              {showForm ? "Cancelar" : "Adicionar vaga"}
            </Button>
          }
        />

        {showForm && (
          <div className="surface-inset mb-5 space-y-3 p-4 animate-slide-down">
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder="Título da vaga *"
                aria-label="Título da vaga"
                className="field"
              />
              <input
                value={draft.company_name}
                onChange={(event) => onDraftChange({ ...draft, company_name: event.target.value })}
                placeholder="Empresa *"
                aria-label="Nome da empresa"
                className="field"
              />
              <input
                value={draft.location}
                onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
                placeholder="Local (ex.: São Paulo, SP)"
                aria-label="Local da vaga"
                className="field"
              />
              <select
                value={draft.location_type}
                onChange={(event) =>
                  onDraftChange({
                    ...draft,
                    location_type: event.target.value,
                    is_remote: event.target.value === "remote",
                  })
                }
                aria-label="Modelo de trabalho"
                className="field"
              >
                <option value="">Modelo de trabalho</option>
                <option value="remote">Remoto</option>
                <option value="hybrid">Híbrido</option>
                <option value="onsite">Presencial</option>
              </select>
              <input
                value={draft.apply_url}
                onChange={(event) => onDraftChange({ ...draft, apply_url: event.target.value })}
                placeholder="Link para candidatura (opcional)"
                aria-label="Link para candidatura"
                className="field sm:col-span-2"
              />
            </div>
            <textarea
              value={draft.description}
              onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
              placeholder="Descrição e requisitos — quanto mais completo, melhores as análises de IA"
              aria-label="Descrição da vaga"
              rows={3}
              className="field resize-y"
            />
            <Button size="sm" icon={Plus} onClick={onCreateJob} loading={creating}>
              Salvar vaga
            </Button>
          </div>
        )}

        <div className="mb-4 flex flex-wrap gap-1.5">
          {JOB_SOURCES.map((item) => (
            <button
              key={item.id}
              onClick={() => onSourceChange(item.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                source === item.id
                  ? "bg-[var(--accent)] text-[var(--accent-contrast)]"
                  : "bg-[var(--bg-input)] text-dim hover:text-body"
              }`}
            >
              {item.name}
            </button>
          ))}
        </div>

        <div className="mb-4 flex gap-2">
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && onSearch()}
            placeholder="python, react, backend, estágio…"
            aria-label="Termo de busca"
            className="field"
          />
          <Button icon={Search} onClick={onSearch} loading={searching} className="shrink-0">
            Buscar
          </Button>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {QUICK_FILTERS.map((filter) => {
            const active = filters.includes(filter);
            return (
              <button
                key={filter}
                onClick={() => onToggleFilter(filter)}
                aria-pressed={active}
                className={`rounded-full px-3 py-1 text-xs ${
                  active
                    ? "bg-accent-soft text-accent ring-1 ring-[var(--border-accent)]"
                    : "bg-[var(--bg-input)] text-dim hover:text-body"
                }`}
              >
                {filter}
              </button>
            );
          })}
        </div>
      </Card>

      {searching && (
        <div className="space-y-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-24" />
          ))}
        </div>
      )}

      {!searching && !sourceAvailable && searched && (
        <Card className="p-5">
          <EmptyState
            icon={WifiOff}
            title={`${activeSource?.name ?? "Esta fonte"} não respondeu`}
            description="O site de vagas está indisponível no momento. Tente outra fonte ou repita em alguns minutos."
          />
        </Card>
      )}

      {!searching && sourceAvailable && results.length > 0 && (
        <div className="space-y-3 stagger">
          <p className="text-xs text-faint">{results.length} vagas encontradas</p>
          {results.map((job, index) => (
            <JobCard key={(job as ExternalJob).url || (job as Job).id || index} job={job} />
          ))}
        </div>
      )}

      {!searching && sourceAvailable && searched && results.length === 0 && (
        <Card className="p-5">
          <EmptyState
            icon={Briefcase}
            title="Nenhuma vaga encontrada"
            description={
              source === "local"
                ? "Você ainda não salvou nenhuma vaga. Use “Adicionar vaga” para cadastrar uma."
                : "Tente termos mais amplos ou selecione outra fonte."
            }
          />
        </Card>
      )}

      {!searching && !searched && (
        <Card className="p-5">
          <EmptyState
            icon={Search}
            title="Comece por uma busca"
            description="Digite uma tecnologia, um cargo ou um nível de senioridade e escolha a fonte."
          />
        </Card>
      )}
    </div>
  );
}
