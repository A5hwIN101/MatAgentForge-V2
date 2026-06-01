export type ScreenEventName =
  | "chat.created"
  | "screen.started"
  | "step.started"
  | "step.updated"
  | "text.delta"
  | "trace.delta"
  | "critique.ready"
  | "feedback.saved"
  | "screen.completed"
  | "screen.failed";

export type StreamStepName =
  | "load_domain_rules"
  | "candidate_analysis"
  | "rule_verification"
  | "contradiction_detection"
  | "critique_generation"
  | "finalize_critique";

export type StreamStatus = "pending" | "in_progress" | "completed" | "failed";

export type WorkflowStep = {
  id: StreamStepName;
  number: string;
  title: string;
  label: string;
  status: StreamStatus;
  detail?: string;
  terminalText?: string;
};

export type StepEventData = {
  step: StreamStepName;
  label: string;
  status: StreamStatus;
  meta?: Record<string, unknown>;
};

export type TextDeltaEventData = {
  delta: string;
};

export type TraceDeltaEventData = {
  delta: Record<string, unknown>;
};

export type CritiqueReadyEventData = {
  critiqueId: string;
  payload: Record<string, unknown>;
};

export type ScreenEventData =
  | StepEventData
  | TextDeltaEventData
  | TraceDeltaEventData
  | CritiqueReadyEventData
  | Record<string, unknown>;

export type ScreenEvent = {
  event: ScreenEventName;
  chatId: string;
  runId: string;
  timestamp: string;
  data: ScreenEventData;
};
