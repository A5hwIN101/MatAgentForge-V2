"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { CritiqueCard } from "@/components/CritiqueCard";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { ReasoningTimeline } from "@/components/ReasoningTimeline";
import { TraceDrawer } from "@/components/TraceDrawer";
import { FeedbackActions } from "@/features/feedback/FeedbackActions";
import { API_BASE_URL } from "@/lib/api";
import type {
  ChatItem,
  CritiqueCard as CritiqueCardType,
  ScreeningErrorCard,
  WorkflowStep,
} from "@/types";

type MessageListProps = {
  messages: ChatItem[];
  workflowSteps: WorkflowStep[];
  isStreaming: boolean;
  streamText: string;
  streamCritique: CritiqueCardType | null;
  streamFailure: ScreeningErrorCard | null;
};

type AnalysisSession = {
  id: string;
  query: string;
  createdAt: string;
  critique?: CritiqueCardType;
  error?: ScreeningErrorCard;
  notes: string[];
};

function groupAnalysisSessions(messages: ChatItem[]): AnalysisSession[] {
  const sessions: AnalysisSession[] = [];
  let currentSession: AnalysisSession | null = null;

  messages
    .slice()
    .sort((left, right) => left.sequenceNo - right.sequenceNo)
    .forEach((message) => {
      if (message.itemType === "user_message") {
        if (currentSession) {
          sessions.push(currentSession);
        }

        currentSession = {
          id: message.id,
          query: message.contentText ?? "Unknown material",
          createdAt: message.createdAt,
          notes: [],
        };
        return;
      }

      if (!currentSession) {
        currentSession = {
          id: `session-${message.id}`,
          query: "Material session",
          createdAt: message.createdAt,
          notes: [],
        };
      }

      if (message.itemType === "critique_card" && message.contentJson) {
        currentSession.critique = message.contentJson as CritiqueCardType;
      } else if (message.itemType === "error_card" && message.contentJson) {
        currentSession.error = message.contentJson as ScreeningErrorCard;
      } else if (message.itemType === "agent_text" && message.contentText) {
        currentSession.notes.push(message.contentText);
      }
    });

  if (currentSession) {
    sessions.push(currentSession);
  }

  return sessions;
}

function AtomBadge() {
  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[#24302b] bg-[#101612] shadow-sm shadow-black/20">
      <svg
        aria-hidden="true"
        viewBox="0 0 64 64"
        className="h-5 w-5 text-[#ff5b57]"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="32" cy="32" r="3.5" fill="currentColor" stroke="none" />
        <ellipse cx="32" cy="32" rx="23" ry="9.5" />
        <ellipse cx="32" cy="32" rx="23" ry="9.5" transform="rotate(60 32 32)" />
        <ellipse cx="32" cy="32" rx="23" ry="9.5" transform="rotate(120 32 32)" />
      </svg>
    </div>
  );
}

