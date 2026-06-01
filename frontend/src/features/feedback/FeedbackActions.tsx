"use client";

import { useEffect, useState } from "react";

type FeedbackAction = "approve" | "reject" | "modify";

type FeedbackActionsProps = {
  critiqueId: string;
  onFeedback: (action: FeedbackAction, reasonText?: string) => Promise<void>;
};

export function FeedbackActions({ critiqueId, onFeedback }: FeedbackActionsProps) {
  const [activeAction, setActiveAction] = useState<Exclude<FeedbackAction, "approve"> | null>(null);
  const [reasonText, setReasonText] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!savedMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setSavedMessage("");
      setActiveAction(null);
      setReasonText("");
    }, 2000);

    return () => window.clearTimeout(timeoutId);
  }, [savedMessage]);

  const submitFeedback = async (action: FeedbackAction, reason?: string) => {
    setIsSaving(true);
    setErrorMessage("");
    try {
      await onFeedback(action, reason);
      setSavedMessage("Feedback saved");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to save feedback");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full rounded-[1.75rem] border border-slate-800 bg-slate-950/55 p-4">
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={isSaving}
          onClick={() => void submitFeedback("approve")}
          className="rounded-full bg-cyan-400 px-5 py-2.5 font-mono text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
        >
          APPROVE
        </button>
        <button
          type="button"
          disabled={isSaving}
          onClick={() => {
            setActiveAction("reject");
            setSavedMessage("");
            setErrorMessage("");
          }}
          className="rounded-full border border-rose-500/70 px-5 py-2.5 font-mono text-sm font-semibold text-rose-200 transition hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          REJECT
        </button>
        <button
          type="button"
          disabled={isSaving}
          onClick={() => {
            setActiveAction("modify");
            setSavedMessage("");
            setErrorMessage("");
          }}
          className="rounded-full border border-sky-500/70 px-5 py-2.5 font-mono text-sm font-semibold text-sky-200 transition hover:bg-sky-500/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          MODIFY
        </button>
      </div>

      {activeAction ? (
        <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <label className="block font-mono text-sm font-medium text-slate-200" htmlFor={`feedback-${critiqueId}`}>
            {activeAction === "reject" ? "Why did you reject?" : "Why did you modify?"}
          </label>
          <input
            id={`feedback-${critiqueId}`}
            type="text"
            value={reasonText}
            onChange={(event) => setReasonText(event.target.value)}
            placeholder="Why did you reject/modify?"
            className="mt-3 h-11 w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 font-mono text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
          />
          <div className="mt-3 flex gap-3">
            <button
              type="button"
              disabled={isSaving}
              onClick={() => void submitFeedback(activeAction, reasonText.trim() || undefined)}
              className="rounded-full bg-cyan-400 px-4 py-2 font-mono text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? "Saving..." : "Submit"}
            </button>
            <button
              type="button"
              disabled={isSaving}
              onClick={() => {
                setActiveAction(null);
                setReasonText("");
                setErrorMessage("");
              }}
              className="rounded-full border border-slate-700 px-4 py-2 font-mono text-sm font-semibold text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}

      {savedMessage ? (
        <p className="mt-3 font-mono text-sm text-emerald-300">{savedMessage}</p>
      ) : null}
      {errorMessage ? (
        <p className="mt-3 font-mono text-sm text-rose-300">{errorMessage}</p>
      ) : null}
    </div>
  );
}
