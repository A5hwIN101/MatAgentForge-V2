"use client";

import { useState } from "react";

import type { CritiqueTrace } from "@/types";

type TraceDrawerProps = {
  trace: CritiqueTrace;
};

export function TraceDrawer({ trace }: TraceDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-slate-200 transition hover:bg-slate-900/70"
      >
        <span>Trace Details</span>
        <span className="text-slate-400">{isOpen ? "Hide" : "Show"}</span>
      </button>

      {isOpen ? (
        <div className="space-y-5 border-t border-slate-800 px-4 py-4 text-sm text-slate-300">
          <section>
            <h4 className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Rules Matched
            </h4>
            <ul className="mt-3 space-y-2">
              {trace.rules_matched.length > 0 ? (
                trace.rules_matched.map((rule) => (
                  <li key={rule} className="rounded-xl bg-slate-900/70 px-3 py-2">
                    {rule}
                  </li>
                ))
              ) : (
                <li className="text-slate-500">No rules matched.</li>
              )}
            </ul>
          </section>

          <section>
            <h4 className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Contradictions
            </h4>
            <div className="mt-3 space-y-3">
              {trace.contradictions.length > 0 ? (
                trace.contradictions.map((item, index) => (
                  <article
                    key={`${item.rule_a}-${item.rule_b}-${index}`}
                    className="rounded-xl border border-amber-700/40 bg-amber-950/20 px-3 py-3"
                  >
                    <p className="font-medium text-amber-200">
                      {item.rule_a} vs {item.rule_b}
                    </p>
                    <p className="mt-1 text-slate-300">{item.type}</p>
                    <p className="mt-2 text-slate-400">{item.resolution}</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      {item.llm_reasoning}
                    </p>
                  </article>
                ))
              ) : (
                <p className="text-slate-500">No contradictions detected.</p>
              )}
            </div>
          </section>

          <section>
            <h4 className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Citations
            </h4>
            <div className="mt-3 space-y-3">
              {trace.citations.length > 0 ? (
                trace.citations.map((citation) => (
                  <article
                    key={`${citation.rule_id}-${citation.source}`}
                    className="rounded-xl bg-slate-900/70 px-3 py-3"
                  >
                    <p className="font-medium text-slate-200">{citation.rule_id}</p>
                    <p className="mt-1 text-slate-400">{citation.source}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-emerald-300">
                      Confidence {Math.round(citation.confidence * 100)}%
                    </p>
                  </article>
                ))
              ) : (
                <p className="text-slate-500">No citations available.</p>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
