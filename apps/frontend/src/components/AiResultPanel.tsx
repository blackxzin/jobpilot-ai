"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  FileEdit,
  FileText,
  Gauge,
  Lightbulb,
  Mail,
  Save,
  Target,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Button, Drawer, ScoreRing } from "@/components/ui";
import type { AtsResult, MatchResult } from "@/lib/types";

export type AiResult =
  | { kind: "match"; data: MatchResult }
  | { kind: "ats"; data: AtsResult }
  | { kind: "cover"; id: string; content: string }
  | { kind: "resume"; content: string; title: string }
  | null;

const TITLES: Record<string, string> = {
  match: "Compatibilidade com a vaga",
  ats: "ATS Score",
  cover: "Carta de apresentação",
  resume: "Currículo direcionado",
};

const ICONS = { match: Target, ats: Gauge, cover: Mail, resume: FileText };

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  return (
    <Button
      variant="secondary"
      size="sm"
      icon={copied ? CheckCircle2 : Copy}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
        } catch {
          // Clipboard access can be denied (insecure origin, permissions).
          // The text stays selectable on screen, so this is not fatal.
        }
      }}
    >
      {copied ? "Copiado" : "Copiar"}
    </Button>
  );
}

function SuggestionList({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-2">
      <h3 className="flex items-center gap-1.5 text-xs font-semibold text-dim">
        <Lightbulb size={13} className="text-[var(--amber)]" /> Sugestões
      </h3>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item} className="surface-inset px-3 py-2 text-xs leading-relaxed text-dim">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function SkillGroup({
  title,
  skills,
  tone,
  icon: Icon,
}: {
  title: string;
  skills: string[];
  tone: "success" | "warning";
  icon: typeof CheckCircle2;
}) {
  if (skills.length === 0) return null;
  return (
    <section className="space-y-2">
      <h3
        className="flex items-center gap-1.5 text-xs font-semibold"
        style={{ color: tone === "success" ? "var(--success)" : "var(--warning)" }}
      >
        <Icon size={13} /> {title}
      </h3>
      <div className="flex flex-wrap gap-1.5">
        {skills.map((skill) => (
          <Badge key={skill} tone={tone}>
            {skill}
          </Badge>
        ))}
      </div>
    </section>
  );
}

export function AiResultPanel({
  result,
  onClose,
  onSaveCoverLetter,
  savingCoverLetter,
}: {
  result: AiResult;
  onClose: () => void;
  onSaveCoverLetter: (id: string, content: string) => Promise<void>;
  savingCoverLetter: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  // Reset the editor whenever a different result is opened, so an edit in
  // progress cannot leak into the next letter.
  useEffect(() => {
    setEditing(false);
    setDraft(result?.kind === "cover" ? result.content : "");
  }, [result]);

  if (!result) return null;

  const Icon = ICONS[result.kind];

  return (
    <Drawer open title={TITLES[result.kind]} icon={Icon} onClose={onClose}>
      {result.kind === "match" && (
        <div className="space-y-6">
          <ScoreRing score={result.data.compatibility_score} label="Compatibilidade com a vaga" />

          {result.data.match_reasons?.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold text-dim">Por quê</h3>
              <ul className="space-y-1.5">
                {result.data.match_reasons.map((reason, index) => {
                  const positive = reason.type === "match";
                  return (
                    <li
                      key={`${reason.text}-${index}`}
                      className="flex items-start gap-2 rounded-lg px-3 py-2 text-xs"
                      style={{
                        background: `color-mix(in srgb, ${positive ? "var(--success)" : "var(--danger)"} 10%, transparent)`,
                        color: positive ? "var(--success)" : "var(--danger)",
                      }}
                    >
                      {positive ? (
                        <CheckCircle2 size={13} className="mt-px shrink-0" />
                      ) : (
                        <AlertTriangle size={13} className="mt-px shrink-0" />
                      )}
                      {reason.text}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}

          <SuggestionList items={result.data.suggestions ?? []} />
        </div>
      )}

      {result.kind === "ats" && (
        <div className="space-y-6">
          <ScoreRing score={result.data.score} label="Aderência ao filtro de ATS" />
          <SkillGroup
            title="Competências encontradas"
            skills={result.data.matched_skills ?? []}
            tone="success"
            icon={CheckCircle2}
          />
          <SkillGroup
            title="Competências ausentes"
            skills={result.data.missing_skills ?? []}
            tone="warning"
            icon={AlertTriangle}
          />
          <SuggestionList items={result.data.suggestions ?? []} />
        </div>
      )}

      {result.kind === "cover" && (
        <div className="space-y-3">
          <div className="flex justify-end gap-2">
            {editing ? (
              <>
                <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  icon={Save}
                  loading={savingCoverLetter}
                  onClick={async () => {
                    await onSaveCoverLetter(result.id, draft);
                    setEditing(false);
                  }}
                >
                  Salvar
                </Button>
              </>
            ) : (
              <>
                <CopyButton text={result.content} />
                <Button
                  variant="secondary"
                  size="sm"
                  icon={FileEdit}
                  onClick={() => {
                    setDraft(result.content);
                    setEditing(true);
                  }}
                >
                  Editar
                </Button>
              </>
            )}
          </div>

          {editing ? (
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              aria-label="Editar carta de apresentação"
              className="field min-h-[28rem] resize-y leading-relaxed"
            />
          ) : (
            <div className="surface-inset whitespace-pre-wrap p-4 text-sm leading-relaxed">
              {result.content}
            </div>
          )}
        </div>
      )}

      {result.kind === "resume" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <CopyButton text={result.content} />
          </div>
          <div className="surface-inset whitespace-pre-wrap p-4 font-mono text-xs leading-relaxed">
            {result.content}
          </div>
        </div>
      )}
    </Drawer>
  );
}
