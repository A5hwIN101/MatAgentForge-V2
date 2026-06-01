"use client";

import { useEffect, useMemo, useState } from "react";

const BRAILLE_FRAMES = [
  "\u280b",
  "\u2819",
  "\u2839",
  "\u2838",
  "\u283c",
  "\u2834",
  "\u2826",
  "\u2827",
  "\u2807",
  "\u280f",
];
const PROGRESS_MESSAGES = [
  "Parsing material formula...",
  "Loading domain rules...",
  "Checking rule applicability...",
  "Scanning citation-backed evidence...",
  "Running critique agent...",
  "Preparing assessment...",
];

type LoadingIndicatorProps = {
  message?: string;
  compact?: boolean;
};

export function LoadingIndicator({ message, compact = false }: LoadingIndicatorProps) {
  const [frameIndex, setFrameIndex] = useState(0);
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const frameTimer = window.setInterval(() => {
      setFrameIndex((current) => (current + 1) % BRAILLE_FRAMES.length);
    }, 80);

    const messageTimer = window.setInterval(() => {
      setMessageIndex((current) => (current + 1) % PROGRESS_MESSAGES.length);
    }, 800);

    return () => {
      window.clearInterval(frameTimer);
      window.clearInterval(messageTimer);
    };
  }, []);

  const activeMessage = useMemo(
    () => message ?? PROGRESS_MESSAGES[messageIndex],
    [message, messageIndex],
  );

  return (
    <div
      className={`flex items-center gap-3 font-mono text-sm text-[#8a9b93] ${
        compact ? "py-1" : "rounded-lg border border-[#1c2420] bg-[#0d120f] px-4 py-3"
      }`}
    >
      <span className="text-base text-[#bc687c]/80">{BRAILLE_FRAMES[frameIndex]}</span>
      <span className="tracking-[0.02em]">{activeMessage}</span>
    </div>
  );
}
