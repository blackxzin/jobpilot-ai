"use client";

import { AlertTriangle, CheckCircle2, FileText, Gauge, Lightbulb, Upload } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { Badge, Button, Card, EmptyState, Field, Meter, SectionHeader } from "@/components/ui";
import { formatRelative } from "@/lib/format";
import type { AtsBreakdown, Resume } from "@/lib/types";

function AtsSummary({ score, breakdown }: { score: number; breakdown: AtsBreakdown }) {
  const tone = score >= 70 ? "success" : score >= 40 ? "warning" : "danger";

  return (
    <div className="space-y-3 border-t border-hair pt-3">
      <div className="flex items-center gap-3">
        <Gauge size={14} className="text-accent" />
        <div className="flex-1">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-dim">ATS Score</span>
            <Badge tone={tone}>{score}/100</Badge>
          </div>
          <Meter value={score} />
        </div>
      </div>

      {(breakdown.matched_skills?.length ?? 0) > 0 && (
        <div className="space-y-1.5">
          <p className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--success)]">
            <CheckCircle2 size={11} /> Competências reconhecidas
          </p>
          <div className="flex flex-wrap gap-1">
            {breakdown.matched_skills?.map((skill) => (
              <Badge key={skill} tone="success">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {(breakdown.missing_skills?.length ?? 0) > 0 && (
        <div className="space-y-1.5">
          <p className="flex items-center gap-1.5 text-[11px] font-medium text-[var(--warning)]">
            <AlertTriangle size={11} /> Lacunas frequentes
          </p>
          <div className="flex flex-wrap gap-1">
            {breakdown.missing_skills?.map((skill) => (
              <Badge key={skill} tone="warning">
                {skill}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {(breakdown.suggestions?.length ?? 0) > 0 && (
        <div className="space-y-1">
          <p className="flex items-center gap-1.5 text-[11px] font-medium text-dim">
            <Lightbulb size={11} className="text-[var(--amber)]" /> Sugestões
          </p>
          <ul className="list-inside list-disc space-y-0.5 text-[11px] text-faint">
            {breakdown.suggestions?.map((suggestion) => (
              <li key={suggestion}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function ResumesView({
  resumes,
  onUpload,
  uploading,
  onOpen,
}: {
  resumes: Resume[];
  onUpload: (formData: FormData) => Promise<void>;
  uploading: boolean;
  onOpen: (resume: Resume) => void;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [fileName, setFileName] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onUpload(new FormData(event.currentTarget));
    formRef.current?.reset();
    setFileName("");
  }

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <SectionHeader
          icon={Upload}
          title="Enviar currículo"
          description="PDF com texto selecionável, até 10 MB. O ATS Score é calculado em segundo plano."
        />
        <form ref={formRef} onSubmit={submit} className="space-y-3">
          <Field label="Título">
            <input name="title" defaultValue="Meu currículo" className="field" />
          </Field>

          <Field label="Arquivo PDF">
            <label className="surface-inset flex cursor-pointer items-center justify-center gap-2 border-dashed px-4 py-6 text-sm text-dim hover:border-[var(--border-accent)] hover:text-body">
              <Upload size={16} />
              <span>{fileName || "Selecionar arquivo"}</span>
              <input
                type="file"
                name="file"
                accept="application/pdf,.pdf"
                required
                onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
                className="sr-only"
              />
            </label>
          </Field>

          <Button type="submit" icon={Upload} loading={uploading}>
            Enviar
          </Button>
        </form>
      </Card>

      <Card className="p-5">
        <SectionHeader
          icon={FileText}
          title="Meus currículos"
          description={`${resumes.length} arquivo${resumes.length === 1 ? "" : "s"}`}
        />

        {resumes.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="Nenhum currículo enviado"
            description="Envie um PDF para liberar compatibilidade, ATS Score, cartas e currículo direcionado."
          />
        ) : (
          <ul className="space-y-3 stagger">
            {resumes.map((resume) => (
              <li key={resume.id} className="surface-inset space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-medium">{resume.title}</h3>
                    <p className="text-[11px] text-faint">
                      Enviado {formatRelative(resume.created_at)}
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => onOpen(resume)}>
                    Abrir
                  </Button>
                </div>

                {resume.content_preview && (
                  <p className="line-clamp-2 text-xs text-faint">{resume.content_preview}</p>
                )}

                {resume.ats_score != null && (
                  <AtsSummary score={resume.ats_score} breakdown={resume.ats_breakdown ?? {}} />
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
