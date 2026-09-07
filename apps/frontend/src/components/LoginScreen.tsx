"use client";

import { ArrowRight, Linkedin, Lock, Mail, Sparkles, User } from "lucide-react";
import { useState, type FormEvent } from "react";
import { AmbientBackground } from "@/components/AmbientBackground";
import { Logo } from "@/components/Logo";
import { Button, Field } from "@/components/ui";

const MIN_PASSWORD_LENGTH = 8;

const HIGHLIGHTS = [
  "Compatibilidade e ATS Score do seu currículo por vaga",
  "Carta de apresentação e currículo direcionado em segundos",
  "Pipeline de candidaturas com métricas de conversão",
];

export function LoginScreen({
  onLogin,
  onRegister,
  onLinkedIn,
  onDemo,
  demoAvailable,
  error,
}: {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, fullName: string) => Promise<void>;
  onLinkedIn: () => Promise<void>;
  onDemo: () => Promise<void>;
  demoAvailable: boolean;
  error: string;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");

  const registering = mode === "register";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLocalError("");

    if (!email.trim()) return setLocalError("Informe seu e-mail.");
    if (password.length < MIN_PASSWORD_LENGTH) {
      return setLocalError(`A senha precisa ter ao menos ${MIN_PASSWORD_LENGTH} caracteres.`);
    }

    setBusy(true);
    try {
      if (registering) await onRegister(email.trim(), password, fullName.trim());
      else await onLogin(email.trim(), password);
    } finally {
      setBusy(false);
    }
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } finally {
      setBusy(false);
    }
  }

  const message = localError || error;

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <AmbientBackground />

      <div className="grid w-full max-w-4xl gap-10 lg:grid-cols-[1.05fr_1fr] lg:items-center">
        {/* Pitch — hidden on small screens where the form is all that matters. */}
        <section className="hidden space-y-6 animate-rise lg:block">
          <Logo size="lg" />
          <h1 className="font-display text-4xl font-semibold leading-tight tracking-tight">
            Seu copiloto de
            <br />
            <span className="text-gradient">carreira com IA</span>
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-dim">
            Encontre vagas compatíveis, entenda por que você combina com elas e prepare cada
            candidatura sem começar do zero toda vez.
          </p>
          <ul className="space-y-3">
            {HIGHLIGHTS.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-dim">
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
                  <Sparkles size={11} />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="w-full animate-rise">
          <div className="mb-6 lg:hidden">
            <Logo size="lg" />
          </div>

          <div className="surface p-6 sm:p-7">
            <div className="mb-5 flex gap-1 rounded-xl bg-[var(--bg-input)] p-1">
              {(["login", "register"] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => {
                    setMode(value);
                    setLocalError("");
                  }}
                  className={`flex-1 rounded-lg py-2 text-xs font-medium ${
                    mode === value
                      ? "bg-[var(--bg-card)] text-body shadow-sm"
                      : "text-dim hover:text-body"
                  }`}
                >
                  {value === "login" ? "Entrar" : "Criar conta"}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="space-y-3.5">
              {registering && (
                <Field label="Nome completo">
                  <div className="relative">
                    <User size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                    <input
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      placeholder="Como podemos te chamar"
                      autoComplete="name"
                      className="field pl-9"
                    />
                  </div>
                </Field>
              )}

              <Field label="E-mail">
                <div className="relative">
                  <Mail size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="voce@exemplo.com"
                    autoComplete="email"
                    required
                    className="field pl-9"
                  />
                </div>
              </Field>

              <Field
                label="Senha"
                hint={registering ? `Mínimo de ${MIN_PASSWORD_LENGTH} caracteres.` : undefined}
              >
                <div className="relative">
                  <Lock size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="••••••••"
                    autoComplete={registering ? "new-password" : "current-password"}
                    required
                    className="field pl-9"
                  />
                </div>
              </Field>

              {message && (
                <p
                  role="alert"
                  className="rounded-lg px-3 py-2 text-xs"
                  style={{
                    background: "color-mix(in srgb, var(--danger) 12%, transparent)",
                    color: "var(--danger)",
                  }}
                >
                  {message}
                </p>
              )}

              <Button type="submit" loading={busy} icon={ArrowRight} className="w-full">
                {registering ? "Criar conta" : "Entrar"}
              </Button>
            </form>

            <div className="relative py-4">
              <span className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-hair" />
              </span>
              <span className="relative mx-auto block w-fit bg-card px-2 text-[11px] text-faint">ou</span>
            </div>

            <div className="space-y-2">
              <button
                onClick={() => run(onLinkedIn)}
                disabled={busy}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#0A66C2] py-2.5 text-sm font-medium text-white hover:bg-[#0958a8] disabled:opacity-50"
              >
                <Linkedin size={15} /> Entrar com LinkedIn
              </button>

              {demoAvailable && (
                <Button
                  variant="secondary"
                  icon={Sparkles}
                  onClick={() => run(onDemo)}
                  disabled={busy}
                  className="w-full"
                >
                  Explorar a demonstração
                </Button>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
