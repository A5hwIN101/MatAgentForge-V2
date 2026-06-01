"use client";

import type { CritiqueTrace } from "@/types";

type TraceDrawerProps = {
  trace: CritiqueTrace;
};

export function TraceDrawer({ trace }: TraceDrawerProps) {
  const citationsByRule = trace.citations.reduce<Record<string, typeof trace.citations>>(
    (accumulator, citation) => {
      const key = citation.rule_name || citation.rule_id;
      accumulator[key] ??= [];
      accumulator[key].push(citation);
      return accumulator;
    },
    {},
  );

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
      <section className="rounded-lg border border-[#1c2420] bg-[#0c110e]">
        <div className="border-b border-[#1c2420] px-4 py-3">
          <p className="font-mono text-[12px] text-[#84968d]">Rule applicability</p>
        </div>

        <div className="space-y-3 px-4 py-4">
          {trace.rules_matched.length > 0 ? (
            trace.rules_matched.map((rule) => (
              <article
                key={rule}
                className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-4 py-4"
              >
                <p className="font-mono text-sm text-slate-100">{rule}</p>
                {(citationsByRule[rule] ?? []).length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {(citationsByRule[rule] ?? []).map((citation) => (
                      <div
                        key={`${citation.rule_id}-${citation.arxiv_id}-${citation.url}`}
                        className="rounded-lg border border-[#1c2420] bg-[#101612] px-4 py-4"
                      >
                        <p className="font-mono text-xs text-slate-300">
                          {citation.paper_title} ({citation.authors}, {citation.year ?? "n/a"})
                        </p>
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-block font-mono text-[12px] text-[#e0a9b5] underline decoration-[#bc687c]/60 underline-offset-2 transition hover:text-[#f0c9d1]"
                        >
                          Open arXiv
                        </a>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-[#1c2420] bg-[#0e1411] px-4 py-5 text-sm text-[#74827d]">
              No domain rules were retained for this material.
            </div>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-[#1c2420] bg-[#0c110e]">
        <div className="border-b border-[#1c2420] px-4 py-3">
          <p className="font-mono text-[12px] text-[#84968d]">Contradictions</p>
        </div>

        <div className="space-y-3 px-4 py-4">
          {trace.contradictions.length > 0 ? (
            trace.contradictions.map((item, index) => (
              <article
                key={`${item.rule_a}-${item.rule_b}-${index}`}
                className="rounded-lg border border-[#5b4036] bg-[#211816] px-4 py-4"
              >
                <p className="font-mono text-sm text-[#f2d4bf]">
                  {item.rule_a} vs {item.rule_b}
                </p>
                <p className="mt-2 font-mono text-sm text-slate-300">{item.type}</p>
                <p className="mt-2 font-mono text-sm text-slate-400">{item.resolution}</p>
                <p className="mt-3 font-mono text-xs leading-5 text-[#7c8984]">
                  {item.llm_reasoning}
                </p>
              </article>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-[#1c2420] bg-[#0e1411] px-4 py-5 text-sm text-[#74827d]">
              No contradiction conflicts were kept in the final reasoning trace.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
