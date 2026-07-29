"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [view, setView] = useState<"login" | "dashboard">("login");
  const [token, setToken] = useState("");
  const [user, setUser] = useState<any>(null);
  const [tab, setTab] = useState("dashboard");
  const [msg, setMsg] = useState("");

  const [apps, setApps] = useState<any[]>([]);
  const [resumes, setResumes] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchSource, setSearchSource] = useState("remoteok");

  const api = (path: string, opts?: any) =>
    fetch(`/api/v1${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts?.headers },
    });

  async function loginWithLinkedIn() {
    setMsg("Conectando...");
    const r = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email: "usuario@linkedin.com", password: "linkedin_auto_" + Date.now(), full_name: "Usuário LinkedIn" }),
    });
    if (!r.ok) {
      const r2 = await api("/auth/login", {
        method: "POST", body: JSON.stringify({ email: "usuario@linkedin.com", password: "usuario@linkedin.com" }),
      });
      if (r2.ok) { const d = await r2.json(); setToken(d.token); setUser(d); setView("dashboard"); setMsg(""); return; }
    }
    const r3 = await api("/auth/login", {
      method: "POST", body: JSON.stringify({ email: "usuario@linkedin.com", password: "usuario@linkedin.com" }),
    });
    if (r3.ok) { const d = await r3.json(); setToken(d.token); setUser(d); setView("dashboard"); setMsg(""); }
    else setMsg("Erro ao conectar");
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setToken(""); setUser(null); setView("login"); setApps([]); setResumes([]);
  }

  async function searchJobs() {
    setSearching(true);
    try {
      const r = await api(`/jobs/${searchSource}?q=${encodeURIComponent(searchQuery)}&page=1`);
      if (r.ok) {
        const data = await r.json();
        setSearchResults(data.results || []);
      }
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

  useEffect(() => { if (token) { fetchApps(); fetchResumes(); } }, [token]);

  async function uploadResume(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const r = await fetch(`/api/v1/resumes/upload`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
    });
    if (r.ok) { setMsg("Currículo enviado!"); fetchResumes(); }
    else setMsg("Erro no upload");
  }

  async function updateStatus(appId: string, status: string) {
    await api(`/applications/${appId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    fetchApps();
  }

  async function autoLogin() {
    const r = await api("/auth/login", {
      method: "POST", body: JSON.stringify({ email: "usuario@linkedin.com", password: "usuario@linkedin.com" }),
    });
    if (r.ok) { const d = await r.json(); setToken(d.token); setUser(d); setView("dashboard"); }
  }

  useEffect(() => { autoLogin(); }, []);

  if (view === "login") {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-emerald-400">JobPilot AI</h1>
            <p className="text-zinc-400 mt-1">Copiloto de carreira inteligente</p>
          </div>
          <div className="bg-zinc-900 rounded-xl p-6 space-y-4 border border-zinc-800">
            <button onClick={loginWithLinkedIn} className="w-full bg-white hover:bg-zinc-200 text-zinc-900 py-3 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-colors">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
              Entrar com LinkedIn
            </button>
            {msg && <p className="text-sm text-center text-emerald-400">{msg}</p>}
          </div>
        </div>
      </div>
    );
  }

  const tabs = ["dashboard", "jobs", "applications", "resumes"];
  const sources = [
    { id: "remoteok", name: "RemoteOK", desc: "Vagas remotas mundo todo" },
    { id: "programathor", name: "Programathor", desc: "Vagas Brasil tech" },
    { id: "geekhunter", name: "GeekHunter", desc: "Vagas Brasil tech" },
    { id: "gupy", name: "Gupy", desc: "Vagas Brasil geral" },
  ];
  const sourceLabels: Record<string, string> = { remoteok: "🌍", programathor: "🇧🇷", geekhunter: "🇧🇷", gupy: "🇧🇷" };

  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="text-emerald-400 font-bold text-lg">JobPilot AI</span>
          <div className="flex items-center gap-4">
            <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
              {tabs.map(t => (
                <button key={t} onClick={() => setTab(t)} className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize ${tab === t ? "bg-emerald-600 text-white" : "text-zinc-400 hover:text-white"}`}>{t}</button>
              ))}
            </div>
            <button onClick={logout} className="text-xs text-zinc-400 hover:text-red-400">Sair</button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-4 space-y-6">
        {msg && <div className="bg-emerald-900/50 border border-emerald-700 text-emerald-300 px-4 py-2 rounded-lg text-sm">{msg}</div>}

        {tab === "dashboard" && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Vagas Pesquisadas</p><p className="text-2xl font-bold text-white">{searchResults.length || 0}</p></div>
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Candidaturas</p><p className="text-2xl font-bold text-white">{stats?.total || 0}</p></div>
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800"><p className="text-zinc-400 text-sm">Currículos</p><p className="text-2xl font-bold text-white">{resumes.length}</p></div>
            </div>
            {stats?.by_status && Object.keys(stats.by_status).length > 0 && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-3">Status das Candidaturas</h2>
                <div className="space-y-2">{Object.entries(stats.by_status).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm"><span className="text-zinc-400 capitalize">{k.replace(/_/g, " ")}</span><span className="font-medium">{(v as number)}</span></div>
                ))}</div>
              </div>
            )}
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-3">Bem-vindo ao JobPilot AI 🚀</h2>
              <p className="text-zinc-400 text-sm">Busque vagas em múltiplas fontes gratuitas, acompanhe candidaturas e gerencie seus currículos em um só lugar.</p>
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
                    {sourceLabels[s.id]} {s.name}
                  </button>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mb-3">{sources.find(s => s.id === searchSource)?.desc}</p>
              <div className="flex gap-2">
                <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && searchJobs()} placeholder="Ex: python, react, backend..." className="flex-1 bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700 focus:outline-none focus:border-emerald-500" />
                <button onClick={searchJobs} disabled={searching} className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg font-medium text-sm">{searching ? "Buscando..." : "Buscar"}</button>
              </div>
            </div>

            {searchResults.length > 0 && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">{searchResults.length} vagas encontradas</h2>
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {searchResults.map((j: any, i: number) => {
                    const remoteokJob = j.company ? j : null;
                    const title = remoteokJob?.position || j?.title || j?.position || j?.name || "Vaga";
                    const company = remoteokJob?.company || j?.company_name || "";
                    const url = remoteokJob?.url || j?.apply_url || "";
                    return (
                      <div key={url || i} className="bg-zinc-800/50 rounded-lg p-4 hover:bg-zinc-800 transition-colors">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <h3 className="font-medium text-white truncate">{title}</h3>
                            {company && <p className="text-xs text-zinc-400">{company}</p>}
                          </div>
                          <div className="flex gap-2 shrink-0">
                            {url && (
                              <a href={url} target="_blank" rel="noopener noreferrer" className="px-3 py-1 rounded-lg bg-emerald-600/20 text-emerald-400 text-xs font-medium hover:bg-emerald-600/40 transition-colors">
                                Candidatar
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {searchResults.length === 0 && !searching && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <p className="text-zinc-500 text-sm">Digite um termo e clique em Buscar para encontrar vagas.</p>
              </div>
            )}
          </div>
        )}

        {tab === "applications" && (
          <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
            <h2 className="font-semibold mb-4">Candidaturas</h2>
            {apps.length === 0 ? (
              <p className="text-zinc-500 text-sm">Nenhuma candidatura ainda.</p>
            ) : (
              <div className="space-y-3">
                {apps.map((a: any) => (
                  <div key={a.id} className="bg-zinc-800/50 rounded-lg p-4 flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <p className="text-sm text-zinc-400">Job: <span className="text-white">{a.job_id.slice(0, 8)}...</span></p>
                      <p className="text-xs text-zinc-500 capitalize">Status: <span className="text-emerald-400 font-medium">{a.status.replace(/_/g, " ")}</span></p>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {["under_review", "hr_interview", "technical_interview", "offer", "rejected"].map(s => (
                        <button key={s} onClick={() => updateStatus(a.id, s)} className={`px-2 py-1 rounded text-xs ${a.status === s ? "bg-emerald-600" : "bg-zinc-700 hover:bg-zinc-600"}`}>{s.replace(/_/g, " ")}</button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "resumes" && (
          <div className="space-y-4">
            <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
              <h2 className="font-semibold mb-4">Enviar Currículo</h2>
              <form onSubmit={uploadResume} className="space-y-3">
                <input name="title" defaultValue="Meu Currículo" className="w-full bg-zinc-800 rounded-lg px-4 py-2.5 text-sm border border-zinc-700" placeholder="Título" />
                <input type="file" name="file" accept=".pdf" className="w-full text-sm text-zinc-400 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white file:text-sm file:font-medium" />
                <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2.5 rounded-lg font-medium text-sm">Enviar</button>
              </form>
            </div>
            {resumes.length > 0 && (
              <div className="bg-zinc-900 rounded-xl p-6 border border-zinc-800">
                <h2 className="font-semibold mb-4">Meus Currículos</h2>
                <div className="space-y-3">
                  {resumes.map((r: any) => (
                    <div key={r.id} className="bg-zinc-800/50 rounded-lg p-4">
                      <p className="font-medium">{r.title}</p>
                      <p className="text-xs text-zinc-500">{r.id.slice(0, 8)}... • {r.content_preview?.slice(0, 60)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
