"use client";

import { ExternalLink, Info, X } from "lucide-react";
import { useState } from "react";
import { IS_STATIC_DEMO } from "@/demo/client";

const REPO_URL = "https://github.com/blackxzin/JOBPILOT_AI";

/**
 * Tells the visitor what they are looking at.
 *
 * The published demo runs entirely in the browser: the data is real output
 * captured from a live instance, but there is no server behind it. Saying so
 * up front is more honest than letting someone discover it when an upload
 * or an external job search quietly fails.
 */
export function DemoBanner() {
  const [dismissed, setDismissed] = useState(false);

  if (!IS_STATIC_DEMO || dismissed) return null;

  return (
    <div
      className="glass sticky top-16 z-30 border-b border-hair px-4 py-2.5"
      role="note"
      style={{ background: "color-mix(in srgb, var(--sky) 12%, var(--bg-nav))" }}
    >
      <div className="mx-auto flex max-w-7xl items-start gap-2.5 text-xs">
        <Info size={14} className="mt-px shrink-0 text-[var(--sky)]" />
        <p className="flex-1 leading-relaxed text-dim">
          <strong className="text-body">Demonstração no navegador.</strong> Os dados e as
          análises são respostas reais capturadas de uma instância rodando — mas não há
          servidor aqui, então upload de currículo, busca em sites de vagas e chat precisam
          da versão completa. Nada que você mudar é salvo.{" "}
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-medium text-accent hover:underline"
          >
            Rodar localmente <ExternalLink size={10} />
          </a>
        </p>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dispensar aviso"
          className="shrink-0 text-faint hover:text-body"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
