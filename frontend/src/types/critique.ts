export type Flag = {
  icon: string;
  text: string;
  severity: string;
};

export type Suggestion = {
  text: string;
  rationale: string;
};

export type Citation = {
  rule_id: string;
  rule_name: string;
  arxiv_id: string;
  paper_title: string;
  authors: string;
  year: number | null;
  url: string;
  evidence_from_paper?: string | null;
};

export type Contradiction = {
  rule_a: string;
  rule_b: string;
  type: string;
  resolution: string;
  llm_reasoning: string;
};

export type CritiqueTrace = {
  rules_matched: string[];
  contradictions: Contradiction[];
  citations: Citation[];
};

export type CritiqueCard = {
  id: string;
  material_formula: string;
  verdict: string;
  score: number;
  domain_rules_passed: number;
  domain_rules_total: number;
  flags: Flag[];
  suggestions: Suggestion[];
  explanation: string;
  trace: CritiqueTrace;
};
