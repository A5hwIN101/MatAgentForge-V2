export type FeedbackAction = "approve" | "reject" | "modify";

export type Feedback = {
  id: string;
  critiqueId: string;
  chatId: string;
  materialId: string;
  action: FeedbackAction;
  reasonText?: string;
  requestedChangesJson?: Record<string, unknown>;
  critiqueSnapshotJson: Record<string, unknown>;
  modelName: string;
  promptVersion: string;
  rulesetVersion: string;
  userSessionId?: string;
  createdAt: string;
};

export type FeedbackCreateRequest = {
  action: FeedbackAction;
  reasonText?: string;
};

export type FeedbackCreateResponse = {
  id: string;
  status: "saved";
};
