"use client";

import {
  Award,
  Building2,
  ClipboardList,
  Github,
  Linkedin,
  Target,
  TrendingUp,
  XCircle,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState, Meter, SectionHeader, Skeleton } from "@/components/ui";
import { formatDate, humanizeStatus } from "@/lib/format";
import type { Analytics, ApplicationStats, GithubImport, ProfileSuggestion } from "@/lib/types";

/** Counts up to `value` so a number that just changed draws the eye. */
function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(value);
      return;
    }
    const duration = 750;
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplay(Math.round(value * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <>
      {display}
      {suffix}
    </>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  caption,
  accent,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  caption?: string;
  accent: string;
}) {
  return (
    <Card interactive className="relative overflow-hidden p-4">
      <span className="absolute inset-y-0 left-0 w-[3px]" style={{ background: accent }} />
      <span
        className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-xl"
        style={{ background: `color-mix(in srgb, ${accent} 14%, transparent)`, color: accent }}
      >
        <Icon size={16} strokeWidth={2.2} />
      </span>
      <p className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</p>
      <p className="font-display text-3xl font-semibold" style={{ color: accent }}>
        <AnimatedNumber value={value} />
      </p>
      {caption && <p className="mt-0.5 text-[11px] text-faint">{caption}</p>}
    </Card>
  );
}

const TIMELINE_DAYS = 30;

/** Expand a sparse series into one entry per day so gaps read as gaps. */
function fillDays(data: { date: string; count: number }[]): { date: string; count: number }[] {
  const counts = new Map(data.map((point) => [point.date.slice(0, 10), point.count]));
  const days: { date: string; count: number }[] = [];
  const today = new Date();

  for (let offset = TIMELINE_DAYS - 1; offset >= 0; offset--) {
    const day = new Date(today);
    day.setDate(today.getDate() - offset);
    const key = day.toISOString().slice(0, 10);
    days.push({ date: key, count: counts.get(key) ?? 0 });
  }
  return days;
}

/** Sparkline-style bar chart of applications per day. */
function TimelineChart({ data }: { data: { date: string; count: number }[] }) {
  const series = fillDays(data);
  const max = Math.max(...series.map((point) => point.count), 1);

  return (
    <div className="flex h-28 items-end gap-1" role="img" aria-label="Candidaturas por dia nos últimos 30 dias">
      {series.map((point) => (
        <div
          key={point.date}
          className="group relative flex-1 rounded-t transition-opacity hover:opacity-80"
          style={{
            height: `${Math.max((point.count / max) * 100, 3)}%`,
            background:
              point.count > 0
                ? "linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 35%, transparent))"
                : "var(--bg-input)",
          }}
        >
          <span className="pointer-events-none absolute bottom-full left-1/2 mb-1 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-elevated px-2 py-1 text-[10px] shadow-lg group-hover:block">
            {formatDate(point.date)}: {point.count}
          </span>
        </div>
      ))}
    </div>
  );
}

const STATUS_COLORS = ["var(--accent)", "var(--sky)", "var(--amber)", "var(--violet)", "var(--rose)"];

