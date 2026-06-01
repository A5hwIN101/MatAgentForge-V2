"use client";

import { useState } from "react";

import { InputBox } from "@/features/chat/InputBox";
import { MessageList } from "@/features/chat/MessageList";
import { Sidebar } from "@/features/chat/Sidebar";
import { useChat } from "@/hooks/useChat";
import { useScreening } from "@/features/screening/useScreening";

function AtomMark({ className = "h-12 w-12" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 64 64"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="32" cy="32" r="3.5" fill="currentColor" stroke="none" />
      <ellipse cx="32" cy="32" rx="23" ry="9.5" />
      <ellipse cx="32" cy="32" rx="23" ry="9.5" transform="rotate(60 32 32)" />
      <ellipse cx="32" cy="32" rx="23" ry="9.5" transform="rotate(120 32 32)" />
    </svg>
  );
}

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
    clearHistory,
    refreshChats,
    refreshChatDetail,
    appendLocalItem,
  } = useChat();
  const screening = useScreening();
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSubmittingFormula, setIsSubmittingFormula] = useState(false);
  const inputDisabled = screening.isStreaming || isSubmittingFormula;

  const hasWorkspaceContent = (activeChatDetail?.items.length ?? 0) > 0 || isLoadingDetail;

  const handleSubmitFormula = async (incomingChatId: string | null, formula: string) => {
    if (inputDisabled) {
      return;
    }

    setIsSubmittingFormula(true);
    try {
      const chat = activeChat ?? (await createChat(`${formula} screening`));
      if (!incomingChatId) {
        setActiveChat(chat.id);
      }

      appendLocalItem(chat.id, {
        itemType: "user_message",
        role: "user",
        contentText: formula,
      }, chat);

      await screening.startScreening(chat.id, formula);
      await Promise.all([refreshChatDetail(chat.id), refreshChats()]);
    } finally {
      setIsSubmittingFormula(false);
    }
  };

  return (
    <main className="h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(188,104,124,0.08),_transparent_20%),linear-gradient(180deg,_#060907_0%,_#090c0a_52%,_#060806_100%)] text-slate-100">
      <div className="flex h-full min-h-0">
        <Sidebar
          chats={chats}
          activeChatId={activeChatId}
          isLoading={isLoadingChats}
          isHistoryOpen={isHistoryOpen}
          onSelectChat={(chatId) => {
            screening.reset();
            setActiveChat(chatId);
          }}
          onToggleHistory={() => setIsHistoryOpen((open) => !open)}
          onClearHistory={() => {
            screening.reset();
            void clearHistory();
          }}
          onNewChat={() => {
            screening.reset();
            void createChat("New Chat");
          }}
        />

        <section className="flex h-screen min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex min-h-0 flex-1 flex-col">
            {!hasWorkspaceContent ? (
              <div className="relative flex min-h-0 flex-1 items-center justify-center px-4 py-6 lg:px-8">
                <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(122,138,131,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(122,138,131,0.08)_1px,transparent_1px)] [background-size:48px_48px]" />
                <div className="absolute inset-x-0 top-0 h-56 bg-[radial-gradient(circle_at_center,_rgba(188,104,124,0.12),_transparent_62%)]" />
                <div className="relative z-10 flex w-full max-w-5xl flex-col items-center">
                  <div className="w-full max-w-4xl rounded-[2rem] border border-[#1b2420] bg-[#090d0b]/88 px-6 py-10 shadow-[0_40px_140px_rgba(0,0,0,0.45)] backdrop-blur md:px-10 md:py-12">
                    <div className="mx-auto flex max-w-3xl flex-col items-center gap-8 text-center">
                      <div className="flex flex-col items-center gap-5 md:flex-row md:items-center md:text-left">
                        <div className="flex h-18 w-18 items-center justify-center rounded-[1.4rem] border border-[#23302a] bg-[#101612] text-[#ff6a68] shadow-lg shadow-black/25">
                          <AtomMark className="h-10 w-10" />
                        </div>
                        <div className="space-y-3">
                          <div className="font-mono text-[11px] uppercase tracking-[0.35em] text-[#6f7f79]">
                            Scientific terminal workspace
                          </div>
                          <h1 className="font-mono text-4xl font-semibold tracking-[0.02em] text-slate-50 md:text-5xl">
                            MatAgent Forge
                          </h1>
                          <p className="font-mono text-sm text-[#86958f] md:text-base">
                            Citation-backed battery material screening.
                          </p>
                        </div>
                      </div>

                      <div className="w-full">
                        <InputBox
                          chatId={activeChatId}
                          disabled={inputDisabled}
                          onSubmit={handleSubmitFormula}
                          variant="workspace"
                          examples={[]}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="shrink-0 px-4 pt-4 lg:px-6">
                  {error ? (
                    <p className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-4 py-3 font-mono text-sm text-amber-200">
                      {error}
                    </p>
                  ) : null}
                </div>

                <div className="flex min-h-0 flex-1 flex-col px-4 py-4 lg:px-6">
                  <MessageList
                    messages={activeChatDetail?.items ?? []}
                    workflowSteps={screening.workflowSteps}
                    isStreaming={screening.isStreaming}
                    streamText={screening.streamText}
                    streamCritique={screening.critique}
                    streamFailure={screening.failure}
                  />
                </div>

                {isLoadingDetail ? (
                  <div className="px-4 pb-3 lg:px-6">
                    <div className="rounded-xl border border-dashed border-[#1f2722] bg-[#0b100d] px-4 py-3 font-mono text-sm text-[#7a8a83]">
                      Loading session detail...
                    </div>
                  </div>
                ) : null}

                <div className="shrink-0 border-t border-[#1c2420] bg-[#090d0b]/96 px-4 py-3 backdrop-blur lg:px-6">
                  <InputBox
                    chatId={activeChatId}
                    disabled={inputDisabled}
                    onSubmit={handleSubmitFormula}
                  />
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
