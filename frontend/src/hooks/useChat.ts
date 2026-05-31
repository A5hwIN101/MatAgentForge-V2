"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { Chat, ChatDetail, ChatItem } from "@/types";

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
  clearHistory: () => Promise<void>;
  refreshChats: () => Promise<void>;
  appendLocalItem: (
    chatId: string,
    item: Omit<ChatItem, "id" | "chatId" | "sequenceNo" | "createdAt">,
  ) => void;
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

const BACKEND_URL = "http://localhost:8000";

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

function mapChatItem(serverItem: ServerChatItem, index: number): ChatItem {
  const itemType =
    serverItem.type === "status_stream"
      ? "agent_status"
      : (serverItem.type as ChatItem["itemType"]);
  let contentJson: ChatItem["contentJson"] | undefined;
  let contentText: string | undefined = serverItem.content;

  if (itemType === "critique_card" || itemType === "error_card") {
    try {
      contentJson = JSON.parse(serverItem.content) as ChatItem["contentJson"];
      contentText = undefined;
    } catch {
      contentJson = undefined;
    }
  }

  return {
    id: serverItem.id,
    chatId: serverItem.chat_id,
    itemType,
    role: itemType === "user_message" ? "user" : "assistant",
    contentText,
    contentJson,
    sequenceNo: index + 1,
    createdAt: serverItem.created_at,
  };
}

export function useChat(apiBaseUrl = BACKEND_URL): UseChatResult {
  const [chats, setChats] = useState<Chat[]>([]);
  const [chatDetails, setChatDetails] = useState<Record<string, ChatDetail>>({});
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshChats = useCallback(async () => {
    setIsLoadingChats(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/chats`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch chats (${response.status})`);
      }

      const payload = (await response.json()) as ServerChat[];
      const mapped = payload.map(mapChat);
      setChats(mapped);
      setActiveChatId((current) => current ?? mapped[0]?.id ?? null);
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Unable to load chats");
    } finally {
      setIsLoadingChats(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void refreshChats();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [refreshChats]);

  useEffect(() => {
    const loadDetail = async () => {
      if (!activeChatId) {
        return;
      }

      setIsLoadingDetail(true);
      try {
        const response = await fetch(`${apiBaseUrl}/api/chats/${activeChatId}`, {
          cache: "no-store",
        });
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

        setChatDetails((current) => {
          const existingDetail = current[activeChatId];
          const persistedItems = (payload.items ?? []).map(mapChatItem);
          const optimisticItems =
            existingDetail?.items.filter((item) => item.id.startsWith("local-")) ?? [];

          return {
            ...current,
            [activeChatId]: {
              chat: baseChat,
              items: [...optimisticItems, ...persistedItems],
            },
          };
        });
        setError(null);
      } catch (detailError) {
        setError(detailError instanceof Error ? detailError.message : "Unable to load chat detail");
      } finally {
        setIsLoadingDetail(false);
      }
    };

    void loadDetail();
  }, [activeChatId, apiBaseUrl, chats]);

  const createChat = useCallback(
    async (title = "New Chat") => {
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
      setError(null);
      return chat;
    },
    [apiBaseUrl],
  );

  const clearHistory = useCallback(async () => {
    const response = await fetch(`${apiBaseUrl}/api/chats`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`Failed to clear chat history (${response.status})`);
    }

    setChats([]);
    setChatDetails({});
    setActiveChatId(null);
    setError(null);
  }, [apiBaseUrl]);

  const appendLocalItem = useCallback(
    (chatId: string, item: Omit<ChatItem, "id" | "chatId" | "sequenceNo" | "createdAt">) => {
      const now = new Date().toISOString();

      setChatDetails((current) => {
        const fallbackChat = chats.find((chat) => chat.id === chatId);
        if (!fallbackChat && !current[chatId]) {
          return current;
        }

        const existingDetail = current[chatId] ?? {
          chat: fallbackChat!,
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
                  item.itemType === "user_message"
                    ? item.contentText ?? chat.lastMaterialFormula
                    : chat.lastMaterialFormula,
              }
            : chat,
        ),
      );
    },
    [chats],
  );

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
    usingMockData: false,
    setActiveChat: setActiveChatId,
    createChat,
    clearHistory,
    refreshChats,
    appendLocalItem,
  };
}
