"use client";

import { useState } from "react";

import type { CritiqueCard as CritiqueCardType } from "@/types";

type CritiqueCardProps = {
  critique: CritiqueCardType;
};

type WorkspaceTab = "results" | "citations";

const TAB_OPTIONS: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "results", label: "Results" },
  { id: "citations", label: "Citations" },
];

function toneForVerdict(verdict: string) {
  const normalized = verdict.toLowerCase();
  if (normalized.includes("infeasible")) {
    return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  }
  if (normalized.includes("concern")) {
    return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  }
  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
}

export function CritiqueCard({ critique }: CritiqueCardProps) {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("results");
  const rulesMatched = critique.trace.rules_matched.length;
  const citationCount = critique.trace.citations.length;
  const isInfeasible = critique.verdict.toLowerCase().includes("infeasible");

  return (
    <article className="w-full rounded-2xl border border-[#1c2420] bg-[#0b100d]/96 shadow-xl shadow-black/15">
      <div className="flex items-start justify-between gap-4 border-b border-[#1c2420] px-5 py-4">
        <div className="min-w-0">
          <p className="font-mono text-[12px] text-[#8ca39a]">MatAgent Forge</p>
          <h2 className="mt-2 font-mono text-xl font-semibold tracking-tight text-slate-50">
            {critique.material_formula}
          </h2>
        </div>
        <div
          className={`shrink-0 rounded-md border px-3 py-1.5 font-mono text-[12px] ${toneForVerdict(
            critique.verdict,
          )}`}
        >
          {critique.verdict}
        </div>
      </div>

      <div className="border-b border-[#1c2420] px-5 py-3">
        <nav className="flex flex-wrap gap-2">
          {TAB_OPTIONS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-md border px-3 py-1.5 font-mono text-[12px] transition ${
                activeTab === tab.id
                  ? "border-[#bc687c]/60 bg-[#bc687c]/10 text-[#f0cad1]"
                  : "border-[#1c2420] bg-[#0d120f] text-[#7c8d86] hover:border-[#2b3530] hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="px-5 py-5">
        {activeTab === "results" ? (
          <div className="space-y-5">
            <div className="rounded-xl border border-[#1c2420] bg-[#101612] px-4 py-4 font-mono text-sm leading-7 text-slate-200">
              {critique.explanation}
            </div>

            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3">
                <p className="font-mono text-[11px] text-[#7f9088]">verdict</p>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-100">
                  {critique.verdict}
                </p>
              </div>
              <div className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3">
                <p className="font-mono text-[11px] text-[#7f9088]">
                  {isInfeasible ? "assessment" : "risk score"}
                </p>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-100">
                  {isInfeasible ? "Not viable" : `${critique.score} / 10`}
                </p>
                {!isInfeasible ? (
                  <p className="mt-1 font-mono text-[11px] text-[#66736e]">Lower is better</p>
                ) : null}
              </div>
              <div className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3">
                <p className="font-mono text-[11px] text-[#7f9088]">rules matched</p>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-100">
                  {rulesMatched}
                </p>
              </div>
              <div className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3">
                <p className="font-mono text-[11px] text-[#7f9088]">citations</p>
                <p className="mt-1 font-mono text-sm font-semibold text-slate-100">
                  {citationCount}
                </p>
              </div>
            </section>

            {critique.flags.length > 0 ? (
              <section className="space-y-2">
                <p className="font-mono text-[12px] text-[#84968d]">Flags</p>
                <div className="space-y-2">
                  {critique.flags.map((flag, index) => (
                    <div
                      key={`${flag.text}-${index}`}
                      className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3 font-mono text-sm text-slate-200"
                    >
                      <span className="mr-2">{flag.icon}</span>
                      {flag.text}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {critique.suggestions.length > 0 ? (
              <section className="space-y-2">
                <p className="font-mono text-[12px] text-[#84968d]">Suggestions</p>
                <div className="space-y-2">
                  {critique.suggestions.map((suggestion, index) => (
                    <article
                      key={`${suggestion.text}-${index}`}
                      className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-3"
                    >
                      <p className="font-mono text-sm font-medium text-slate-100">
                        {suggestion.text}
                      </p>
                      <p className="mt-2 font-mono text-sm leading-6 text-slate-400">
                        {suggestion.rationale}
                      </p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : null}

        {activeTab === "citations" ? (
          <section className="space-y-3">
            {critique.trace.citations.length > 0 ? (
              critique.trace.citations.map((citation) => (
                <article
                  key={`${citation.rule_id}-${citation.arxiv_id}-${citation.url}`}
                  className="rounded-lg border border-[#1c2420] bg-[#101612] px-4 py-4"
                >
                  <p className="font-mono text-[12px] text-[#84968d]">{citation.rule_name}</p>
                  <h4 className="mt-2 font-mono text-base text-slate-100">
                    {citation.paper_title}
                  </h4>
                  <p className="mt-2 font-mono text-sm text-slate-400">
                    {citation.authors} | {citation.year ?? "n/a"} | arXiv {citation.arxiv_id}
                  </p>
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-block font-mono text-[12px] text-[#e0a9b5] underline decoration-[#bc687c]/60 underline-offset-2 transition hover:text-[#f0cad1]"
                  >
                    Open arXiv source
                  </a>
                  <p className="mt-3 font-mono text-sm leading-6 text-slate-300">
                    {citation.evidence_from_paper ?? "No excerpt attached for this citation."}
                  </p>
                </article>
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-[#1c2420] bg-[#101612] px-4 py-5 text-sm text-[#74827d]">
                No citations were attached to this critique.
              </div>
            )}
          </section>
        ) : null}
      </div>
    </article>
  );
}
