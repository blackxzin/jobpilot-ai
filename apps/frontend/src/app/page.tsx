"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [token, setToken] = useState("");
  const [tab, setTab] = useState("dashboard");
  const [msg, setMsg] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");

  const [apps, setApps] = useState<any[]>([]);
  const [resumes, setResumes] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchSource, setSearchSource] = useState("remoteok");
  const [showLogin, setShowLogin] = useState(true);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPass, setLoginPass] = useState("");

  // LLM config
  const [llmConfigs, setLlmConfigs] = useState<any[]>([]);
  const [editingProvider, setEditingProvider] = useState("");
  const [editKey, setEditKey] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editModel, setEditModel] = useState("");

  // AI analysis
  const [analyzing, setAnalyzing] = useState<string>("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [coverLetter, setCoverLetter] = useState("");

  // LinkedIn & GitHub
  const [githubUsername, setGithubUsername] = useState("");
  const [githubData, setGithubData] = useState<any>(null);
  const [linkedinData, setLinkedinData] = useState<any>(null);
  const [importing, setImporting] = useState(false);

  const api = (path: string, opts?: any) =>
    fetch(`/api/v1${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts?.headers },
    });

  async function doLogin() {
    const email = loginEmail || "user@jobpilot.ai";
    const pass = loginPass || "jobpilot123";
    let r = await api("/auth/register", { method: "POST", body: JSON.stringify({ email, password: pass, full_name: email.split("@")[0] }) });
    if (!r.ok) r = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password: pass }) });
    if (r.ok) { const d = await r.json(); setToken(d.token); setShowLogin(false); setMsg(""); }
    else setMsg("Erro ao entrar");
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setToken(""); setShowLogin(true); setApps([]); setResumes([]);
  }

  async function searchJobs() {
    setSearching(true);
    try {
      const r = await api(`/jobs/${searchSource}?q=${encodeURIComponent(searchQuery)}&page=1`);
      if (r.ok) { const d = await r.json(); setSearchResults(d.results || []); }
    } catch {}
    setSearching(false);
  }

  async function fetchApps() {
    const r = await api("/applications/list");
    if (r.ok) setApps((await r.json()).results);
    const s = await api("/applications/stats");
    if (s.ok) setStats(await s.json());
  }

  async function fetchResumes() {
    const r = await api("/resumes/list");
    if (r.ok) setResumes((await r.json()).results);
  }

  async function fetchLlmConfigs() {
    const r = await api("/settings/llm");
    if (r.ok) setLlmConfigs((await r.json()).configs);
  }

  useEffect(() => { if (token) { fetchApps(); fetchResumes(); fetchLlmConfigs(); } }, [token]);

  async function uploadResume(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const r = await fetch(`/api/v1/resumes/upload`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd });
    if (r.ok) { setMsg("Currículo enviado!"); fetchResumes(); } else setMsg("Erro no upload");
  }

  async function updateStatus(appId: string, status: string) {
    await api(`/applications/${appId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    fetchApps();
  }

  async function saveLlmConfig(providerName: string) {
    const body: any = { provider_name: providerName, api_key: editKey, base_url: editUrl, model: editModel };
    const r = await api("/settings/llm", { method: "POST", body: JSON.stringify(body) });
    if (r.ok) { setMsg(`${providerName} configurado!`); setEditingProvider(""); setEditKey(""); setEditUrl(""); setEditModel(""); fetchLlmConfigs(); }
    else setMsg("Erro ao salvar");
  }

  async function importGithub() {
    if (!githubUsername) return;
    setImporting(true);
    const r = await api("/ai/github/import", { method: "POST", body: JSON.stringify({ username: githubUsername }) });
    if (r.ok) { const d = await r.json(); setGithubData(d); setMsg("GitHub importado!"); }
    else setMsg("Erro ao importar GitHub");
    setImporting(false);
  }

  async function analyzeLinkedin() {
    if (!linkedinUrl) return;
    setImporting(true);
    const r = await api("/ai/linkedin/analyze", { method: "POST", body: JSON.stringify({ url: linkedinUrl }) });
    if (r.ok) { const d = await r.json(); setLinkedinData(d); setAnalysisResult(d); setMsg("LinkedIn analisado!"); }
    else setMsg("Erro ao analisar LinkedIn");
    setImporting(false);
  }

  async function runMatching(appId: string, jobId: string, resumeId: string) {
    setAnalyzing(appId);
    setCoverLetter("");
    setAnalysisResult(null);
    const r = await api("/ai/match", { method: "POST", body: JSON.stringify({ job_id: jobId, resume_id: resumeId }) });
    if (r.ok) setAnalysisResult(await r.json());
    else setMsg("Erro na análise");
    setAnalyzing("");
  }

  async function runAts(resumeId: string, jobId: string) {
    setAnalyzing("ats");
    setAnalysisResult(null);
    setCoverLetter("");
    const r = await api("/ai/ats-score", { method: "POST", body: JSON.stringify({ job_id: jobId, resume_id: resumeId }) });
    if (r.ok) setAnalysisResult(await r.json());
    else setMsg("Erro no ATS");
    setAnalyzing("");
  }

  async function runCoverLetter(resumeId: string, jobId: string) {
    setAnalyzing("cover");
    setAnalysisResult(null);
    setCoverLetter("");
    const r = await api("/ai/cover-letter", { method: "POST", body: JSON.stringify({ job_id: jobId, resume_id: resumeId }) });
    if (r.ok) { const d = await r.json(); setCoverLetter(d.cover_letter); }
    else setMsg("Erro na carta");
    setAnalyzing("");
  }

  if (showLogin) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-emerald-400">JobPilot AI</h1>
            <p className="text-zinc-400 text-sm mt-1">Copiloto de carreira inteligente</p>
          </div>
          <div className="bg-zinc-900 rounded-xl p-6 space-y-3 border border-zinc-800">
            <input value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="Email (opcional)" className="w-full bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700" />
            <input value={loginPass} onChange={e => setLoginPass(e.target.value)} type="password" placeholder="Senha (opcional)" className="w-full bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700" />
            <button onClick={doLogin} className="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-lg font-medium text-sm">Entrar</button>
            <p className="text-xs text-zinc-500 text-center">Deixe em branco para entrar rápido</p>
            {msg && <p className="text-sm text-center text-red-400">{msg}</p>}
          </div>
        </div>
      </div>
    );
  }

  const tabs = ["dashboard", "jobs", "applications", "resumes", "ia"];
  const sources = [
    { id: "remoteok", name: "RemoteOK", desc: "Vagas remotas mundo todo" },
    { id: "programathor", name: "Programathor", desc: "Vagas Brasil tech" },
    { id: "geekhunter", name: "GeekHunter", desc: "Vagas Brasil tech" },
    { id: "gupy", name: "Gupy", desc: "Vagas Brasil geral" },
  ];

  const llmProviders = [
    { id: "openai", name: "OpenAI", icon: "🤖", models: "gpt-4o, gpt-4o-mini", needs_url: false },
    { id: "anthropic", name: "Anthropic Claude", icon: "🟣", models: "claude-sonnet-4, claude-haiku-3.5", needs_url: false },
    { id: "gemini", name: "Google Gemini", icon: "🔵", models: "gemini-2.0-flash, gemini-2.0-pro", needs_url: false },
    { id: "nvidia_nim", name: "NVIDIA NIM", icon: "🟢", models: "nvidia/llama-3.3-70b-instruct", needs_url: true },
    { id: "ollama", name: "Ollama (local)", icon: "🦙", models: "llama3.1, mistral, qwen2", needs_key: false },
    { id: "openrouter", name: "OpenRouter", icon: "🔀", models: "openai/gpt-4o, meta-llama/llama-3.1", needs_url: false },
  ];

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="text-emerald-400 font-bold text-lg">JobPilot AI</span>
          <div className="flex items-center gap-4">
            <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
              {tabs.map(t => (
                <button key={t} onClick={() => setTab(t)} className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize ${tab === t ? "bg-emerald-600 text-white" : "text-zinc-400 hover:text-white"}`}>
                  {t === "ia" ? "🤖 IA" : t}
                </button>
              ))}
            </div>
            <button onClick={logout} className="text-xs text-zinc-400 hover:text-red-400">Sair</button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-4 space-y-6">
        {msg && <div className="bg-emerald-900/50 border border-emerald-700 text-emerald-300 px-4 py-2 rounded-lg text-sm">{msg}</div>}

        {/* ANALYSIS MODAL */}
        {(analysisResult || coverLetter) && (
          <div className="bg-zinc-900 rounded-xl p-6 border border-emerald-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">
                {analysisResult?.compatibility_score !== undefined ? "🎯 Resultado do Matching" :
                 analysisResult?.score !== undefined ? "📊 ATS Score" : "✉️ Carta de Apresentação"}
              </h2>
              <button onClick={() => { setAnalysisResult(null); setCoverLetter(""); }} className="text-zinc-500 hover:text-white text-xs">✕ Fechar</button>
            </div>

            {analysisResult?.compatibility_score !== undefined && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className={`text-4xl font-bold ${analysisResult.compatibility_score >= 70 ? "text-emerald-400" : analysisResult.compatibility_score >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                    {analysisResult.compatibility_score}%
                  </div>
                  <p className="text-sm text-zinc-400">Compatibilidade com a vaga</p>
                </div>
                {analysisResult.match_reasons?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">Análise:</p>
                    <div className="space-y-1">{analysisResult.match_reasons.map((r: any, i: number) => (
                      <div key={i} className={`text-xs px-3 py-1.5 rounded-lg ${r.type === "match" ? "bg-emerald-900/30 text-emerald-400" : "bg-red-900/30 text-red-400"}`}>
                        {r.type === "match" ? "✅" : "⚠️"} {r.text}
                      </div>
                    ))}</div>
                  </div>
                )}
                {analysisResult.suggestions?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">💡 Sugestões:</p>
                    <ul className="list-disc list-inside text-xs text-zinc-400 space-y-1">
                      {analysisResult.suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {analysisResult?.score !== undefined && analysisResult?.compatibility_score === undefined && (
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className={`text-4xl font-bold ${(analysisResult.score || 0) >= 70 ? "text-emerald-400" : (analysisResult.score || 0) >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                    {analysisResult.score}/100
                  </div>
                  <p className="text-sm text-zinc-400">ATS Score</p>
                </div>
                {analysisResult.matched_skills?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2 text-emerald-400">✅ Skills compatíveis: {analysisResult.matched_skills.join(", ")}</p>
                  </div>
                )}
                {analysisResult.missing_skills?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2 text-red-400">⚠️ Skills faltando: {analysisResult.missing_skills.join(", ")}</p>
                  </div>
                )}
                {analysisResult.suggestions?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-2">💡 Sugestões:</p>
                    <ul className="list-disc list-inside text-xs text-zinc-400 space-y-1">
                      {analysisResult.suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {coverLetter && (
              <div className="bg-zinc-800/50 rounded-lg p-4 whitespace-pre-wrap text-sm text-zinc-300 leading-relaxed max-h-96 overflow-y-auto">
                {coverLetter}
              </div>
            )}
          </div>
        )}

        {tab === "dashboard" && (
          <>
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-4">📥 Importar Dados</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-zinc-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-medium mb-2">🐙 GitHub</h3>
                  <div className="flex gap-2">
                    <input value={githubUsername} onChange={e => setGithubUsername(e.target.value)} placeholder="Nome de usuário do GitHub" className="flex-1 bg-zinc-900 rounded-lg px-3 py-2 text-xs border border-zinc-700 focus:outline-none focus:border-emerald-500" />
                    <button onClick={importGithub} disabled={importing} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-xs font-medium">{importing ? "Importando..." : "Importar"}</button>
                  </div>
                  {githubData && (
                    <div className="mt-3 text-xs text-zinc-400">
                      <p className="text-emerald-400 font-medium">{githubData.profile?.name || githubUsername}</p>
                      <p>{githubData.profile?.bio}</p>
                      <p className="mt-1">📦 {githubData.total_repos} repositórios • 🏷️ {(githubData.skills || []).join(", ")}</p>
                    </div>
                  )}
                </div>
                <div className="bg-zinc-800/50 rounded-lg p-4">
                  <h3 className="text-sm font-medium mb-2">🔗 LinkedIn</h3>
                  <div className="flex gap-2">
                    <input value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} placeholder="https://linkedin.com/in/..." className="flex-1 bg-zinc-900 rounded-lg px-3 py-2 text-xs border border-zinc-700 focus:outline-none focus:border-emerald-500" />
                    <button onClick={analyzeLinkedin} disabled={importing} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-3 py-2 rounded-lg text-xs font-medium">{importing ? "Analisando..." : "Analisar"}</button>
                  </div>
                  {linkedinData && (
                    <div className="mt-3 text-xs text-zinc-400">
                      <p className="text-emerald-400 font-medium">{linkedinData.name || "Analisado"}</p>
                      <p>{linkedinData.headline}</p>
                      {(linkedinData.skills || []).length > 0 && <p className="mt-1">🏷️ {linkedinData.skills.join(", ")}</p>}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Status chart */}
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">📊 Status Candidaturas</h2>
                {stats?.by_status && Object.keys(stats.by_status).length > 0 ? (
                  <>
                    <svg viewBox="0 0 200 120" className="w-full h-32">
                      {(() => {
                        const entries = Object.entries(stats.by_status) as [string, number][];
                        const max = Math.max(...entries.map(([,v]) => v), 1);
                        const colors = ["#34d399", "#60a5fa", "#f59e0b", "#a78bfa", "#f87171", "#e2e8f0", "#2dd4bf"];
                        const w = 180 / entries.length;
                        return entries.map(([k, v], i) => (
                          <g key={k}>
                            <rect x={10 + i * w} y={110 - (v as number / max) * 80} width={Math.max(w - 4, 8)} height={(v as number / max) * 80}
                              fill={colors[i % colors.length]} rx="4" />
                            <text x={10 + i * w + (w - 4) / 2} y="123" textAnchor="middle" fill="#a1a1aa" fontSize="8">
                              {k.replace(/_/g, "").slice(0, 6)}
                            </text>
                            <text x={10 + i * w + (w - 4) / 2} y={105 - (v as number / max) * 80} textAnchor="middle" fill="white" fontSize="9" fontWeight="bold">
                              {v}
                            </text>
                          </g>
                        ));
                      })()}
                    </svg>
                    <div className="flex flex-wrap gap-2 mt-3">
                      {Object.entries(stats.by_status).map(([k, v]) => (
                        <span key={k} className="text-xs bg-zinc-800 px-2 py-0.5 rounded"><span className="capitalize">{k.replace(/_/g, " ")}</span>: <strong>{v as number}</strong></span>
                      ))}
                    </div>
                  </>
                ) : <p className="text-zinc-500 text-sm">Nenhuma candidatura ainda.</p>}
              </div>

              {/* Activity / Overview */}
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">📈 Resumo</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">Total Candidaturas</span>
                    <span className="text-lg font-bold text-white">{stats?.total || 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">Currículos</span>
                    <span className="text-lg font-bold text-white">{resumes.length}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">Vagas Encontradas</span>
                    <span className="text-lg font-bold text-white">{searchResults.length || 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">IA Configurada</span>
                    <span className="text-lg font-bold text-emerald-400">{llmConfigs.filter((c: any) => c.has_key).length > 0 ? "✅ Sim" : "❌ Não"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">GitHub</span>
                    <span className="text-lg font-bold text-white">{githubData ? "✅ Conectado" : "—"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400">LinkedIn</span>
                    <span className="text-lg font-bold text-white">{linkedinData ? "✅ Analisado" : "—"}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Old stat cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Vagas</p><p className="text-2xl font-bold text-white">{searchResults.length || 0}</p></div>
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Candidaturas</p><p className="text-2xl font-bold text-white">{stats?.total || 0}</p></div>
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Currículos</p><p className="text-2xl font-bold text-white">{resumes.length}</p></div>
            </div>
          </>
        )}

        {tab === "jobs" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-4">Buscar Vagas</h2>
              <div className="flex gap-2 mb-4 flex-wrap">
                {sources.map(s => (
                  <button key={s.id} onClick={() => setSearchSource(s.id)} className={`px-3 py-1.5 rounded-lg text-xs font-medium ${searchSource === s.id ? "bg-emerald-600 text-white" : "bg-zinc-800 text-zinc-400 hover:text-white"}`}>
                    {s.id === "remoteok" ? "🌍" : "🇧🇷"} {s.name}
                  </button>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mb-3">{sources.find(s => s.id === searchSource)?.desc}</p>
              <div className="flex gap-2 mb-4">
                <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && searchJobs()} placeholder="Ex: python, react, backend, estágio..." className="flex-1 bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700 focus:outline-none focus:border-emerald-500" />
                <button onClick={searchJobs} disabled={searching} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg font-medium text-sm">{searching ? "Buscando..." : "Buscar"}</button>
              </div>
              <div className="flex gap-2 flex-wrap">
                {[
                  { label: "Estágio", emoji: "🎓" }, { label: "Junior", emoji: "🌱" }, { label: "Pleno", emoji: "📈" },
                  { label: "Senior", emoji: "🚀" }, { label: "Home Office", emoji: "🏠" }, { label: "Remoto", emoji: "🌍" },
                  { label: "Híbrido", emoji: "🔄" }, { label: "Presencial", emoji: "🏢" }, { label: "CLT", emoji: "📋" },
                  { label: "PJ", emoji: "📝" }, { label: "Freelance", emoji: "⚡" }, { label: "Tempo Integral", emoji: "💼" },
                  { label: "Meio Período", emoji: "⏳" },
                ].map(f => (
                  <button key={f.label} onClick={() => setSearchQuery(prev => prev ? `${prev} ${f.label}` : f.label)}
                    className="px-3 py-1.5 rounded-lg text-xs bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white transition-colors">{f.emoji} {f.label}</button>
                ))}
              </div>
            </div>
            {searchResults.length > 0 && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">{searchResults.length} vagas</h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {searchResults.map((j: any, i: number) => {
                    const title = j.position || j.title || j.name || "Vaga";
                    const company = j.company || j.company_name || "";
                    const url = j.url || j.apply_url || "";
                    return (
                      <div key={url || i} className="bg-zinc-800/50 rounded-lg p-4 hover:bg-zinc-800 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <h3 className="font-medium text-white truncate">{title}</h3>
                            {company && <p className="text-xs text-zinc-400">{company}</p>}
                          </div>
                          {url && <a href={url} target="_blank" rel="noopener noreferrer" className="px-3 py-1 rounded-lg bg-emerald-600/20 text-emerald-400 text-xs font-medium hover:bg-emerald-600/40 shrink-0">Candidatar</a>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {searchResults.length === 0 && !searching && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-500 text-sm">Digite um termo e clique em Buscar.</p></div>
            )}
          </div>
        )}

        {tab === "applications" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-4">Candidaturas</h2>
              {apps.length === 0 ? <p className="text-zinc-500 text-sm">Nenhuma ainda.</p> : (
                <div className="space-y-4">
                  {apps.map((a: any) => (
                    <div key={a.id} className="bg-zinc-800/50 rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div>
                          <p className="text-sm text-zinc-400">Job: <span className="text-white">{a.job_id.slice(0, 8)}...</span></p>
                          <p className="text-xs capitalize">Status: <span className="text-emerald-400 font-medium">{a.status.replace(/_/g, " ")}</span></p>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                          {["under_review", "hr_interview", "technical_interview", "offer", "rejected"].map(s => (
                            <button key={s} onClick={() => updateStatus(a.id, s)} className={`px-2 py-1 rounded text-xs ${a.status === s ? "bg-emerald-600" : "bg-zinc-700 hover:bg-zinc-600"}`}>{s.replace(/_/g, " ")}</button>
                          ))}
                        </div>
                      </div>
                      {/* AI buttons */}
                      <div className="flex gap-2 pt-1 border-t border-zinc-700/50">
                        <button onClick={() => runMatching(a.id, a.job_id, a.resume_id)} disabled={analyzing === a.id}
                          className="px-3 py-1.5 rounded text-xs bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/40 disabled:opacity-50">
                          {analyzing === a.id ? "Analisando..." : "🎯 Matching"}
                        </button>
                        <button onClick={() => runAts(a.resume_id, a.job_id)} disabled={analyzing === "ats"}
                          className="px-3 py-1.5 rounded text-xs bg-purple-600/20 text-purple-400 hover:bg-purple-600/40 disabled:opacity-50">
                          {analyzing === "ats" ? "Analisando..." : "📊 ATS Score"}
                        </button>
                        <button onClick={() => runCoverLetter(a.resume_id, a.job_id)} disabled={analyzing === "cover"}
                          className="px-3 py-1.5 rounded text-xs bg-amber-600/20 text-amber-400 hover:bg-amber-600/40 disabled:opacity-50">
                          {analyzing === "cover" ? "Gerando..." : "✉️ Carta"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {tab === "resumes" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-4">Enviar Currículo</h2>
              <form onSubmit={uploadResume} className="space-y-3">
                <input name="title" defaultValue="Meu Currículo" className="w-full bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700" />
                <input type="file" name="file" accept=".pdf" className="w-full text-sm file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white file:text-sm file:font-medium" />
                <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2.5 rounded-lg font-medium text-sm">Enviar</button>
              </form>
            </div>
            {resumes.length > 0 && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">Meus Currículos ({resumes.length})</h2>
                <div className="space-y-3">
                  {resumes.map((r: any) => (
                    <div key={r.id} className="bg-zinc-800/50 rounded-lg p-4">
                      <p className="font-medium">{r.title}</p>
                      <p className="text-xs text-zinc-500 mb-2">{r.content_preview?.slice(0, 100)}</p>
                      <button onClick={() => { setCoverLetter(""); setAnalysisResult(r); }} className="text-xs text-emerald-400 hover:text-emerald-300">Ver conteúdo completo</button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "ia" && (
          <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
            <h2 className="font-semibold mb-4">🤖 Configurar Inteligência Artificial</h2>
            <p className="text-sm text-zinc-400 mb-6">Escolha seu provedor de IA e coloque sua chave (API Key). Os dados ficam criptografados.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {llmProviders.map(p => {
                const config = llmConfigs.find((c: any) => c.provider_name === p.id);
                const isEditing = editingProvider === p.id;
                return (
                  <div key={p.id} className={`bg-zinc-800/50 rounded-xl p-5 border ${config?.is_active ? "border-emerald-700" : "border-zinc-700"} ${isEditing ? "ring-2 ring-emerald-500" : ""}`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2"><span className="text-xl">{p.icon}</span><h3 className="font-medium">{p.name}</h3></div>
                      {config?.has_key && <span className="text-xs bg-emerald-900/50 text-emerald-400 px-2 py-0.5 rounded">✅ Ativo</span>}
                    </div>
                    <p className="text-xs text-zinc-500 mb-3">Modelos: {p.models}</p>
                    {isEditing ? (
                      <div className="space-y-2">
                        {p.id !== "ollama" && <input value={editKey} onChange={e => setEditKey(e.target.value)} type="password" placeholder="API Key" className="w-full bg-zinc-900 rounded px-3 py-2 text-xs border border-zinc-600" />}
                        {p.needs_url && <input value={editUrl} onChange={e => setEditUrl(e.target.value)} placeholder="Base URL" className="w-full bg-zinc-900 rounded px-3 py-2 text-xs border border-zinc-600" />}
                        <input value={editModel} onChange={e => setEditModel(e.target.value)} placeholder="Modelo (opcional)" className="w-full bg-zinc-900 rounded px-3 py-2 text-xs border border-zinc-600" />
                        <div className="flex gap-2 pt-1">
                          <button onClick={() => saveLlmConfig(p.id)} className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded text-xs font-medium">Salvar</button>
                          <button onClick={() => { setEditingProvider(""); setEditKey(""); setEditUrl(""); setEditModel(""); }} className="bg-zinc-700 hover:bg-zinc-600 text-white px-3 py-1.5 rounded text-xs">Cancelar</button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        {config?.model && <p className="text-xs text-zinc-400 mb-2">Modelo: {config.model}</p>}
                        <button onClick={() => { setEditingProvider(p.id); setEditKey(""); setEditUrl(""); setEditModel(config?.model || ""); }} className="bg-zinc-700 hover:bg-zinc-600 text-white px-3 py-1.5 rounded text-xs font-medium">
                          {config?.has_key ? "Alterar Chave" : p.id === "ollama" ? "Configurar" : "Adicionar Chave"}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="mt-6 p-4 bg-zinc-800/30 rounded-lg border border-zinc-700">
              <h3 className="text-sm font-medium mb-2">🔒 Segurança</h3>
              <p className="text-xs text-zinc-400">Suas chaves de API são criptografadas e armazenadas com segurança no banco de dados.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
