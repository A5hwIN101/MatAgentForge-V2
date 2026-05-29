"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { Chat, ChatDetail, ChatItem, CritiqueCard } from "@/types";

type UseChatResult = {
  chats: Chat[];
  activeChatId: string | null;
  activeChat: Chat | null;
  activeChatDetail: ChatDetail | null;
  isLoadingChats: boolean;
  isLoadingDetail: boolean;
  error: string | null;
  usingMockData: boolean;
  setActiveChat: (chatId: string) => void;
  createChat: (title?: string) => Promise<Chat>;
  refreshChats: () => Promise<void>;
  appendLocalItem: (
    chatId: string,
    item: Omit<ChatItem, "id" | "chatId" | "sequenceNo" | "createdAt">,
  ) => void;
  replaceLocalItems: (chatId: string, items: ChatItem[]) => void;
};

type ServerChat = {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_material_formula?: string | null;
  last_verdict?: string | null;
};

type ServerChatItem = {
  id: string;
  chat_id: string;
  type: string;
  content: string;
  created_at: string;
};

type ServerChatDetail = {
  id?: string;
  title?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  chat?: ServerChat;
  items?: ServerChatItem[];
};

const MOCK_CRITIQUE: CritiqueCard = {
  id: "critique-sidebar-demo",
  material_formula: "LiCoO2",
  verdict: "Feasible with concerns",
  score: 7.2,
  domain_rules_passed: 3,
  domain_rules_total: 3,
  flags: [
    { icon: "⚠", text: "Co scarcity — cost risk at scale", severity: "warning" },
    { icon: "⚠", text: "Thermal runaway above 150°C", severity: "warning" },
    { icon: "✅", text: "Ionic conductivity — strong", severity: "success" },
  ],
  suggestions: [
    {
      text: "Substitute Ni-Mn for Co (NMC path)",
      rationale: "Reduce cobalt dependency while preserving cathode performance.",
    },
  ],
  explanation: "Strong conductivity, but cost and thermal constraints need attention.",
  trace: {
    rules_matched: ["high_ionic_conductivity", "cobalt_scarcity_penalty"],
    contradictions: [],
    citations: [
      {
        rule_id: "high_ionic_conductivity",
        source: "mock_materials_project_rulepack",
        confidence: 0.91,
      },
    ],
  },
};

const MOCK_CHATS: Chat[] = [
  {
    id: "mock-chat-1",
    title: "LiCoO2 screening",
    lastMaterialFormula: "LiCoO2",
    lastVerdict: "Feasible with concerns",
    status: "active",
    createdAt: new Date("2026-05-28T09:00:00Z").toISOString(),
    updatedAt: new Date("2026-05-28T09:12:00Z").toISOString(),
  },
  {
    id: "mock-chat-2",
    title: "LMFP candidate",
    lastMaterialFormula: "LiMnFePO4",
    lastVerdict: "Promising",
    status: "active",
    createdAt: new Date("2026-05-28T11:00:00Z").toISOString(),
    updatedAt: new Date("2026-05-28T11:14:00Z").toISOString(),
  },
];

const MOCK_CHAT_DETAILS: Record<string, ChatDetail> = {
  "mock-chat-1": {
    chat: MOCK_CHATS[0],
    items: [
      {
        id: "mock-1-user",
        chatId: "mock-chat-1",
        itemType: "user_message",
        role: "user",
        contentText: "LiCoO2",
        sequenceNo: 1,
        createdAt: new Date("2026-05-28T09:01:00Z").toISOString(),
      },
      {
        id: "mock-1-text",
        chatId: "mock-chat-1",
        itemType: "agent_text",
        role: "assistant",
        contentText: "Previous screening highlighted cobalt cost pressure and thermal concerns.",
        sequenceNo: 2,
        createdAt: new Date("2026-05-28T09:02:00Z").toISOString(),
      },
      {
        id: "mock-1-critique",
        chatId: "mock-chat-1",
        itemType: "critique_card",
        role: "assistant",
        contentJson: MOCK_CRITIQUE,
        sequenceNo: 3,
        createdAt: new Date("2026-05-28T09:03:00Z").toISOString(),
      },
    ],
  },
  "mock-chat-2": {
    chat: MOCK_CHATS[1],
    items: [
      {
        id: "mock-2-user",
        chatId: "mock-chat-2",
        itemType: "user_message",
        role: "user",
        contentText: "LiMnFePO4",
        sequenceNo: 1,
        createdAt: new Date("2026-05-28T11:02:00Z").toISOString(),
      },
      {
        id: "mock-2-status",
        chatId: "mock-chat-2",
        itemType: "agent_status",
        role: "system",
        contentText: "Ready for next screening pass.",
        sequenceNo: 2,
        createdAt: new Date("2026-05-28T11:03:00Z").toISOString(),
      },
    ],
  },
};

function mapChat(serverChat: ServerChat): Chat {
  return {
    id: serverChat.id,
    title: serverChat.title,
    lastMaterialFormula: serverChat.last_material_formula ?? undefined,
    lastVerdict: serverChat.last_verdict ?? undefined,
    status: (serverChat.status as Chat["status"]) ?? "active",
    createdAt: serverChat.created_at,
    updatedAt: serverChat.updated_at,
  };
}

function mapChatItem(serverItem: ServerChatItem): ChatItem {
  const itemType =
    serverItem.type === "status_stream"
      ? "agent_status"
      : (serverItem.type as ChatItem["itemType"]);

  return {
    id: serverItem.id,
    chatId: serverItem.chat_id,
    itemType,
    role: itemType === "user_message" ? "user" : "assistant",
    contentText: serverItem.content,
    sequenceNo: 0,
    createdAt: serverItem.created_at,
  };
}

