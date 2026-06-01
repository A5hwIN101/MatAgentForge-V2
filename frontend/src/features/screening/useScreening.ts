"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type {
  CritiqueCard,
  ScreenEvent,
  ScreeningErrorCard,
  StreamStatus,
  WorkflowStep,
} from "@/types";

const WORKFLOW_STEP_ORDER: Array<Pick<WorkflowStep, "id" | "number" | "title">> = [
  { id: "candidate_analysis", number: "01", title: "Parse Material" },
  { id: "load_domain_rules", number: "02", title: "Load Rules" },
  { id: "rule_verification", number: "03", title: "Verify Rules" },
  { id: "finalize_critique", number: "04", title: "Final Assessment" },
];

type ScreeningState = {
  events: ScreenEvent[];
  streamText: string;
  critique: CritiqueCard | null;
  failure: ScreeningErrorCard | null;
  isStreaming: boolean;
  error: string | null;
};

type UseScreeningResult = ScreeningState & {
  activeRunId: string | null;
  workflowSteps: WorkflowStep[];
  startScreening: (chatId: string, formula: string) => Promise<void>;
  reset: () => void;
};

const initialState: ScreeningState = {
  events: [],
  streamText: "",
  critique: null,
  failure: null,
  isStreaming: false,
  error: null,
};

function isStepEvent(
  event: ScreenEvent,
): event is ScreenEvent & { data: { step: WorkflowStep["id"]; status?: StreamStatus; label?: string } } {
  return event.event === "step.started" || event.event === "step.updated";
}

function normalizeStepStatus(status: unknown): StreamStatus {
  if (
    status === "pending" ||
    status === "in_progress" ||
    status === "completed" ||
    status === "failed"
  ) {
    return status;
  }

  return "pending";
}

function mapWorkflowStepId(stepId: WorkflowStep["id"]): WorkflowStep["id"] {
  if (
    stepId === "contradiction_detection" ||
    stepId === "critique_generation" ||
    stepId === "finalize_critique"
  ) {
    return "finalize_critique";
  }

  return stepId;
}

function buildWorkflowSteps(
  events: ScreenEvent[],
  streamText: string,
  critique: CritiqueCard | null,
  failure: ScreeningErrorCard | null,
): WorkflowStep[] {
  const steps: WorkflowStep[] = WORKFLOW_STEP_ORDER.map((step) => ({
    ...step,
    label: step.title,
    status: "pending" as StreamStatus,
    detail: undefined as string | undefined,
  }));

  const stepIndexById = new Map(steps.map((step, index) => [step.id, index]));
  let activeStepId: WorkflowStep["id"] | null = null;

  events.forEach((event) => {
    if (event.event === "step.started" && isStepEvent(event)) {
      const stepId = mapWorkflowStepId(event.data.step);
      const nextIndex = stepIndexById.get(stepId);
      if (nextIndex === undefined) {
        return;
      }

      if (activeStepId) {
        const previousIndex = stepIndexById.get(activeStepId);
        if (previousIndex !== undefined && steps[previousIndex].status === "in_progress") {
          steps[previousIndex].status = "completed";
        }
      }

      activeStepId = stepId;
      steps[nextIndex].status = "in_progress";
    }

    if (event.event === "step.updated" && isStepEvent(event)) {
      const stepId = mapWorkflowStepId(event.data.step);
      const nextIndex = stepIndexById.get(stepId);
      if (nextIndex === undefined) {
        return;
      }

      steps[nextIndex].status = normalizeStepStatus(event.data.status);
      steps[nextIndex].label =
        typeof event.data.label === "string" ? event.data.label : steps[nextIndex].title;
      steps[nextIndex].detail = steps[nextIndex].label;
    }

    if (event.event === "screen.failed" && activeStepId) {
      const failedIndex = stepIndexById.get(activeStepId);
      if (failedIndex !== undefined) {
        const failedPayload = event.data as Record<string, unknown>;
        steps[failedIndex].status = "failed";
        steps[failedIndex].detail =
          typeof failedPayload.error === "string"
            ? failedPayload.error
            : "Screening failed.";
      }
    }

    if (event.event === "screen.completed") {
      if (activeStepId) {
        const completedIndex = stepIndexById.get(activeStepId);
        if (completedIndex !== undefined) {
          steps[completedIndex].status = "completed";
        }
      }

      steps.forEach((step) => {
        if (step.status === "in_progress") {
          step.status = "completed";
        }
      });
    }
  });

  if (streamText.trim()) {
    const critiqueIndex = stepIndexById.get("critique_generation");
    if (critiqueIndex !== undefined) {
      steps[critiqueIndex].detail = streamText.trim();
      steps[critiqueIndex].terminalText = streamText.trim();
      if (steps[critiqueIndex].status === "pending") {
        steps[critiqueIndex].status = "in_progress";
      }
    }
  }

  if (critique) {
    const loadRules = stepIndexById.get("load_domain_rules");
    const ruleVerification = stepIndexById.get("rule_verification");
    const finalize = stepIndexById.get("finalize_critique");

    if (loadRules !== undefined) {
      steps[loadRules].status = "completed";
      steps[loadRules].detail = `${critique.domain_rules_total} domain rules loaded for review.`;
    }

    if (ruleVerification !== undefined) {
      steps[ruleVerification].status = "completed";
      steps[ruleVerification].detail = `${critique.trace.rules_matched.length} rules applied with material-specific reasoning.`;
    }

    if (finalize !== undefined) {
      steps[finalize].status = failure ? "failed" : "completed";
      steps[finalize].detail =
        critique.trace.contradictions.length > 0
          ? `${critique.trace.contradictions.length} contradiction checks surfaced reviewable tradeoffs.`
          : "No contradiction conflicts were retained in the final assessment.";
      if (!failure) {
        steps[finalize].detail = critique.verdict.toLowerCase().includes("infeasible")
          ? "Assessment: Not Viable."
          : `${critique.verdict} with risk score ${critique.score} / 10.`;
      }
    }
  }

  return steps;
}

