"use client";

import { TraceDrawer } from "@/components/TraceDrawer";
import type { CritiqueCard as CritiqueCardType } from "@/types";

type FeedbackAction = "approve" | "reject" | "modify";

type CritiqueCardProps = {
  critique: CritiqueCardType;
  onFeedback: (action: FeedbackAction, reason?: string) => void;
};

export function CritiqueCard({ critique, onFeedback }: CritiqueCardProps) {
  return (
    <article className="w-full max-w-3xl rounded-[2rem] border border-slate-800 bg-slate-900/85 p-6 shadow-2xl shadow-slate-950/40 backdrop-blur">
      <header className="border-b border-slate-800 pb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.34em] text-slate-500">
          Material
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">
          {critique.material_formula}
        </h2>
      </header>

      <section className="border-b border-slate-800 py-5">
        <dl className="space-y-3 text-sm sm:text-base">
          <div className="flex items-center justify-between gap-4">
            <dt className="font-medium uppercase tracking-[0.24em] text-slate-500">
              Domain Rules
            </dt>
            <dd className="font-semibold text-emerald-300">
              ✅ {critique.domain_rules_passed}/{critique.domain_rules_total}
            </dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="font-medium uppercase tracking-[0.24em] text-slate-500">
              Critique Score
            </dt>
            <dd className="font-semibold text-slate-100">{critique.score} / 10</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="font-medium uppercase tracking-[0.24em] text-slate-500">
              Verdict
            </dt>
            <dd className="font-semibold text-amber-200">{critique.verdict}</dd>
          </div>
        </dl>
      </section>

      <section className="border-b border-slate-800 py-5">
        <h3 className="text-xs font-semibold uppercase tracking-[0.34em] text-slate-500">
          Critique Flags
        </h3>
        <ul className="mt-4 space-y-3">
          {critique.flags.map((flag, index) => (
            <li
              key={`${flag.text}-${index}`}
              className="flex items-start gap-3 rounded-2xl bg-slate-950/70 px-4 py-3 text-slate-200"
            >
              <span className="text-lg">{flag.icon}</span>
              <span className="leading-6">{flag.text}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="border-b border-slate-800 py-5">
        <h3 className="text-xs font-semibold uppercase tracking-[0.34em] text-slate-500">
          Suggestions
        </h3>
        <div className="mt-4 space-y-4">
          {critique.suggestions.map((suggestion, index) => (
            <article
              key={`${suggestion.text}-${index}`}
              className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-4"
            >
              <p className="text-base font-medium text-slate-100">→ {suggestion.text}</p>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                {suggestion.rationale}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="py-5">
        <p className="text-sm leading-6 text-slate-400">{critique.explanation}</p>
        <div className="mt-5">
          <TraceDrawer trace={critique.trace} />
        </div>
      </section>

      <footer className="border-t border-slate-800 pt-5">
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => onFeedback("approve")}
            className="rounded-full bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
          >
            APPROVE
          </button>
          <button
            type="button"
            onClick={() => onFeedback("reject")}
            className="rounded-full border border-rose-500/60 px-5 py-2.5 text-sm font-semibold text-rose-200 transition hover:bg-rose-500/10"
          >
            REJECT
          </button>
          <button
            type="button"
            onClick={() => onFeedback("modify")}
            className="rounded-full border border-sky-500/60 px-5 py-2.5 text-sm font-semibold text-sky-200 transition hover:bg-sky-500/10"
          >
            MODIFY
          </button>
        </div>
      </footer>
    </article>
  );
}