export function useChat(apiBaseUrl = "http://127.0.0.1:8000"): UseChatResult {
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatDetails, setChatDetails] = useState<Record<string, ChatDetail>>({});
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usingMockData, setUsingMockData] = useState(false);

  const applyMockData = useCallback(() => {
    setChats(MOCK_CHATS);
    setChatDetails(MOCK_CHAT_DETAILS);
    setActiveChatId((current) => current ?? MOCK_CHATS[0]?.id ?? null);
    setUsingMockData(true);
  }, []);

  const refreshChats = useCallback(async () => {
    setIsLoadingChats(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/chats`);
      if (!response.ok) {
        throw new Error(`Failed to fetch chats (${response.status})`);
      }

      const payload = (await response.json()) as ServerChat[];
      if (payload.length === 0) {
        applyMockData();
        setError(null);
        return;
      }

      const mapped = payload.map(mapChat);
      setChats(mapped);
      setActiveChatId((current) => current ?? mapped[0]?.id ?? null);
      setUsingMockData(false);
      setError(null);
    } catch (fetchError) {
      applyMockData();
      setError(fetchError instanceof Error ? fetchError.message : "Unable to load chats");
    } finally {
      setIsLoadingChats(false);
    }
  }, [apiBaseUrl, applyMockData]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void refreshChats();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [refreshChats]);

  useEffect(() => {
    const loadDetail = async () => {
      if (!activeChatId || chatDetails[activeChatId]) {
        return;
      }

      setIsLoadingDetail(true);
      try {
        const response = await fetch(`${apiBaseUrl}/api/chats/${activeChatId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch chat detail (${response.status})`);
        }

        const payload = (await response.json()) as ServerChatDetail;
        const baseChat =
          payload.chat !== undefined
            ? mapChat(payload.chat)
            : chats.find((chat) => chat.id === activeChatId) ?? null;

        if (!baseChat) {
          throw new Error("Chat detail missing chat metadata");
        }

        setChatDetails((current) => ({
          ...current,
          [activeChatId]: {
            chat: baseChat,
            items: (payload.items ?? []).map((item, index) => ({
              ...mapChatItem(item),
              sequenceNo: index + 1,
            })),
          },
        }));
        setUsingMockData(false);
        setError(null);
      } catch (detailError) {
        if (MOCK_CHAT_DETAILS[activeChatId]) {
          setChatDetails((current) => ({
            ...current,
            [activeChatId]: MOCK_CHAT_DETAILS[activeChatId],
          }));
          setUsingMockData(true);
        }
        setError(detailError instanceof Error ? detailError.message : "Unable to load chat detail");
      } finally {
        setIsLoadingDetail(false);
      }
    };

    void loadDetail();
  }, [activeChatId, apiBaseUrl, chatDetails, chats]);

  const createChat = useCallback(
    async (title = "New Chat") => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/chats`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ title }),
        });
        if (!response.ok) {
          throw new Error(`Failed to create chat (${response.status})`);
        }

        const payload = (await response.json()) as ServerChat;
        const chat = mapChat(payload);

        setChats((current) => [chat, ...current]);
        setChatDetails((current) => ({
          ...current,
          [chat.id]: {
            chat,
            items: [],
          },
        }));
        setActiveChatId(chat.id);
        setUsingMockData(false);
        setError(null);
        return chat;
      } catch {
        const chat: Chat = {
          id: `mock-created-${crypto.randomUUID()}`,
          title,
          status: "active",
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        setChats((current) => [chat, ...current]);
        setChatDetails((current) => ({
          ...current,
          [chat.id]: {
            chat,
            items: [],
          },
        }));
        setActiveChatId(chat.id);
        setUsingMockData(true);
        return chat;
      }
    },
    [apiBaseUrl],
  );

  const appendLocalItem = useCallback(
    (chatId: string, item: Omit<ChatItem, "id" | "chatId" | "sequenceNo" | "createdAt">) => {
      const now = new Date().toISOString();

      setChatDetails((current) => {
        const existingDetail = current[chatId] ?? {
          chat: chats.find((chat) => chat.id === chatId)!,
          items: [],
        };
        const nextItem: ChatItem = {
          id: `local-${crypto.randomUUID()}`,
          chatId,
          sequenceNo: existingDetail.items.length + 1,
          createdAt: now,
          ...item,
        };

        return {
          ...current,
          [chatId]: {
            ...existingDetail,
            items: [...existingDetail.items, nextItem],
          },
        };
      });

      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                updatedAt: now,
                lastMaterialFormula:
                  item.itemType === "user_message" ? item.contentText ?? chat.lastMaterialFormula : chat.lastMaterialFormula,
              }
            : chat,
        ),
      );
    },
    [chats],
  );

  const replaceLocalItems = useCallback((chatId: string, items: ChatItem[]) => {
    setChatDetails((current) => {
      const existing = current[chatId];
      if (!existing) {
        return current;
      }

      return {
        ...current,
        [chatId]: {
          ...existing,
          items,
        },
      };
    });
  }, []);

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeChatId) ?? null,
    [activeChatId, chats],
  );

  const activeChatDetail = activeChatId ? chatDetails[activeChatId] ?? null : null;

  return {
    chats,
    activeChatId,
    activeChat,
    activeChatDetail,
    isLoadingChats,
    isLoadingDetail,
    error,
    usingMockData,
    setActiveChat: setActiveChatId,
    createChat,
    refreshChats,
    appendLocalItem,
    replaceLocalItems,
  };
}