export function useScreening(apiBaseUrl = API_BASE_URL): UseScreeningResult {
  const [state, setState] = useState<ScreeningState>(initialState);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const activeRequestIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abortActiveRequest = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    activeRequestIdRef.current = null;
    setActiveRunId(null);
  }, []);

  const reset = useCallback(() => {
    abortActiveRequest();
    setState(initialState);
  }, [abortActiveRequest]);

  useEffect(() => {
    return () => {
      abortActiveRequest();
    };
  }, [abortActiveRequest]);

  const startScreening = useCallback(
    async (chatId: string, formula: string) => {
      abortActiveRequest();

      const requestId = crypto.randomUUID();
      const controller = new AbortController();
      let streamRunId: string | null = null;

      activeRequestIdRef.current = requestId;
      abortControllerRef.current = controller;
      setActiveRunId(null);
      setState({
        events: [],
        streamText: "",
        critique: null,
        failure: null,
        isStreaming: true,
        error: null,
      });

      try {
        const response = await fetch(`${apiBaseUrl}/api/chats/${chatId}/screen`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ formula }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Screening request failed with status ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          if (activeRequestIdRef.current !== requestId) {
            await reader.cancel();
            return;
          }

          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });

          while (buffer.includes("\n\n")) {
            const separatorIndex = buffer.indexOf("\n\n");
            const rawEvent = buffer.slice(0, separatorIndex);
            buffer = buffer.slice(separatorIndex + 2);

            const dataLine = rawEvent
              .split("\n")
              .find((line) => line.startsWith("data: "));

            if (!dataLine) {
              continue;
            }

            const payload = dataLine.slice(6).trim();
            if (!payload) {
              continue;
            }

            const event = JSON.parse(payload) as ScreenEvent;

            if (activeRequestIdRef.current !== requestId) {
              continue;
            }

            if (!streamRunId) {
              streamRunId = event.runId;
              setActiveRunId(event.runId);
            }

            if (event.runId !== streamRunId) {
              continue;
            }

            setState((current) => {
              const nextEvents = [...current.events, event];
              let nextText = current.streamText;
              let nextCritique = current.critique;
              let nextFailure = current.failure;
              let nextError = current.error;
              let nextStreaming = current.isStreaming;
              const eventData = event.data as Record<string, unknown>;

              if (event.event === "text.delta" && typeof eventData.delta === "string") {
                nextText += eventData.delta;
              }

              if (event.event === "critique.ready") {
                nextCritique = event.data as unknown as CritiqueCard;
                nextFailure = null;
              }

              if (event.event === "screen.failed") {
                nextCritique = null;
                nextFailure = {
                  title:
                    typeof eventData.title === "string"
                      ? eventData.title
                      : "Unable to screen material",
                  message:
                    typeof eventData.error === "string"
                      ? eventData.error
                      : "Screening failed.",
                  hint:
                    typeof eventData.hint === "string" ? eventData.hint : undefined,
                  code:
                    typeof eventData.code === "string" ? eventData.code : undefined,
                };
                nextError =
                  typeof eventData.error === "string"
                    ? eventData.error
                    : "Screening failed.";
                nextStreaming = false;
              }

              if (event.event === "screen.completed") {
                nextStreaming = false;
              }

              return {
                events: nextEvents,
                streamText: nextText,
                critique: nextCritique,
                failure: nextFailure,
                isStreaming: nextStreaming,
                error: nextError,
              };
            });
          }
        }

        if (activeRequestIdRef.current === requestId) {
          setState((current) => ({
            ...current,
            isStreaming: false,
          }));
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        if (activeRequestIdRef.current !== requestId) {
          return;
        }

        setState((current) => ({
          ...current,
          failure: {
            title: "Unable to screen material",
            message: error instanceof Error ? error.message : "Unknown screening error",
          },
          isStreaming: false,
          error: error instanceof Error ? error.message : "Unknown screening error",
        }));
      } finally {
        if (activeRequestIdRef.current === requestId) {
          activeRequestIdRef.current = null;
          abortControllerRef.current = null;
        }
      }
    },
    [abortActiveRequest, apiBaseUrl],
  );

  const workflowSteps = useMemo(
    () => buildWorkflowSteps(state.events, state.streamText, state.critique, state.failure),
    [state.critique, state.events, state.failure, state.streamText],
  );

  return {
    ...state,
    activeRunId,
    workflowSteps,
    startScreening,
    reset,
  };
}
