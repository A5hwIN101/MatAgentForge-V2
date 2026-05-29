"use client";

import type { Chat } from "@/types";

type SidebarProps = {
  chats: Chat[];
  activeChatId: string | null;
  isLoading: boolean;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void | Promise<void>;
};

export function Sidebar({
  chats,
  activeChatId,
  isLoading,
  onSelectChat,
  onNewChat,
}: SidebarProps) {
  return (
    <aside className="flex min-h-[320px] flex-col rounded-[2rem] border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/30">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.34em] text-slate-500">History</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Chats</h2>
        </div>
        <button
          type="button"
          onClick={() => void onNewChat()}
          className="rounded-full border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-emerald-400 hover:text-white"
        >
          New Chat
        </button>
      </div>

      <div className="mt-5 flex-1 space-y-3 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="rounded-2xl border border-dashed border-slate-700 px-4 py-5 text-sm text-slate-500">
            Loading chats...
          </div>
        ) : chats.length > 0 ? (
          chats.map((chat) => {
            const isActive = chat.id === activeChatId;

            return (
              <button
                key={chat.id}
                type="button"
                onClick={() => onSelectChat(chat.id)}
                className={`w-full rounded-2xl border px-4 py-4 text-left transition ${
                  isActive
                    ? "border-emerald-400/70 bg-emerald-500/10"
                    : "border-slate-800 bg-slate-950/50 hover:border-slate-700"
                }`}
              >
                <p className="text-sm font-semibold text-white">{chat.title}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                  {chat.lastMaterialFormula ?? "No material yet"}
                </p>
                <p className="mt-2 text-sm text-slate-400">
                  {chat.lastVerdict ?? "Open chat and screen a new candidate"}
                </p>
              </button>
            );
          })
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-700 px-4 py-5 text-sm text-slate-500">
            No chats available.
          </div>
        )}
      </div>
    </aside>
  );
}
