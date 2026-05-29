"use client";

import { useCallback, useMemo, useState } from "react";

import type { CritiqueCard } from "@/types";

type ScreeningEvent = {
  event: string;
  chat_id: string;
  run_id: string;
  timestamp: string;
  data: Record<string, unknown>;
};

type ScreeningState = {
  events: ScreeningEvent[];
  streamText: string;
  critique: CritiqueCard | null;
  isStreaming: boolean;
  error: string | null;
};

type UseScreeningResult = ScreeningState & {
  currentStepLabels: string[];
  startScreening: (chatId: string, formula: string) => Promise<void>;
  reset: () => void;
};

const initialState: ScreeningState = {
  events: [],
  streamText: "",
  critique: null,
  isStreaming: false,
  error: null,
};

export function useScreening(apiBaseUrl = "http://127.0.0.1:8000"): UseScreeningResult {
  const [state, setState] = useState<ScreeningState>(initialState);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  const startScreening = useCallback(
    async (chatId: string, formula: string) => {
      setState({
        events: [],
        streamText: "",
        critique: null,
        isStreaming: true,
        error: null,
      });

      try {
        const response = await fetch(`${apiBaseUrl}/api/chats/${chatId}/screen`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ formula }),
        });

        if (!response.ok || !response.body) {
          throw new Error(`Screening request failed with status ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) {
              continue;
            }

            const json = line.slice(6).trim();
            if (!json) {
              continue;
            }

            const event = JSON.parse(json) as ScreeningEvent;

            setState((current) => {
              const nextEvents = [...current.events, event];
              let nextText = current.streamText;
              let nextCritique = current.critique;
              let isStreaming = current.isStreaming;

              if (event.event === "text.delta" && typeof event.data.delta === "string") {
                nextText += event.data.delta;
              }

              if (event.event === "critique.ready") {
                nextCritique = event.data as unknown as CritiqueCard;
              }

              if (event.event === "screen.completed") {
                isStreaming = false;
              }

              return {
                events: nextEvents,
                streamText: nextText,
                critique: nextCritique,
                isStreaming,
                error: null,
              };
            });
          }
        }

        setState((current) => ({
          ...current,
          isStreaming: false,
        }));
      } catch (error) {
        setState((current) => ({
          ...current,
          isStreaming: false,
          error: error instanceof Error ? error.message : "Unknown screening error",
        }));
      }
    },
    [apiBaseUrl],
  );

  const currentStepLabels = useMemo(
    () =>
      state.events
        .filter((event) => event.event === "step.updated")
        .map((event) => String(event.data.label ?? "")),
    [state.events],
  );

  return {
    ...state,
    currentStepLabels,
    startScreening,
    reset,
  };
}
