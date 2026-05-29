"use client";

import { CritiqueCard } from "@/components/CritiqueCard";
import type { ChatItem, CritiqueCard as CritiqueCardType } from "@/types";

type MessageListProps = {
  messages: ChatItem[];
  onFeedback: (action: "approve" | "reject" | "modify", reason?: string) => void;
};

export function MessageList({ messages, onFeedback }: MessageListProps) {
  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
      {messages.length > 0 ? (
        messages.map((message) => {
          if (message.itemType === "critique_card" && message.contentJson) {
            return (
              <div key={message.id} className="flex justify-start">
                <CritiqueCard
                  critique={message.contentJson as CritiqueCardType}
                  onFeedback={onFeedback}
                />
              </div>
            );
          }

          if (message.itemType === "user_message") {
            return (
              <div key={message.id} className="flex justify-end">
                <div className="max-w-2xl rounded-[1.5rem] bg-emerald-400 px-5 py-4 text-sm font-medium text-slate-950 shadow-lg shadow-emerald-900/10">
                  {message.contentText}
                </div>
              </div>
            );
          }

          if (message.itemType === "agent_status" || message.itemType === "status_stream") {
            return (
              <div key={message.id} className="flex justify-start">
                <div className="max-w-2xl rounded-[1.25rem] border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-300">
                  {message.contentText}
                </div>
              </div>
            );
          }

          return (
            <div key={message.id} className="flex justify-start">
              <div className="max-w-3xl rounded-[1.5rem] border border-slate-800 bg-slate-900/80 px-5 py-4 text-sm leading-6 text-slate-200">
                {message.contentText}
              </div>
            </div>
          );
        })
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-[2rem] border border-dashed border-slate-800 bg-slate-950/40 p-10 text-center text-sm leading-6 text-slate-500">
          Choose a chat or start a new one to screen a material candidate.
        </div>
      )}
    </div>
  );
}
