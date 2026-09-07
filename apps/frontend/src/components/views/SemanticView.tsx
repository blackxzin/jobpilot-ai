"use client";

import { BadgeCheck, Building2, ExternalLink, MapPin, Sparkles } from "lucide-react";
import { Badge, Button, Card, EmptyState, Meter, SectionHeader, Skeleton } from "@/components/ui";
import type { SemanticHit } from "@/lib/types";

const EXAMPLES = [
  "backend python com aws em startup",
  "liderança técnica remoto sênior",
  "kubernetes terraform plataforma",
];

export function SemanticView({
  query,
  onQueryChange,
  onSearch,
  searching,
  results,
  searched,
  indexedJobs,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  onSearch: () => void;
  searching: boolean;
  results: SemanticHit[];
  searched: boolean;
  indexedJobs: number;
}) {
  return (
    <div className="space-y-4">
      <Card className="p-5">
        <SectionHeader
          icon={Sparkles}
          title="Busca semântica"
          description={`Encontra vagas por significado, não só por palavra exata · ${indexedJobs} vagas indexadas`}
        />

        <div className="flex gap-2">
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && onSearch()}
            placeholder="Descreva a vaga que você quer…"
            aria-label="Descrição da vaga desejada"
            className="field"
          />
          <Button icon={Sparkles} onClick={onSearch} loading={searching} className="shrink-0">
            Buscar
          </Button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-faint">Exemplos:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => onQueryChange(example)}
              className="rounded-full bg-[var(--bg-input)] px-2.5 py-1 text-[11px] text-dim hover:text-body"
            >
              {example}
            </button>
          ))}
        </div>
      </Card>

      {searching && (
        <div className="space-y-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      )}

      {!searching && results.length > 0 && (
        <div className="space-y-3 stagger">
          {results.map((hit) => (
            <Card key={hit.id} interactive className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-medium">{hit.title}</h3>
                    <Badge tone={hit.score >= 60 ? "success" : hit.score >= 30 ? "warning" : "neutral"}>
                      {hit.score}% relevante
                    </Badge>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-dim">
                    {hit.company && (
                      <span className="flex items-center gap-1">
                        <Building2 size={11} /> {hit.company}
                      </span>
                    )}
                    {hit.location && (
                      <span className="flex items-center gap-1">
                        <MapPin size={11} /> {hit.location}
                      </span>
                    )}
                  </div>
                  <Meter value={hit.score} />
                  {hit.description && (
                    <p className="line-clamp-2 text-xs text-faint">{hit.description}</p>
                  )}
                  {hit.match && (
                    <p className="flex items-start gap-1 text-[11px] text-accent">
                      <BadgeCheck size={12} className="mt-px shrink-0" />
                      <span className="line-clamp-1">{hit.match}</span>
                    </p>
                  )}
                </div>

                {hit.apply_url && (
                  <a
                    href={hit.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex shrink-0 items-center gap-1 rounded-lg bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent"
                  >
                    Ver <ExternalLink size={11} />
                  </a>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {!searching && !searched && (
        <Card className="p-5">
          <EmptyState
            icon={Sparkles}
            title="Descreva a vaga que você procura"
            description={
              indexedJobs === 0
                ? "Nenhuma vaga indexada ainda. Salve vagas na aba Vagas para alimentar a busca."
                : `${indexedJobs} vagas prontas para busca por significado, sem depender de palavra exata.`
            }
          />
        </Card>
      )}

      {!searching && searched && results.length === 0 && (
        <Card className="p-5">
          <EmptyState
            icon={Sparkles}
            title="Nada semelhante encontrado"
            description={
              indexedJobs === 0
                ? "Nenhuma vaga foi indexada ainda. Salve vagas na aba Vagas para alimentar a busca."
                : "Tente descrever a vaga com outras palavras."
            }
          />
        </Card>
      )}
    </div>
  );
}
