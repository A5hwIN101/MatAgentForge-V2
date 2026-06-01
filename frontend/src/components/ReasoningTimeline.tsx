"use client";

import type { WorkflowStep } from "@/types";

type ReasoningTimelineProps = {
  steps: WorkflowStep[];
  streamText?: string;
};

export function ReasoningTimeline({ steps, streamText }: ReasoningTimelineProps) {
  return (
    <div className="space-y-2">
      {steps.map((step) => {
        const tone =
          step.status === "completed"
            ? "border-emerald-400/40 text-emerald-200"
            : step.status === "in_progress"
              ? "border-[#bc687c]/50 text-[#f0c9d1]"
              : step.status === "failed"
                ? "border-rose-400/50 text-rose-200"
                : "border-[#26302b] text-[#7c8d86]";
        const detailText =
          step.id === "critique_generation" && streamText?.trim()
            ? streamText.trim()
            : step.detail;

        return (
          <div
            key={step.id}
            className="rounded-lg border border-[#1c2420] bg-[#0f1512] px-3 py-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-md border px-2 py-0.5 font-mono text-[11px] ${tone}`}
                  >
                    {step.status === "completed"
                      ? "ok"
                      : step.status === "in_progress"
                        ? "..."
                        : step.status === "failed"
                          ? "!!"
                        : step.number}
                  </span>
                  <span className="font-mono text-sm text-slate-100">{step.title}</span>
                </div>
                <p className="mt-2 font-mono text-sm text-[#91a39b]">{step.label}</p>
                {detailText ? (
                  <p className="mt-2 font-mono text-sm leading-6 text-slate-300">{detailText}</p>
                ) : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
