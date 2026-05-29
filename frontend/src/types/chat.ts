export type ChatStatus = "active" | "archived";

export type Chat = {
  id: string;
  title: string;
  lastMaterialFormula?: string;
  lastVerdict?: string;
  status: ChatStatus;
  createdAt: string;
  updatedAt: string;
};

export type ChatItemType =
  | "user_message"
  | "status_stream"
  | "agent_text"
  | "critique_card";

export type ChatRole = "user" | "assistant" | "system";

export type ChatItem = {
  id: string;
  chatId: string;
  itemType: ChatItemType;
  role: ChatRole;
  contentText?: string;
  contentJson?: Record<string, unknown>;
  sequenceNo: number;
  createdAt: string;
};

export type ChatDetail = {
  chat: Chat;
  items: ChatItem[];
};
