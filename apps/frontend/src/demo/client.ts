/**
 * In-browser API implementation for the static demo.
 *
 * The published demo has no backend: it is the real frontend served as static
 * files. This module answers the same routes the API does, from fixtures that
 * were captured from a running instance — so what a visitor sees is what the
 * application actually returns, not hand-written mock data.
 *
 * Writes are applied to in-memory state so the interface behaves normally;
 * nothing survives a reload, and the UI says so.
 */
import type { ApiClient } from "@/lib/api";
import { ApiError } from "@/lib/api";
import type {
  Analytics,
  Application,
  ApplicationStats,
  CalendarEvent,
  CoverLetter,
  Job,
  LlmConfig,
  Notification,
  Resume,
  SemanticHit,
} from "@/lib/types";
import fixtures from "./fixtures.json";

interface AiFixture {
  match: unknown;
  ats: unknown;
  cover: { cover_letter: string; id: string };
  tailor: { tailored_resume: string };
}

interface Fixtures {
  analytics: Analytics;
  applications: { results: Application[] };
  applicationStats: ApplicationStats;
  resumes: { results: Resume[] };
  calendar: { events: CalendarEvent[] };
  notifications: { results: Notification[] };
  unreadCount: { unread_count: number };
  llmConfigs: { configs: LlmConfig[] };
  coverLetters: CoverLetter[];
  localJobs: { results: Job[] };
  ai: Record<string, AiFixture>;
  profileSuggestion: Record<string, unknown>;
  semantic: Record<string, { results: SemanticHit[]; indexed_jobs: number }>;
}

const data = fixtures as unknown as Fixtures;

/** Mutable session state, reset on every page load. */
interface DemoState {
  applications: Application[];
  events: CalendarEvent[];
  notifications: Notification[];
  coverLetters: CoverLetter[];
  jobs: Job[];
}

function initialState(): DemoState {
  return {
    applications: structuredClone(data.applications.results),
    events: structuredClone(data.calendar.events),
    notifications: structuredClone(data.notifications.results),
    coverLetters: structuredClone(data.coverLetters),
    jobs: structuredClone(data.localJobs.results),
  };
}

let state = initialState();

const LATENCY_MS = 260;

function delay<T>(value: T): Promise<T> {
  // A little latency so loading states and skeletons are actually visible,
  // rather than the whole UI snapping into place instantly.
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS));
}

function unreadCount(): number {
  return state.notifications.filter((notification) => notification.status !== "read").length;
}

/** Recompute the dashboard from live state so status changes are reflected. */
function analytics(): Analytics {
  const total = state.applications.length;
  const share = (n: number) => (total > 0 ? Math.round((n / total) * 1000) / 10 : 0);
  const countWhere = (predicate: (a: Application) => boolean) =>
    state.applications.filter(predicate).length;

  const interviews = countWhere((a) =>
    ["hr_interview", "technical_interview", "offer"].includes(a.status),
  );
  const offers = countWhere((a) => a.status === "offer");
  const rejected = countWhere((a) => a.status === "rejected");
  const responded = countWhere((a) => a.status !== "applied");

  const companies = new Map<string, number>();
  for (const application of state.applications) {
    if (application.company) {
      companies.set(application.company, (companies.get(application.company) ?? 0) + 1);
    }
  }

  return {
    ...data.analytics,
    total_applications: total,
    interviews,
    offers,
    rejected,
    interview_rate: share(interviews),
    offer_rate: share(offers),
    rejection_rate: share(rejected),
    response_rate: share(responded),
    top_companies: [...companies.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5),
  };
}

function applicationStats(): ApplicationStats {
  const byStatus: Record<string, number> = {};
  for (const application of state.applications) {
    byStatus[application.status] = (byStatus[application.status] ?? 0) + 1;
  }
  return { total: state.applications.length, by_status: byStatus };
}

/**
 * Rank the indexed jobs for a query the fixtures do not cover.
 *
 * Deliberately the same idea as the backend's local vectorizer — shared
 * vocabulary means similarity — just small enough to run inline.
 */
