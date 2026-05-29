export function ChatInterfacePlaceholder() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen max-w-7xl gap-6 px-6 py-8">
        <aside className="flex w-80 flex-col rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                MatAgent-Critique
              </p>
              <h1 className="mt-2 text-xl font-semibold text-white">
                Chat History
              </h1>
            </div>
            <button className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-200">
              Load
            </button>
          </div>

          <div className="mt-4 rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-400">
            No chats loaded yet. Click <span className="text-slate-200">Load</span>{" "}
            to fetch history from the backend.
          </div>
        </aside>

        <section className="flex flex-1 flex-col rounded-3xl border border-slate-800 bg-slate-900/70 p-8">
          <div className="border-b border-slate-800 pb-6">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-400">
              Chunk 1 Placeholder
            </p>
            <h2 className="mt-3 text-3xl font-semibold text-white">
              Chat Interface
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Frontend skeleton is live. Next chunks will replace this placeholder
              with the streaming chat timeline, critique card, and feedback
              actions defined in the spec.
            </p>
          </div>

          <div className="mt-8 grid gap-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-sm text-slate-500">User Input</p>
              <p className="mt-2 text-base text-slate-200">LiCoO2</p>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-sm text-slate-500">Streaming Steps</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-200">
                <li>⚙ Loading domain rules...</li>
                <li>🔍 Screening LiCoO₂...</li>
                <li>⚠ Running critique...</li>
                <li>✅ Done</li>
              </ul>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
