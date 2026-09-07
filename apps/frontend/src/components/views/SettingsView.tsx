"use client";

import { Bot, CheckCircle2, Info, Shield } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, Field, SectionHeader } from "@/components/ui";
import { LLM_PROVIDERS } from "@/lib/constants";
import type { LlmConfig } from "@/lib/types";

interface Draft {
  apiKey: string;
  baseUrl: string;
  model: string;
}

const EMPTY_DRAFT: Draft = { apiKey: "", baseUrl: "", model: "" };

export function SettingsView({
  configs,
  onSave,
  saving,
}: {
  configs: LlmConfig[];
  onSave: (providerId: string, draft: Draft) => Promise<void>;
  saving: string;
}) {
  const [editing, setEditing] = useState("");
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);

  const anyConfigured = configs.some((config) => config.has_key);

  function startEditing(providerId: string, current?: LlmConfig) {
    setEditing(providerId);
    setDraft({
      apiKey: "",
      baseUrl: current?.base_url ?? "",
      model: current?.model ?? "",
    });
  }

  async function save(providerId: string) {
    await onSave(providerId, draft);
    setEditing("");
    setDraft(EMPTY_DRAFT);
  }

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <SectionHeader
          icon={Bot}
          title="Provedores de IA"
          description="Escolha onde as análises são geradas. As chaves são criptografadas antes de serem gravadas."
        />

        {!anyConfigured && (
          <div
            className="mb-5 flex gap-2.5 rounded-xl px-4 py-3 text-xs"
            style={{
              background: "color-mix(in srgb, var(--warning) 10%, transparent)",
              color: "var(--warning)",
            }}
          >
            <Info size={14} className="mt-px shrink-0" />
            <p className="leading-relaxed">
              Nenhum provedor configurado. O app está rodando com o{" "}
              <strong>analisador local</strong>: compatibilidade, ATS Score, carta e currículo
              direcionado funcionam, mas o chat e as análises abertas precisam de um modelo de
              linguagem.
            </p>
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2">
          {LLM_PROVIDERS.map((provider) => {
            const config = configs.find((item) => item.provider_name === provider.id);
            const isEditing = editing === provider.id;

            return (
              <div
                key={provider.id}
                className={`surface-inset space-y-3 p-4 ${
                  isEditing ? "ring-1 ring-[var(--accent)]" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg"
                      style={{
                        background: `color-mix(in srgb, ${provider.accent} 16%, transparent)`,
                        color: provider.accent,
                      }}
                    >
                      <Bot size={15} />
                    </span>
                    <div>
                      <h3 className="text-sm font-medium">{provider.name}</h3>
                      <p className="text-[11px] text-faint">{provider.models}</p>
                    </div>
                  </div>
                  {config?.has_key && (
                    <Badge tone="success" icon={CheckCircle2}>
                      Ativo
                    </Badge>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-2.5">
                    {provider.needsKey && (
                      <Field label="Chave de API">
                        <input
                          type="password"
                          value={draft.apiKey}
                          onChange={(event) => setDraft({ ...draft, apiKey: event.target.value })}
                          placeholder={config?.has_key ? "Deixe em branco para manter" : "sk-…"}
                          autoComplete="off"
                          className="field"
                        />
                      </Field>
                    )}
                    {provider.needsUrl && (
                      <Field label="Base URL">
                        <input
                          value={draft.baseUrl}
                          onChange={(event) => setDraft({ ...draft, baseUrl: event.target.value })}
                          placeholder="http://localhost:11434"
                          className="field"
                        />
                      </Field>
                    )}
                    <Field label="Modelo" hint="Opcional — usa o padrão do provedor se vazio.">
                      <input
                        value={draft.model}
                        onChange={(event) => setDraft({ ...draft, model: event.target.value })}
                        placeholder={provider.models.split(",")[0].trim()}
                        className="field"
                      />
                    </Field>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => save(provider.id)}
                        loading={saving === provider.id}
                      >
                        Salvar
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          setEditing("");
                          setDraft(EMPTY_DRAFT);
                        }}
                      >
                        Cancelar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {config?.model && (
                      <p className="text-xs text-dim">
                        Modelo: <span className="text-body">{config.model}</span>
                      </p>
                    )}
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => startEditing(provider.id, config)}
                    >
                      {config?.has_key
                        ? "Alterar"
                        : provider.needsKey
                          ? "Adicionar chave"
                          : "Configurar"}
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="flex gap-3 p-5">
        <Shield size={16} className="mt-0.5 shrink-0 text-accent" />
        <div className="space-y-1">
          <h3 className="text-sm font-medium">Como suas chaves são guardadas</h3>
          <p className="text-xs leading-relaxed text-dim">
            Cada chave é criptografada com Fernet antes de ir para o banco, usando uma chave
            derivada do <code className="text-accent">SECRET_KEY</code> da instância. A API nunca
            devolve a chave em texto — apenas se ela existe.
          </p>
        </div>
      </Card>
    </div>
  );
}