function rankJobs(query: string): { results: SemanticHit[]; indexed_jobs: number } {
  const indexed = Object.values(data.semantic)[0]?.indexed_jobs ?? state.jobs.length;
  const terms = new Set(tokenize(query));
  if (terms.size === 0) return { results: [], indexed_jobs: indexed };

  const results = state.jobs
    .map((job) => {
      const haystack = new Set(
        tokenize(`${job.title} ${job.company} ${job.location} ${job.description}`),
      );
      const overlap = [...terms].filter((term) => haystack.has(term)).length;
      return {
        id: job.id,
        title: job.title,
        company: job.company,
        location: job.location,
        description: job.description,
        apply_url: job.apply_url,
        score: Math.round((overlap / terms.size) * 1000) / 10,
        match: job.description.slice(0, 200),
      };
    })
    .filter((hit) => hit.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 12);

  return { results, indexed_jobs: indexed };
}

function tokenize(text: string): string[] {
  return (text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .match(/[a-z0-9][a-z0-9+#._-]*/g)
    ?.map((token) => token.replace(/[._-]+$/, ""))
    .filter((token) => token.length > 2) ?? [];
}

function aiFor(applicationId: string): AiFixture {
  const fixture = data.ai[applicationId];
  if (!fixture) {
    throw new ApiError(
      "Esta combinação não está pré-calculada na demonstração. " +
        "Rode o projeto localmente para analisar qualquer vaga.",
      404,
    );
  }
  return fixture;
}

function applicationByPayload(body: unknown): Application {
  const payload = body as { job_id?: string; resume_id?: string };
  const match = state.applications.find(
    (application) =>
      application.job_id === payload?.job_id && application.resume_id === payload?.resume_id,
  );
  if (!match) throw new ApiError("Candidatura não encontrada na demonstração.", 404);
  return match;
}

const NOT_AVAILABLE =
  "Indisponível na demonstração estática — esta ação precisa do backend. " +
  "Rode `docker compose up -d` para a versão completa.";

function get(path: string): unknown {
  if (path.startsWith("/analytics/overview")) return analytics();
  if (path.startsWith("/applications/list")) return { results: state.applications };
  if (path.startsWith("/applications/stats")) return applicationStats();
  if (path.startsWith("/resumes/list")) return data.resumes;
  if (path.startsWith("/calendar")) return { events: state.events };
  if (path.startsWith("/notifications/unread-count")) return { unread_count: unreadCount() };
  if (path.startsWith("/notifications")) return { results: state.notifications };
  if (path.startsWith("/settings/llm")) return data.llmConfigs;
  if (path.startsWith("/cover-letters")) return state.coverLetters;
  if (path.startsWith("/auth/me")) {
    return { id: "demo", email: "demo@jobpilot.ai", full_name: "Lucas Oliveira (Demo)" };
  }

  if (path.startsWith("/search/semantic")) {
    const query = decodeURIComponent(new URLSearchParams(path.split("?")[1] ?? "").get("q") ?? "");
    return data.semantic[query] ?? rankJobs(query);
  }

  if (path.startsWith("/jobs?")) return { results: state.jobs, available: true };
  if (path.startsWith("/jobs/")) {
    // External boards need a live HTTP call, which a static page cannot make.
    return { results: [], source: "demo", available: false };
  }

  throw new ApiError(NOT_AVAILABLE, 501);
}

function post(path: string, body: unknown): unknown {
  if (path.startsWith("/auth/demo")) {
    state = initialState();
    return {
      user_id: "demo",
      email: "demo@jobpilot.ai",
      full_name: "Lucas Oliveira (Demo)",
      token: "demo-token",
    };
  }
  if (path.startsWith("/auth/logout")) return { message: "Logged out" };

  if (path.startsWith("/ai/match")) return aiFor(applicationByPayload(body).id).match;
  if (path.startsWith("/ai/ats-score")) return aiFor(applicationByPayload(body).id).ats;
  if (path.startsWith("/ai/cover-letter")) return aiFor(applicationByPayload(body).id).cover;
  if (path.startsWith("/ai/tailor-resume")) return aiFor(applicationByPayload(body).id).tailor;
  if (path.startsWith("/ai/auto-apply")) {
    const fixture = aiFor(applicationByPayload(body).id);
    return {
      application_id: "demo",
      tailored_resume: fixture.tailor.tailored_resume,
      cover_letter: fixture.cover.cover_letter,
      status: "applied",
    };
  }
  if (path.startsWith("/ai/linkedin/analyze")) {
    const target = (body as { target_role?: string })?.target_role?.trim();
    const suggestion = data.profileSuggestion as { headline?: string };
    // The headline is the only field the target role changes, so it can be
    // reflected without another precomputed variant per role.
    return target
      ? { ...suggestion, headline: `${target} · ${(suggestion.headline ?? "").split(" · ").slice(1).join(" · ")}` }
      : suggestion;
  }

  if (path.startsWith("/ai/chat")) {
    return {
      response:
        "O chat precisa de um provedor de IA configurado, que a demonstração estática não " +
        "tem. Tudo que não depende de geração de texto livre — compatibilidade, ATS Score, " +
        "carta e currículo direcionado — está funcionando aqui ao lado.",
      provider: "demo",
    };
  }

  if (path.startsWith("/calendar")) {
    const draft = body as Partial<CalendarEvent>;
    const event: CalendarEvent = {
      id: `demo-${Date.now()}`,
      title: draft.title ?? "Novo evento",
      event_type: draft.event_type ?? "interview",
      date: draft.date || null,
      notes: draft.notes ?? "",
      location: draft.location ?? "",
      status: "scheduled",
    };
    state.events = [...state.events, event];
    return event;
  }

  throw new ApiError(NOT_AVAILABLE, 501);
}

function patch(path: string, body: unknown): unknown {
  const statusMatch = path.match(/^\/applications\/([^/]+)\/status$/);
  if (statusMatch) {
    const status = (body as { status: Application["status"] }).status;
    state.applications = state.applications.map((application) =>
      application.id === statusMatch[1] ? { ...application, status } : application,
    );
    const updated = state.applications.find((a) => a.id === statusMatch[1]);
    if (!updated) throw new ApiError("Candidatura não encontrada.", 404);
    return updated;
  }

  const readMatch = path.match(/^\/notifications\/([^/]+)\/read$/);
  if (readMatch) {
    state.notifications = state.notifications.map((notification) =>
      notification.id === readMatch[1] ? { ...notification, status: "read" } : notification,
    );
    return { status: "read" };
  }

  const eventMatch = path.match(/^\/calendar\/([^/]+)$/);
  if (eventMatch) {
    const patchBody = body as Partial<CalendarEvent>;
    state.events = state.events.map((event) =>
      event.id === eventMatch[1] ? { ...event, ...patchBody } : event,
    );
    return { status: "ok" };
  }

  const letterMatch = path.match(/^\/cover-letters\/([^/]+)$/);
  if (letterMatch) {
    const content = (body as { content: string }).content;
    state.coverLetters = state.coverLetters.map((letter) =>
      letter.id === letterMatch[1] ? { ...letter, content } : letter,
    );
    return { status: "ok" };
  }

  throw new ApiError(NOT_AVAILABLE, 501);
}

function remove(path: string): unknown {
  const eventMatch = path.match(/^\/calendar\/([^/]+)$/);
  if (eventMatch) {
    state.events = state.events.filter((event) => event.id !== eventMatch[1]);
    return { status: "deleted" };
  }

  const letterMatch = path.match(/^\/cover-letters\/([^/]+)$/);
  if (letterMatch) {
    state.coverLetters = state.coverLetters.filter((letter) => letter.id !== letterMatch[1]);
    return { status: "deleted" };
  }

  throw new ApiError(NOT_AVAILABLE, 501);
}

/** An ApiClient that never touches the network. */
export function createDemoClient(): ApiClient {
  return {
    get: <T,>(path: string) => delay(get(path) as T),
    post: <T,>(path: string, body?: unknown) => delay(post(path, body) as T),
    patch: <T,>(path: string, body?: unknown) => delay(patch(path, body) as T),
    delete: <T,>(path: string) => delay(remove(path) as T),
    upload: <T,>() =>
      Promise.reject<T>(
        new ApiError(
          "Upload de currículo precisa do backend. Rode o projeto localmente para testar.",
          501,
        ),
      ),
  };
}

/** True when this build was produced for the static demo. */
export const IS_STATIC_DEMO = process.env.NEXT_PUBLIC_STATIC_DEMO === "true";
