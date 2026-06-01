"use client";

import type { Chat } from "@/types";

type SidebarProps = {
  chats: Chat[];
  activeChatId: string | null;
  isLoading: boolean;
  isHistoryOpen: boolean;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void | Promise<void>;
  onClearHistory: () => void | Promise<void>;
  onToggleHistory: () => void;
};

const railButtonBase =
  "flex h-10 w-10 items-center justify-center rounded-lg border font-mono text-[12px] transition";

export function Sidebar({
  chats,
  activeChatId,
  isLoading,
  isHistoryOpen,
  onSelectChat,
  onNewChat,
  onClearHistory,
  onToggleHistory,
}: SidebarProps) {
  const visibleChats = chats.filter(
    (chat) => chat.id === activeChatId || Boolean(chat.lastMaterialFormula || chat.lastVerdict),
  );

  return (
    <aside className="flex h-screen shrink-0">
      <div className="flex w-[68px] flex-col items-center justify-between border-r border-[#1c2420] bg-[#080c0a] px-3 py-4">
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#1c2420] bg-[#0d120f] font-mono text-sm font-semibold text-slate-100">
            MF
          </div>
          <button
            type="button"
            onClick={onToggleHistory}
            className={`${railButtonBase} ${
              isHistoryOpen
                ? "border-[#bc687c]/60 bg-[#bc687c]/10 text-[#e7b4bf]"
                : "border-[#1c2420] bg-[#0d120f] text-[#7a8a83] hover:border-[#2a342f] hover:text-slate-200"
            }`}
            title="Toggle history"
          >
            H
          </button>
          <button
            type="button"
            onClick={() => void onNewChat()}
            className={`${railButtonBase} border-[#1c2420] bg-[#0d120f] text-[#7a8a83] hover:border-[#2a342f] hover:text-slate-200`}
            title="New chat"
          >
            N
          </button>
        </div>

        <button
          type="button"
          onClick={() => {
            const confirmed = window.confirm("Clear all chat history?");
            if (confirmed) {
              void onClearHistory();
            }
          }}
          className={`${railButtonBase} border-[#4e2933] bg-[#241518] text-[#d1a1aa] hover:border-[#bc687c] hover:text-[#f0cad1]`}
          title="Clear history"
        >
          CL
        </button>
      </div>

      {isHistoryOpen ? (
        <div className="flex h-screen w-[228px] min-h-0 flex-col border-r border-[#1c2420] bg-[#0b100d]">
          <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
            <div className="space-y-2">
              {isLoading ? (
                <div className="rounded-lg border border-dashed border-[#1c2420] bg-[#0d120f] px-3 py-4 font-mono text-sm text-[#778680]">
                  Loading screening history...
                </div>
              ) : visibleChats.length > 0 ? (
                visibleChats.map((chat) => {
                  const isActive = chat.id === activeChatId;

                  return (
                    <button
                      key={chat.id}
                      type="button"
                      onClick={() => onSelectChat(chat.id)}
                      className={`w-full rounded-lg border px-3 py-3 text-left transition ${
                        isActive
                          ? "border-[#bc687c]/45 bg-[#1a1214]"
                          : "border-[#1c2420] bg-[#0d120f] hover:border-[#2a342f]"
                      }`}
                    >
                      <p className="truncate font-mono text-[13px] text-slate-100">{chat.title}</p>
                      <p className="mt-1 truncate font-mono text-[11px] text-[#809089]">
                        {chat.lastMaterialFormula ?? "Draft session"}
                      </p>
                      <p className="mt-1 truncate font-mono text-[11px] text-[#6d7a75]">
                        {chat.lastVerdict ?? "Ready for analysis"}
                      </p>
                    </button>
                  );
                })
              ) : (
                <div className="rounded-lg border border-dashed border-[#1c2420] bg-[#0d120f] px-3 py-4 font-mono text-sm text-[#778680]">
                  No screening history yet. Start with a material in the main workspace.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
