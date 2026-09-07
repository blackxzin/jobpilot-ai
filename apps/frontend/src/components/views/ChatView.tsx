"use client";

import { MessageCircle, Send, Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";
import { Button, Card, SectionHeader } from "@/components/ui";

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

const SUGGESTIONS = [
  "Como melhorar meu currículo para vagas de backend?",
  "O que estudar para uma entrevista técnica de sistemas distribuídos?",
  "Como negociar salário numa proposta?",
];

export function ChatView({
  history,
  draft,
  onDraftChange,
  onSend,
  sending,
  offline,
}: {
  history: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  sending: boolean;
  offline: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view as the conversation grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [history, sending]);

  return (
    <Card className="flex h-[70vh] flex-col p-5">
      <SectionHeader
        icon={MessageCircle}
        title="Assistente de carreira"
        description={
          offline
            ? "Nenhum provedor de IA configurado — configure em IA para conversar."
            : "Pergunte sobre currículo, entrevistas, transição de carreira e negociação."
        }
      />

      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl bg-page p-4">
        {history.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft text-accent animate-breathe">
              <Sparkles size={19} />
            </span>
            <p className="text-sm text-dim">Por onde quer começar?</p>
            <div className="flex flex-col gap-1.5">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onDraftChange(suggestion)}
                  className="rounded-lg bg-[var(--bg-input)] px-3 py-2 text-xs text-dim hover:text-body"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed animate-rise ${
                message.role === "user"
                  ? "bg-accent-soft text-accent"
                  : "surface-inset text-body"
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="surface-inset flex gap-1 px-4 py-3">
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  className="h-1.5 w-1.5 rounded-full bg-[var(--text-muted)]"
                  style={{
                    animation: "breathe 1.2s ease-in-out infinite",
                    animationDelay: `${dot * 0.15}s`,
                  }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && !event.shiftKey && onSend()}
          placeholder="Digite sua pergunta…"
          aria-label="Mensagem para o assistente"
          className="field"
        />
        <Button
          icon={Send}
          onClick={onSend}
          loading={sending}
          disabled={!draft.trim()}
          className="shrink-0"
        >
          Enviar
        </Button>
      </div>
    </Card>
  );
}
