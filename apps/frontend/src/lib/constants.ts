import {
  Bot,
  Briefcase,
  Calendar,
  ClipboardList,
  FileText,
  LayoutDashboard,
  MessageCircle,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export interface TabDefinition {
  id: string;
  label: string;
  icon: LucideIcon;
}

export const TABS: TabDefinition[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "jobs", label: "Vagas", icon: Briefcase },
  { id: "semantic", label: "Busca IA", icon: Sparkles },
  { id: "applications", label: "Candidaturas", icon: ClipboardList },
  { id: "calendar", label: "Agenda", icon: Calendar },
  { id: "resumes", label: "Currículos", icon: FileText },
  { id: "chat", label: "Chat", icon: MessageCircle },
  { id: "settings", label: "IA", icon: Bot },
];

export interface JobSource {
  id: string;
  name: string;
  description: string;
}

/** Only boards that work without credentials are offered in the picker. */
export const JOB_SOURCES: JobSource[] = [
  { id: "local", name: "Minhas vagas", description: "Vagas salvas na sua base" },
  { id: "remoteok", name: "RemoteOK", description: "Vagas remotas no mundo todo" },
  { id: "jobicy", name: "Jobicy", description: "Vagas remotas de tecnologia" },
  { id: "linkedin", name: "LinkedIn", description: "Vagas públicas do LinkedIn" },
  { id: "gupy", name: "Gupy", description: "Vagas do portal Gupy" },
];

export const QUICK_FILTERS = [
  "Estágio",
  "Júnior",
  "Pleno",
  "Sênior",
  "Remoto",
  "Híbrido",
  "Presencial",
  "CLT",
  "PJ",
  "Freelance",
];

/** The statuses a user can move an application through, in pipeline order. */
export const PIPELINE_STATUSES = [
  "applied",
  "under_review",
  "technical_test",
  "hr_interview",
  "technical_interview",
  "offer",
  "rejected",
] as const;

export interface ProviderDefinition {
  id: string;
  name: string;
  models: string;
  needsKey: boolean;
  needsUrl: boolean;
  accent: string;
}

export const LLM_PROVIDERS: ProviderDefinition[] = [
  { id: "openai", name: "OpenAI", models: "gpt-4o, gpt-4o-mini", needsKey: true, needsUrl: false, accent: "var(--success)" },
  { id: "anthropic", name: "Anthropic Claude", models: "claude-sonnet-4, claude-haiku-3.5", needsKey: true, needsUrl: false, accent: "var(--amber)" },
  { id: "gemini", name: "Google Gemini", models: "gemini-2.0-flash, gemini-2.0-pro", needsKey: true, needsUrl: false, accent: "var(--sky)" },
  { id: "nvidia_nim", name: "NVIDIA NIM", models: "meta/llama-3.2-3b-instruct", needsKey: true, needsUrl: true, accent: "var(--success)" },
  { id: "ollama", name: "Ollama (local)", models: "llama3.1, mistral, qwen2", needsKey: false, needsUrl: true, accent: "var(--violet)" },
  { id: "openrouter", name: "OpenRouter", models: "openai/gpt-4o, meta-llama/llama-3.1", needsKey: true, needsUrl: false, accent: "var(--rose)" },
];

export const COVER_LETTER_LANGUAGES = [
  { value: "pt-BR", label: "Português" },
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
];

export const COVER_LETTER_TONES = [
  { value: "professional", label: "Profissional" },
  { value: "formal", label: "Formal" },
  { value: "enthusiastic", label: "Entusiasmado" },
  { value: "casual", label: "Casual" },
];
