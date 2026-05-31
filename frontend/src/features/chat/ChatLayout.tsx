"use client";

import { useMemo } from "react";

import { InputBox } from "@/features/chat/InputBox";
import { MessageList } from "@/features/chat/MessageList";
import { Sidebar } from "@/features/chat/Sidebar";
import { useChat } from "@/hooks/useChat";
import { useScreening } from "@/features/screening/useScreening";
import type { ChatItem } from "@/types";

export function ChatLayout() {
  const {
    chats,
    activeChatId,
    activeChat,
    activeChatDetail,
    isLoadingChats,
    isLoadingDetail,
    error,
    setActiveChat,
    createChat,
    appendLocalItem,
  } = useChat();
  const screening = useScreening();

  const timelineMessages = useMemo<ChatItem[]>(() => {
    const persistedItems = activeChatDetail?.items ?? [];
    if (!screening.isStreaming && !screening.critique && !screening.streamText && screening.currentStepLabels.length === 0) {
      return persistedItems;
    }

    const ephemeralItems: ChatItem[] = [];
    let sequenceStart = persistedItems.length;

    screening.currentStepLabels.forEach((label) => {
      sequenceStart += 1;
      ephemeralItems.push({
        id: `stream-step-${sequenceStart}-${label}`,
        chatId: activeChatId ?? "stream",
        itemType: "agent_status",
        role: "system",
        contentText: label,
        sequenceNo: sequenceStart,
        createdAt: new Date().toISOString(),
      });
    });

    if (screening.streamText.trim()) {
      sequenceStart += 1;
      ephemeralItems.push({
        id: `stream-text-${sequenceStart}`,
        chatId: activeChatId ?? "stream",
        itemType: "agent_text",
        role: "assistant",
        contentText: screening.streamText.trim(),
        sequenceNo: sequenceStart,
        createdAt: new Date().toISOString(),
      });
    }

    if (screening.critique) {
      sequenceStart += 1;
      ephemeralItems.push({
        id: screening.critique.id,
        chatId: activeChatId ?? "stream",
        itemType: "critique_card",
        role: "assistant",
        contentJson: screening.critique,
        sequenceNo: sequenceStart,
        createdAt: new Date().toISOString(),
      });
    }

    return [...persistedItems, ...ephemeralItems];
  }, [
    activeChatDetail?.items,
    activeChatId,
    screening.critique,
    screening.currentStepLabels,
    screening.isStreaming,
    screening.streamText,
  ]);

  const handleSubmitFormula = async (incomingChatId: string | null, formula: string) => {
    const chat = activeChat ?? (await createChat(`${formula} screening`));
    if (!incomingChatId) {
      setActiveChat(chat.id);
    }

    appendLocalItem(chat.id, {
      itemType: "user_message",
      role: "user",
      contentText: formula,
    });

    await screening.startScreening(chat.id, formula);
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.14),_transparent_28%),linear-gradient(180deg,_#020617_0%,_#0f172a_52%,_#020617_100%)] px-5 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-7xl gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Sidebar
          chats={chats}
          activeChatId={activeChatId}
          isLoading={isLoadingChats}
          onSelectChat={setActiveChat}
          onNewChat={() => {
            void createChat("New Chat");
          }}
        />

        <section className="flex min-h-[70vh] flex-col rounded-[2rem] border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/30 sm:p-6">
          <header className="border-b border-slate-800 pb-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.34em] text-emerald-300">
                  MatAgent-Critique
                </p>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">
                  {activeChat?.title ?? "Chat Interface"}
                </h1>
              </div>
              <div className="text-sm text-slate-400">Live backend connection</div>
            </div>
            {error ? <p className="mt-3 text-sm text-amber-300">{error}</p> : null}
            {screening.error ? (
              <p className="mt-3 text-sm text-rose-300">{screening.error}</p>
            ) : null}
          </header>

          <div className="flex flex-1 flex-col gap-5 py-5">
            <MessageList messages={timelineMessages} />

            {isLoadingDetail ? (
              <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-3 text-sm text-slate-500">
                Loading chat detail...
              </div>
            ) : null}
          </div>

          <div className="border-t border-slate-800 pt-5">
            <InputBox
              chatId={activeChatId}
              disabled={screening.isStreaming}
              onSubmit={handleSubmitFormula}
            />
          </div>
        </section>
      </div>
    </main>
  );
}