export function MessageList({
  messages,
  workflowSteps,
  isStreaming,
  streamText,
  streamCritique,
  streamFailure,
}: MessageListProps) {
  const [feedbackNotice, setFeedbackNotice] = useState("");
  const [feedbackError, setFeedbackError] = useState("");
  const [expandedThinkingId, setExpandedThinkingId] = useState<string | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);
  const sessions = useMemo(() => groupAnalysisSessions(messages), [messages]);

  useEffect(() => {
    if (!feedbackNotice) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setFeedbackNotice("");
    }, 2000);

    return () => window.clearTimeout(timeoutId);
  }, [feedbackNotice]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    const anchor = bottomAnchorRef.current;
    if (!container || !anchor) {
      return;
    }

    anchor.scrollIntoView({
      block: "end",
      behavior: messages.length > 0 ? "smooth" : "auto",
    });
  }, [isStreaming, messages, streamCritique, streamFailure, streamText, workflowSteps]);

  const handleFeedback = async (
    critiqueId: string,
    action: "approve" | "reject" | "modify",
    reasonText?: string,
  ) => {
    setFeedbackError("");

    const response = await fetch(`${API_BASE_URL}/api/critiques/${critiqueId}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action,
        reason_text: reasonText ?? null,
      }),
    });

    const payload = (await response.json()) as { detail?: string };
    if (!response.ok) {
      const message = payload.detail ?? "Failed to save feedback";
      setFeedbackError(message);
      throw new Error(message);
    }

    setFeedbackNotice("Feedback saved");
  };

  return (
    <div
      ref={scrollContainerRef}
      className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain pb-40"
    >
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 px-2">
        {feedbackNotice ? (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 font-mono text-sm text-emerald-200">
            {feedbackNotice}
          </div>
        ) : null}
        {feedbackError ? (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 font-mono text-sm text-rose-200">
            {feedbackError}
          </div>
        ) : null}
      </div>

      {sessions.map((session, index) => {
        const isLatestSession = index === sessions.length - 1;
        const hasWorkflow =
          isLatestSession && (isStreaming || workflowSteps.some((step) => step.status !== "pending"));
        const isThinkingOpen = expandedThinkingId === session.id;
        const activeCritique =
          isLatestSession && !session.critique ? streamCritique ?? null : session.critique;
        const activeError =
          isLatestSession && !session.error ? streamFailure ?? null : session.error;

        return (
          <section key={session.id} className="mx-auto flex w-full max-w-5xl flex-col gap-3 px-2">
            <div className="flex justify-end">
              <div className="max-w-[18rem] rounded-2xl border border-[#29342f] bg-[#f7f7f3] px-4 py-2.5 text-right text-sm font-medium text-slate-900 shadow-sm shadow-black/10">
                {session.query}
              </div>
            </div>

            <div className="flex items-start gap-3">
              <AtomBadge />
              <div className="min-w-0 flex-1 max-w-4xl space-y-3">
                {hasWorkflow ? (
                  <div className="rounded-xl border border-[#1c2420] bg-[#0d120f]">
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedThinkingId((current) =>
                          current === session.id ? null : session.id,
                        )
                      }
                      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                    >
                      <div className="flex items-center gap-3">
                        {isStreaming ? <LoadingIndicator compact /> : null}
                        <span className="font-mono text-sm text-[#e3b2bd]">
                          {isStreaming ? "Thinking..." : "View thinking process"}
                        </span>
                      </div>
                      <span className="font-mono text-[12px] text-[#74827d]">
                        {isThinkingOpen ? "Hide" : "Open"}
                      </span>
                    </button>

                    {isThinkingOpen ? (
                      <div className="space-y-3 border-t border-[#1c2420] px-4 py-4">
                        <ReasoningTimeline steps={workflowSteps} streamText={streamText} />
                        {activeCritique ? <TraceDrawer trace={activeCritique.trace} /> : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {!session.critique && !session.error ? (
                  <div className="w-full max-w-4xl rounded-2xl border border-[#1c2420] bg-[#0b100d]/96 px-5 py-5 shadow-xl shadow-black/15">
                    <div className="flex items-center gap-3">
                      <p className="font-mono text-[12px] text-[#8ca39a]">MatAgent Forge</p>
                      <span className="rounded-md border border-[#24302b] bg-[#101612] px-2 py-1 font-mono text-[11px] text-[#74827d]">
                        {isStreaming ? "streaming" : "queued"}
                      </span>
                    </div>
                    <div className="mt-4 min-h-20 rounded-xl border border-[#1c2420] bg-[#101612] px-4 py-4 font-mono text-sm leading-7 text-slate-200">
                      {session.notes[session.notes.length - 1] || streamText || "Preparing analysis..."}
                      {isStreaming ? (
                        <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-[#bc687c]/80 align-middle" />
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {activeCritique ? (
                  <div className="w-full space-y-4">
                    <CritiqueCard critique={activeCritique} />
                    <FeedbackActions
                      critiqueId={activeCritique.id}
                      onFeedback={(action, reasonText) =>
                        handleFeedback(activeCritique.id, action, reasonText)
                      }
                    />
                  </div>
                ) : null}

                {activeError ? (
                  <article className="w-full rounded-2xl border border-rose-500/25 bg-rose-950/15 px-5 py-5 text-slate-100 shadow-xl shadow-black/10">
                    <div className="flex items-center gap-3">
                      <p className="font-mono text-[12px] text-rose-300">Invalid material formula</p>
                    </div>
                    <h3 className="mt-3 text-xl font-semibold text-rose-100">
                      {activeError.title}
                    </h3>
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                      {activeError.message}
                    </p>
                    {activeError.hint ? (
                      <p className="mt-4 text-sm text-slate-400">{activeError.hint}</p>
                    ) : null}
                  </article>
                ) : null}
              </div>
            </div>
          </section>
        );
      })}
      <div ref={bottomAnchorRef} className="h-px shrink-0" />
    </div>
  );
}
