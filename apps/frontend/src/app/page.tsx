"use client";

import { Rocket } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AiResultPanel, type AiResult } from "@/components/AiResultPanel";
import { AmbientBackground } from "@/components/AmbientBackground";
import { AppShell } from "@/components/AppShell";
import { LoginScreen } from "@/components/LoginScreen";
import { ToastStack } from "@/components/ui";
import { ApplicationsView } from "@/components/views/ApplicationsView";
import { CalendarView, EMPTY_EVENT_DRAFT, type EventDraft } from "@/components/views/CalendarView";
import { ChatView, type ChatMessage } from "@/components/views/ChatView";
import { DashboardView } from "@/components/views/DashboardView";
import { EMPTY_JOB_DRAFT, JobsView, type NewJobDraft } from "@/components/views/JobsView";
import { ResumesView } from "@/components/views/ResumesView";
import { SemanticView } from "@/components/views/SemanticView";
import { SettingsView } from "@/components/views/SettingsView";
import { useSession } from "@/hooks/useSession";
import { useTheme } from "@/hooks/useTheme";
import { useToast } from "@/hooks/useToast";
import { createDemoClient, IS_STATIC_DEMO } from "@/demo/client";
import { createClient } from "@/lib/api";
import type {
  Analytics,
  Application,
  ApplicationStats,
  AtsResult,
  CalendarEvent,
  CoverLetter,
  ExternalJob,
  GithubImport,
  Job,
  JobSearchResponse,
  ProfileSuggestion,
  LlmConfig,
  MatchResult,
  Notification,
  Resume,
  SemanticHit,
} from "@/lib/types";

interface InstanceMeta {
  demo_mode: boolean;
  linkedin_oauth: boolean;
}