function StatusBreakdown({ byStatus }: { byStatus: Record<string, number> }) {
  const entries = Object.entries(byStatus).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  return (
    <ul className="space-y-3">
      {entries.map(([status, count], index) => (
        <li key={status} className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-dim">{humanizeStatus(status)}</span>
            <span className="font-medium">
              {count}
              <span className="ml-1 text-faint">
                ({total > 0 ? Math.round((count / total) * 100) : 0}%)
              </span>
            </span>
          </div>
          <div className="meter">
            <span
              style={{
                width: `${total > 0 ? (count / total) * 100 : 0}%`,
                background: STATUS_COLORS[index % STATUS_COLORS.length],
              }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function DashboardView({
  analytics,
  stats,
  loading,
  githubUsername,
  onGithubUsernameChange,
  githubData,
  onImportGithub,
  targetRole,
  onTargetRoleChange,
  profileSuggestion,
  onSuggestProfile,
  hasResume,
  importing,
}: {
  analytics: Analytics | null;
  stats: ApplicationStats | null;
  loading: boolean;
  githubUsername: string;
  onGithubUsernameChange: (value: string) => void;
  githubData: GithubImport | null;
  onImportGithub: () => void;
  targetRole: string;
  onTargetRoleChange: (value: string) => void;
  profileSuggestion: ProfileSuggestion | null;
  onSuggestProfile: () => void;
  /** Positioning is derived from the resume, so it is unavailable without one. */
  hasResume: boolean;
  importing: string;
}) {
  if (loading) {
    return (
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  const timeline = analytics?.applications_over_time ?? [];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={ClipboardList}
          label="Candidaturas"
          value={analytics?.total_applications ?? stats?.total ?? 0}
          caption={`${analytics?.response_rate ?? 0}% de resposta`}
          accent="var(--sky)"
        />
        <StatCard
          icon={Target}
          label="Entrevistas"
          value={analytics?.interviews ?? 0}
          caption={`${analytics?.interview_rate ?? 0}% de conversão`}
          accent="var(--accent)"
        />
        <StatCard
          icon={Award}
          label="Propostas"
          value={analytics?.offers ?? 0}
          caption={`${analytics?.offer_rate ?? 0}% de conversão`}
          accent="var(--amber)"
        />
        <StatCard
          icon={XCircle}
          label="Rejeições"
          value={analytics?.rejected ?? 0}
          caption={`${analytics?.rejection_rate ?? 0}% do total`}
          accent="var(--rose)"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="p-5 lg:col-span-3">
          <SectionHeader
            icon={TrendingUp}
            title="Funil de candidaturas"
            description="Distribuição por estágio do processo"
          />
          {stats?.by_status && Object.keys(stats.by_status).length > 0 ? (
            <StatusBreakdown byStatus={stats.by_status} />
          ) : (
            <EmptyState
              icon={ClipboardList}
              title="Sem candidaturas ainda"
              description="Registre uma candidatura para ver seu funil aqui."
            />
          )}
        </Card>

        <Card className="p-5 lg:col-span-2">
          <SectionHeader icon={Zap} title="Destaques" />
          <dl className="space-y-4">
            <div className="flex items-center justify-between">
              <dt className="text-sm text-dim">ATS Score médio</dt>
              <dd className="font-display text-lg font-semibold">
                {analytics?.avg_ats_score != null ? `${analytics.avg_ats_score}/100` : "—"}
              </dd>
            </div>

            {analytics?.top_companies && analytics.top_companies.length > 0 && (
              <div className="space-y-2 border-t border-hair pt-3">
                <dt className="flex items-center gap-1.5 text-xs font-medium text-dim">
                  <Building2 size={12} /> Empresas mais aplicadas
                </dt>
                <dd className="space-y-2">
                  {analytics.top_companies.map((company) => (
                    <div key={company.name} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="truncate text-dim">{company.name}</span>
                        <span className="shrink-0 font-medium">{company.count}×</span>
                      </div>
                      <Meter
                        value={company.count}
                        max={analytics.top_companies[0]?.count ?? 1}
                      />
                    </div>
                  ))}
                </dd>
              </div>
            )}

            {analytics?.top_skills && analytics.top_skills.length > 0 && (
              <div className="space-y-2 border-t border-hair pt-3">
                <dt className="text-xs font-medium text-dim">Suas principais competências</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {analytics.top_skills.map((skill) => (
                    <Badge key={skill.name} tone="accent">
                      {skill.name}
                    </Badge>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </Card>
      </div>

      {timeline.length > 0 && (
        <Card className="p-5">
          <SectionHeader
            icon={TrendingUp}
            title="Atividade dos últimos 30 dias"
            description={`${timeline.reduce((sum, point) => sum + point.count, 0)} candidaturas no período`}
          />
          <TimelineChart data={timeline} />
        </Card>
      )}

      <Card className="p-5">
        <SectionHeader
          icon={Github}
          title="Importar seu perfil"
          description="Traga dados do GitHub e do LinkedIn para enriquecer as análises"
        />
        <div className="grid gap-4 md:grid-cols-2">
          <div className="surface-inset space-y-3 p-4">
            <h3 className="flex items-center gap-1.5 text-sm font-medium">
              <Github size={14} /> GitHub
            </h3>
            <div className="flex gap-2">
              <input
                value={githubUsername}
                onChange={(event) => onGithubUsernameChange(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && onImportGithub()}
                placeholder="seu-usuario"
                aria-label="Nome de usuário do GitHub"
                className="field"
              />
              <Button
                size="sm"
                onClick={onImportGithub}
                loading={importing === "github"}
                className="shrink-0"
              >
                Importar
              </Button>
            </div>
            {githubData && (
              <div className="space-y-1.5 text-xs">
                <p className="font-medium text-accent">
                  {githubData.profile?.name || githubUsername}
                </p>
                {githubData.profile?.bio && <p className="text-dim">{githubData.profile.bio}</p>}
                <p className="text-faint">{githubData.total_repos} repositórios públicos</p>
                <div className="flex flex-wrap gap-1">
                  {(githubData.skills ?? []).slice(0, 10).map((skill) => (
                    <Badge key={skill}>{skill}</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="surface-inset space-y-3 p-4">
            <h3 className="flex items-center gap-1.5 text-sm font-medium">
              <Linkedin size={14} /> Posicionamento no LinkedIn
            </h3>
            <p className="text-[11px] leading-relaxed text-faint">
              Gerado a partir do seu currículo, não do endereço do perfil — nada é inventado.
            </p>
            <div className="flex gap-2">
              <input
                value={targetRole}
                onChange={(event) => onTargetRoleChange(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && hasResume && onSuggestProfile()}
                placeholder="Cargo-alvo (opcional)"
                aria-label="Cargo-alvo"
                className="field"
              />
              <Button
                size="sm"
                onClick={onSuggestProfile}
                loading={importing === "profile"}
                disabled={!hasResume}
                className="shrink-0"
              >
                Gerar
              </Button>
            </div>

            {!hasResume && (
              <p className="text-[11px] text-[var(--warning)]">
                Envie um currículo na aba Currículos para liberar esta análise.
              </p>
            )}

            {profileSuggestion && (
              <div className="space-y-2.5 border-t border-hair pt-3 text-xs">
                {profileSuggestion.headline && (
                  <div>
                    <p className="text-[11px] font-medium text-dim">Headline sugerida</p>
                    <p className="text-accent">{profileSuggestion.headline}</p>
                  </div>
                )}
                {profileSuggestion.about && (
                  <div>
                    <p className="text-[11px] font-medium text-dim">Sobre</p>
                    <p className="whitespace-pre-wrap text-faint">{profileSuggestion.about}</p>
                  </div>
                )}
                {(profileSuggestion.suggested_roles?.length ?? 0) > 0 && (
                  <div className="space-y-1">
                    <p className="text-[11px] font-medium text-dim">
                      Cargos que sua experiência sustenta
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {profileSuggestion.suggested_roles?.map((role) => (
                        <Badge key={role} tone="info">
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {(profileSuggestion.skills?.length ?? 0) > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {profileSuggestion.skills?.slice(0, 12).map((skill) => (
                      <Badge key={skill}>{skill}</Badge>
                    ))}
                  </div>
                )}
                {(profileSuggestion.gaps?.length ?? 0) > 0 && (
                  <div className="space-y-1">
                    <p className="text-[11px] font-medium text-[var(--warning)]">
                      O que fortaleceria o perfil
                    </p>
                    <ul className="list-inside list-disc space-y-0.5 text-faint">
                      {profileSuggestion.gaps?.map((gap) => (
                        <li key={gap}>{gap}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {profileSuggestion.analysis && (
                  <p className="text-faint">{profileSuggestion.analysis}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
