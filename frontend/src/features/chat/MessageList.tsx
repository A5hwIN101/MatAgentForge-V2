"use client";

import { useEffect, useState } from "react";

import { CritiqueCard } from "@/components/CritiqueCard";
import { FeedbackActions } from "@/features/feedback/FeedbackActions";
import type { ChatItem, CritiqueCard as CritiqueCardType } from "@/types";

const BACKEND_URL = "http://localhost:8000";

type MessageListProps = {
  messages: ChatItem[];
};

export function MessageList({ messages }: MessageListProps) {
  const [feedbackNotice, setFeedbackNotice] = useState("");
  const [feedbackError, setFeedbackError] = useState("");

  useEffect(() => {
    if (!feedbackNotice) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setFeedbackNotice("");
    }, 2000);

    return () => window.clearTimeout(timeoutId);
  }, [feedbackNotice]);

  const handleFeedback = async (
    critiqueId: string,
    action: "approve" | "reject" | "modify",
    reasonText?: string,
  ) => {
    setFeedbackError("");

    const response = await fetch(`${BACKEND_URL}/api/critiques/${critiqueId}/feedback`, {
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
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
      {feedbackNotice ? (
        <div className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
          {feedbackNotice}
        </div>
      ) : null}
      {feedbackError ? (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {feedbackError}
        </div>
      ) : null}
      {messages.length > 0 ? (
        messages.map((message) => {
          if (message.itemType === "critique_card" && message.contentJson) {
            const critique = message.contentJson as CritiqueCardType;

            return (
              <div key={message.id} className="flex justify-start">
                <div className="flex w-full max-w-3xl flex-col gap-4">
                  <CritiqueCard critique={critique} />
                  <FeedbackActions
                    critiqueId={critique.id}
                    onFeedback={(action, reasonText) =>
                      handleFeedback(critique.id, action, reasonText)
                    }
                  />
                </div>
              </div>
            );
          }

          if (message.itemType === "user_message") {
            return (
              <div key={message.id} className="flex justify-end">
                <div className="max-w-2xl rounded-[1.5rem] bg-emerald-400 px-5 py-4 text-sm font-medium text-slate-950 shadow-lg shadow-emerald-900/10">
                  {message.contentText}
                </div>
              </div>
            );
          }

          if (message.itemType === "agent_status" || message.itemType === "status_stream") {
            return (
              <div key={message.id} className="flex justify-start">
                <div className="max-w-2xl rounded-[1.25rem] border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-300">
                  {message.contentText}
                </div>
              </div>
            );
          }

          return (
            <div key={message.id} className="flex justify-start">
              <div className="max-w-3xl rounded-[1.5rem] border border-slate-800 bg-slate-900/80 px-5 py-4 text-sm leading-6 text-slate-200">
                {message.contentText}
              </div>
            </div>
          );
        })
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-[2rem] border border-dashed border-slate-800 bg-slate-950/40 p-10 text-center text-sm leading-6 text-slate-500">
          Choose a chat or start a new one to screen a material candidate.
        </div>
      )}
    </div>
  );
}