export default function Home() {
  const session = useSession();
  const { client, user, restoring, handleApiError } = session;
  const theme = useTheme();
  const toast = useToast();

  const [tab, setTab] = useState("dashboard");
  const [meta, setMeta] = useState<InstanceMeta>({ demo_mode: false, linkedin_oauth: false });
  const [loginError, setLoginError] = useState("");

  // ── Data ────────────────────────────────────────────────────────
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [llmConfigs, setLlmConfigs] = useState<LlmConfig[]>([]);
  const [coverLetters, setCoverLetters] = useState<CoverLetter[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  // ── Job search ──────────────────────────────────────────────────
  const [source, setSource] = useState("remoteok");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<string[]>([]);
  const [jobResults, setJobResults] = useState<(Job | ExternalJob)[]>([]);
  const [sourceAvailable, setSourceAvailable] = useState(true);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [jobDraft, setJobDraft] = useState<NewJobDraft>(EMPTY_JOB_DRAFT);
  const [creatingJob, setCreatingJob] = useState(false);
  const [assistedBusy, setAssistedBusy] = useState(false);

  // ── Semantic search ─────────────────────────────────────────────
  const [semanticQuery, setSemanticQuery] = useState("");
  const [semanticResults, setSemanticResults] = useState<SemanticHit[]>([]);
  const [semanticSearching, setSemanticSearching] = useState(false);
  const [semanticSearched, setSemanticSearched] = useState(false);
  const [indexedJobs, setIndexedJobs] = useState(0);

  // ── Calendar ────────────────────────────────────────────────────
  const [eventDraft, setEventDraft] = useState<EventDraft>(EMPTY_EVENT_DRAFT);
  const [creatingEvent, setCreatingEvent] = useState(false);

  // ── AI ──────────────────────────────────────────────────────────
  const [aiResult, setAiResult] = useState<AiResult>(null);
  const [busyAction, setBusyAction] = useState("");
  const [savingCoverLetter, setSavingCoverLetter] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [language, setLanguage] = useState("pt-BR");
  const [tone, setTone] = useState("professional");

  // ── Imports ─────────────────────────────────────────────────────
  const [githubUsername, setGithubUsername] = useState("");
  const [githubData, setGithubData] = useState<GithubImport | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [profileSuggestion, setProfileSuggestion] = useState<ProfileSuggestion | null>(null);
  const [importing, setImporting] = useState("");

  // ── Chat ────────────────────────────────────────────────────────
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [chatting, setChatting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const usingLocalAnalyzer = llmConfigs.every((config) => !config.has_key);

  /** Runs an API call and reports any failure as a toast instead of silently. */
  const guard = useCallback(
    async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
      try {
        return await action();
      } catch (error) {
        toast.error(handleApiError(error));
        return undefined;
      }
    },
    [handleApiError, toast],
  );

  // Instance capabilities drive which entry points the login screen offers.
  useEffect(() => {
    if (IS_STATIC_DEMO) {
      setMeta({ demo_mode: true, linkedin_oauth: false });
      return;
    }
    createClient("")
      .get<InstanceMeta>("/meta")
      .then(setMeta)
      .catch(() => setMeta({ demo_mode: false, linkedin_oauth: false }));
  }, []);

  const refreshNotifications = useCallback(async () => {
    const [list, count] = await Promise.all([
      client.get<{ results: Notification[] }>("/notifications?limit=20"),
      client.get<{ unread_count: number }>("/notifications/unread-count"),
    ]);
    setNotifications(list.results);
    setUnreadCount(count.unread_count);
  }, [client]);

  const refreshApplications = useCallback(async () => {
    const [list, summary] = await Promise.all([
      client.get<{ results: Application[] }>("/applications/list"),
      client.get<ApplicationStats>("/applications/stats"),
    ]);
    setApplications(list.results);
    setStats(summary);
  }, [client]);

  // Load everything the shell needs once a session exists. Failures are
  // reported once rather than per-endpoint, so a cold backend does not
  // produce six identical toasts.
  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    (async () => {
      setLoadingData(true);
      try {
        const [analyticsData, applicationList, applicationStats, resumeList, eventList, configs] =
          await Promise.all([
            client.get<Analytics>("/analytics/overview"),
            client.get<{ results: Application[] }>("/applications/list"),
            client.get<ApplicationStats>("/applications/stats"),
            client.get<{ results: Resume[] }>("/resumes/list"),
            client.get<{ events: CalendarEvent[] }>("/calendar"),
            client.get<{ configs: LlmConfig[] }>("/settings/llm"),
          ]);
        if (cancelled) return;
        setAnalytics(analyticsData);
        setApplications(applicationList.results);
        setStats(applicationStats);
        setResumes(resumeList.results);
        setEvents(eventList.events);
        setLlmConfigs(configs.configs);
        await refreshNotifications();

        // Cheap probe purely for the "N vagas indexadas" counter, which would
        // otherwise read zero until the user ran their first search.
        const probe = await client.get<{ indexed_jobs: number }>(
          "/search/semantic?q=engenharia&limit=1",
        );
        if (!cancelled) setIndexedJobs(probe.indexed_jobs);
      } catch (error) {
        if (!cancelled) toast.error(handleApiError(error));
      } finally {
        if (!cancelled) setLoadingData(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // `toast` and `handleApiError` are stable callbacks; re-running on them
    // would refetch the whole dashboard on every toast.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, client, refreshNotifications]);

  // ── Auth actions ────────────────────────────────────────────────

  async function login(email: string, password: string) {
    setLoginError("");
    try {
      await session.login(email, password);
    } catch (error) {
      setLoginError(handleApiError(error));
    }
  }

  async function register(email: string, password: string, fullName: string) {
    setLoginError("");
    try {
      await session.register(email, password, fullName);
    } catch (error) {
      setLoginError(handleApiError(error));
    }
  }

  async function loginWithLinkedIn() {
    setLoginError("");
    try {
      const api = IS_STATIC_DEMO ? createDemoClient() : createClient("");
      const { auth_url } = await api.get<{ auth_url: string }>("/auth/linkedin/login");
      window.location.href = auth_url;
    } catch (error) {
      setLoginError(handleApiError(error));
    }
  }

  async function loginAsDemo() {
    setLoginError("");
    try {
      await session.loginAsDemo();
    } catch (error) {
      setLoginError(handleApiError(error));
    }
  }

  // ── Jobs ────────────────────────────────────────────────────────

  async function searchJobs() {
    setSearching(true);
    setSearched(true);
    const terms = [query.trim(), ...filters].filter(Boolean).join(" ");
    const path =
      source === "local"
        ? `/jobs?query=${encodeURIComponent(terms)}&page=1`
        : `/jobs/${source}?q=${encodeURIComponent(terms)}&page=1`;

    const response = await guard(() =>
      client.get<JobSearchResponse<Job | ExternalJob>>(path),
    );
    setJobResults(response?.results ?? []);
    setSourceAvailable(response?.available ?? true);
    setSearching(false);
  }

  async function assistApplication(job: Job | ExternalJob) {
    const candidate = job as ExternalJob;
    const vacancy = {
      title: candidate.position || candidate.title || candidate.name || "",
      company: candidate.company || candidate.company_name || "",
      description: job.description || "",
      url: candidate.url || candidate.apply_url || (job as Job).apply_url || "",
    };
    if (!vacancy.url) { toast.error("Esta vaga não possui link."); return; }
    if (resumes.length === 0) {
      toast.error("Envie seu currículo PDF na aba Currículos antes de se candidatar.");
      setTab("resumes");
      return;
    }
    // The local companion owns the visible browser session, not the backend.
    // Explicit click authorizes opening and filling; any final submission is
    // only recorded when the external platform independently confirms it.
    setAssistedBusy(true);
    try {
      if (vacancy.description.length >= 30) {
        const prep = await guard(() => client.post<{
          match_score: number; keywords_supported_by_resume: string[];
          missing_skills_not_to_claim: string[]; cover_letter_draft: string;
        }>("/ai/prepare-external", { resume_id: resumes[0].id, job: vacancy }));
        if (prep) {
          toast.success("Compatibilidade: " + prep.match_score +
            "%. Palavras-chave do seu currículo: " +
            (prep.keywords_supported_by_resume.join(", ") || "não identificadas") +
            ". Lacunas: " + (prep.missing_skills_not_to_claim.join(", ") || "nenhuma"));
        }
      }
      const response = await fetch("http://127.0.0.1:8765/apply", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job: vacancy, profile: {}, consent: true }),
      });
      const outcome = await response.json() as { state?: string; reason?: string; error?: string };
      if (!response.ok) throw new Error(outcome.error || "Agente local indisponível.");
      toast.success(outcome.reason || "O navegador de candidatura foi aberto.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message +
        " Inicie o companion na pasta companion com npm start." : "Não foi possível iniciar o agente.");
    } finally { setAssistedBusy(false); }
  }

  async function createJob() {
    if (!jobDraft.title.trim() || !jobDraft.company_name.trim()) {
      toast.error("Informe ao menos o título e a empresa.");
      return;
    }
    setCreatingJob(true);
    const created = await guard(() => client.post<Job>("/jobs", jobDraft));
    if (created) {
      toast.success("Vaga cadastrada.");
      setJobDraft(EMPTY_JOB_DRAFT);
      // Index it so it becomes reachable from semantic search straight away.
      await guard(() => client.post(`/search/index-job/${created.id}`));
      setSource("local");
      setQuery("");
      setFilters([]);
      const list = await guard(() => client.get<JobSearchResponse<Job>>("/jobs?query=&page=1"));
      setJobResults(list?.results ?? []);
      setSearched(true);
      setSourceAvailable(true);
    }
    setCreatingJob(false);
  }

  async function runSemanticSearch() {
    if (!semanticQuery.trim()) return;
    setSemanticSearching(true);
    setSemanticSearched(true);
    const response = await guard(() =>
      client.get<{ results: SemanticHit[]; indexed_jobs: number }>(
        `/search/semantic?q=${encodeURIComponent(semanticQuery)}&limit=12`,
      ),
    );
    setSemanticResults(response?.results ?? []);
    setIndexedJobs(response?.indexed_jobs ?? 0);
    setSemanticSearching(false);
  }

  // ── Calendar ────────────────────────────────────────────────────

  async function createEvent() {
    if (!eventDraft.title.trim()) {
      toast.error("Informe um título para o evento.");
      return;
    }
    setCreatingEvent(true);
    const created = await guard(() => client.post("/calendar", eventDraft));
    if (created) {
      toast.success("Evento criado.");
      setEventDraft(EMPTY_EVENT_DRAFT);
      const list = await guard(() => client.get<{ events: CalendarEvent[] }>("/calendar"));
      if (list) setEvents(list.events);
    }
    setCreatingEvent(false);
  }

  async function deleteEvent(id: string) {
    const done = await guard(() => client.delete(`/calendar/${id}`));
    if (done !== undefined) {
      setEvents((current) => current.filter((event) => event.id !== id));
      toast.success("Evento removido.");
    }
  }

  async function updateEventStatus(id: string, status: string) {
    const done = await guard(() => client.patch(`/calendar/${id}`, { status }));
    if (done !== undefined) {
      setEvents((current) =>
        current.map((event) => (event.id === id ? { ...event, status } : event)),
      );
    }
  }

  // ── AI actions ──────────────────────────────────────────────────

  async function runAiAction(actionId: string, application: Application) {
    const payload = { job_id: application.job_id, resume_id: application.resume_id };
    setBusyAction(`${actionId}:${application.id}`);

    try {
      if (actionId === "match") {
        const data = await guard(() => client.post<MatchResult>("/ai/match", payload));
        if (data) setAiResult({ kind: "match", data });
      } else if (actionId === "ats") {
        const data = await guard(() => client.post<AtsResult>("/ai/ats-score", payload));
        if (data) setAiResult({ kind: "ats", data });
      } else if (actionId === "cover") {
        const data = await guard(() =>
          client.post<{ cover_letter: string; id: string }>("/ai/cover-letter", {
            ...payload,
            language,
            tone,
          }),
        );
        if (data) setAiResult({ kind: "cover", id: data.id, content: data.cover_letter });
      } else if (actionId === "tailor") {
        const data = await guard(() =>
          client.post<{ tailored_resume: string }>("/ai/tailor-resume", payload),
        );
        if (data) {
          setAiResult({
            kind: "resume",
            content: data.tailored_resume,
            title: application.job_title,
          });
        }
      } else if (actionId === "auto") {
        const data = await guard(() =>
          client.post<{ cover_letter: string; tailored_resume: string }>("/ai/auto-apply", payload),
        );
        if (data) {
          toast.success("Candidatura automática registrada.");
          setAiResult({
            kind: "resume",
            content: data.tailored_resume,
            title: application.job_title,
          });
          await guard(refreshApplications);
        }
      }
    } finally {
      setBusyAction("");
    }
  }

  async function updateApplicationStatus(id: string, status: string) {
    const updated = await guard(() =>
      client.patch<Application>(`/applications/${id}/status`, { status }),
    );
    if (updated) {
      setApplications((current) =>
        current.map((application) =>
          application.id === id ? { ...application, status: updated.status } : application,
        ),
      );
      const fresh = await guard(() => client.get<Analytics>("/analytics/overview"));
      if (fresh) setAnalytics(fresh);
      await guard(refreshApplications);
    }
  }

  async function loadCoverLetters() {
    const list = await guard(() => client.get<CoverLetter[]>("/cover-letters"));
    if (list) setCoverLetters(list);
  }

  async function saveCoverLetter(id: string, content: string) {
    setSavingCoverLetter(true);
    const saved = await guard(() => client.patch(`/cover-letters/${id}`, { content }));
    if (saved !== undefined) {
      setAiResult({ kind: "cover", id, content });
      toast.success("Carta atualizada.");
    }
    setSavingCoverLetter(false);
  }

  async function deleteCoverLetter(id: string) {
    const done = await guard(() => client.delete(`/cover-letters/${id}`));
    if (done !== undefined) {
      setCoverLetters((current) => current.filter((letter) => letter.id !== id));
      toast.success("Carta removida.");
    }
  }

  // ── Imports, resumes, chat ──────────────────────────────────────

  async function importGithub() {
    if (!githubUsername.trim()) return;
    setImporting("github");
    const data = await guard(() =>
      client.post<GithubImport>("/ai/github/import", { username: githubUsername.trim() }),
    );
    if (data) {
      setGithubData(data);
      toast.success(`Perfil de ${githubUsername} importado.`);
    }
    setImporting("");
  }

  async function suggestProfile() {
    setImporting("profile");
    const data = await guard(() =>
      client.post<ProfileSuggestion>("/ai/linkedin/analyze", {
        target_role: targetRole.trim(),
      }),
    );
    if (data) {
      setProfileSuggestion(data);
      toast.success("Sugestões geradas a partir do seu currículo.");
    }
    setImporting("");
  }

  async function uploadResume(formData: FormData) {
    setUploading(true);
    const created = await guard(() => client.upload<Resume>("/resumes/upload", formData));
    if (created) {
      toast.success("Currículo enviado. O ATS Score aparece em instantes.");
      const list = await guard(() => client.get<{ results: Resume[] }>("/resumes/list"));
      if (list) setResumes(list.results);
    }
    setUploading(false);
  }

  async function sendChat() {
    const message = chatDraft.trim();
    if (!message) return;

    setChatHistory((current) => [...current, { role: "user", text: message }]);
    setChatDraft("");
    setChatting(true);

    const response = await guard(() =>
      client.post<{ response: string }>("/ai/chat", { message }),
    );
    if (response) {
      setChatHistory((current) => [...current, { role: "assistant", text: response.response }]);
    }
    setChatting(false);
  }

  async function markNotificationRead(id: string) {
    const done = await guard(() => client.patch(`/notifications/${id}/read`));
    if (done !== undefined) await guard(refreshNotifications);
  }

  // ── Render ──────────────────────────────────────────────────────

  if (restoring) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <AmbientBackground />
        <div className="flex items-center gap-2.5 text-sm text-faint">
          <Rocket size={16} className="animate-breathe text-accent" />
          Carregando…
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <LoginScreen
          onLogin={login}
          onRegister={register}
          onLinkedIn={loginWithLinkedIn}
          onDemo={loginAsDemo}
          demoAvailable={meta.demo_mode}
          error={loginError}
        />
        <ToastStack toasts={toast.toasts} onDismiss={toast.dismiss} />
      </>
    );
  }

  return (
    <>
      <AmbientBackground />
      <AppShell
        user={user}
        activeTab={tab}
        onTabChange={setTab}
        theme={theme.theme}
        onToggleTheme={theme.toggle}
        onLogout={session.logout}
        notifications={notifications}
        unreadCount={unreadCount}
        onMarkRead={markNotificationRead}
        offline={usingLocalAnalyzer}
      >
        {tab === "dashboard" && (
          <DashboardView
            analytics={analytics}
            stats={stats}
            loading={loadingData}
            githubUsername={githubUsername}
            onGithubUsernameChange={setGithubUsername}
            githubData={githubData}
            onImportGithub={importGithub}
            targetRole={targetRole}
            onTargetRoleChange={setTargetRole}
            profileSuggestion={profileSuggestion}
            onSuggestProfile={suggestProfile}
            hasResume={resumes.length > 0}
            importing={importing}
          />
        )}

        {tab === "jobs" && (
          <JobsView
            source={source}
            onSourceChange={setSource}
            query={query}
            onQueryChange={setQuery}
            filters={filters}
            onToggleFilter={(filter) =>
              setFilters((current) =>
                current.includes(filter)
                  ? current.filter((item) => item !== filter)
                  : [...current, filter],
              )
            }
            onSearch={searchJobs}
            searching={searching}
            results={jobResults}
            sourceAvailable={sourceAvailable}
            searched={searched}
            draft={jobDraft}
            onDraftChange={setJobDraft}
            onCreateJob={createJob}
            creating={creatingJob}
            onAssist={assistApplication}
            assistedBusy={assistedBusy}
          />
        )}

        {tab === "semantic" && (
          <SemanticView
            query={semanticQuery}
            onQueryChange={setSemanticQuery}
            onSearch={runSemanticSearch}
            searching={semanticSearching}
            results={semanticResults}
            searched={semanticSearched}
            indexedJobs={indexedJobs}
          />
        )}

        {tab === "applications" && (
          <ApplicationsView
            applications={applications}
            loading={loadingData}
            busyAction={busyAction}
            onRunAction={runAiAction}
            onUpdateStatus={updateApplicationStatus}
            language={language}
            onLanguageChange={setLanguage}
            tone={tone}
            onToneChange={setTone}
            coverLetters={coverLetters}
            showHistory={showHistory}
            onToggleHistory={() => {
              const next = !showHistory;
              setShowHistory(next);
              if (next) void loadCoverLetters();
            }}
            onViewCoverLetter={(letter) =>
              setAiResult({ kind: "cover", id: letter.id, content: letter.content })
            }
            onDeleteCoverLetter={deleteCoverLetter}
          />
        )}

        {tab === "calendar" && (
          <CalendarView
            events={events}
            draft={eventDraft}
            onDraftChange={setEventDraft}
            onCreate={createEvent}
            onDelete={deleteEvent}
            onUpdateStatus={updateEventStatus}
            creating={creatingEvent}
          />
        )}

        {tab === "resumes" && (
          <ResumesView
            resumes={resumes}
            onUpload={uploadResume}
            uploading={uploading}
            onOpen={(resume) =>
              setAiResult({
                kind: "resume",
                content: resume.content_preview,
                title: resume.title,
              })
            }
          />
        )}

        {tab === "chat" && (
          <ChatView
            history={chatHistory}
            draft={chatDraft}
            onDraftChange={setChatDraft}
            onSend={sendChat}
            sending={chatting}
            offline={usingLocalAnalyzer}
          />
        )}

        {tab === "settings" && (
          <SettingsView
            configs={llmConfigs}
            saving={busyAction}
            onSave={async (providerId, draft) => {
              setBusyAction(providerId);
              const saved = await guard(() =>
                client.post("/settings/llm", {
                  provider_name: providerId,
                  api_key: draft.apiKey,
                  base_url: draft.baseUrl,
                  model: draft.model,
                }),
              );
              if (saved !== undefined) {
                toast.success("Provedor configurado.");
                const configs = await guard(() =>
                  client.get<{ configs: LlmConfig[] }>("/settings/llm"),
                );
                if (configs) setLlmConfigs(configs.configs);
              }
              setBusyAction("");
            }}
          />
        )}
      </AppShell>

      <AiResultPanel
        result={aiResult}
        onClose={() => setAiResult(null)}
        onSaveCoverLetter={saveCoverLetter}
        savingCoverLetter={savingCoverLetter}
      />

      <ToastStack toasts={toast.toasts} onDismiss={toast.dismiss} />
    </>
  );
}
