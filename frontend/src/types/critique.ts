export type CritiqueFlagKind = "warning" | "success" | "info";

export type CritiqueFlag = {
  kind: CritiqueFlagKind;
  label: string;
  detail?: string;
};

export type CritiqueSuggestion = {
  label: string;
  detail?: string;
};

export type CritiqueCitation = {
  label: string;
  source: string;
};

export type CritiqueSummary = {
  rulesPassed: number;
  rulesTotal: number;
  critiqueScore: number;
  verdict: string;
};

export type CritiqueSections = {
  flags: CritiqueFlag[];
  suggestions: CritiqueSuggestion[];
  citations?: CritiqueCitation[];
};

export type CritiqueTracePreview = {
  contradictionCount: number;
  evidenceCount: number;
};

export type Critique = {
  id: string;
  chatId: string;
  chatItemId: string;
  materialId: string;
  runId: string;
  summary: CritiqueSummary;
  sections: CritiqueSections;
  traceJson?: Record<string, unknown>;
  tracePreview?: CritiqueTracePreview;
  modelName: string;
  promptVersion: string;
  rulesetVersion: string;
  createdAt: string;
};
