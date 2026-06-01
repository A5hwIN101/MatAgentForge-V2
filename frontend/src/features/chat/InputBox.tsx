"use client";

import { type FormEvent, useState } from "react";

const DEFAULT_WORKSPACE_EXAMPLES = ["LiCoO2", "LiFePO4", "Li(Ni,Mn,Co)O2"];

type InputBoxProps = {
  chatId: string | null;
  disabled?: boolean;
  onSubmit: (chatId: string | null, formula: string) => void | Promise<void>;
  variant?: "compact" | "workspace";
  examples?: string[];
};

export function InputBox({
  chatId,
  disabled = false,
  onSubmit,
  variant = "compact",
  examples = [],
}: InputBoxProps) {
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isDisabled = disabled || isSubmitting;
  const workspaceExamples = examples.length > 0 ? examples : DEFAULT_WORKSPACE_EXAMPLES;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formula = value.trim();
    if (!formula || isDisabled) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(chatId, formula);
      setValue("");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (variant === "workspace") {
    return (
      <div className="w-full max-w-4xl">
        <form
          onSubmit={handleSubmit}
          className="rounded-[1.35rem] border border-[#1c2420] bg-[#080d0b]/96 p-3.5 shadow-xl shadow-black/20"
        >
          <div className="rounded-[1.1rem] border border-[#1c2420] bg-[#0d120f] px-4 py-3.5">
            <textarea
              value={value}
              onChange={(event) => setValue(event.target.value)}
              disabled={isDisabled}
              placeholder="Enter a material formula to screen, e.g. LiCoO2"
              rows={4}
              className="w-full resize-none bg-transparent font-mono text-base leading-8 text-slate-100 outline-none placeholder:text-[#64726d] disabled:cursor-not-allowed disabled:opacity-60"
            />
            <div className="mt-4 flex flex-wrap items-end justify-between gap-3.5">
              <div className="flex flex-wrap gap-3">
                {workspaceExamples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    disabled={isDisabled}
                    onClick={() => setValue(example)}
                    className="min-h-11 rounded-xl border border-[#26332d] bg-[#111714]/92 px-4 py-2.5 text-left font-mono text-[13px] text-[#9aa9a2] shadow-[0_10px_24px_rgba(0,0,0,0.12)] transition duration-150 hover:-translate-y-px hover:border-[#446159] hover:bg-[#151d19] hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {example}
                  </button>
                ))}
              </div>
              <button
                type="submit"
                disabled={isDisabled}
                className="rounded-md border border-[#34544e] bg-[#16211d] px-5 py-2.5 font-mono text-sm text-[#d7e6df] transition hover:border-[#bc687c] hover:bg-[#241518] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isDisabled ? "Analyzing..." : "Start analysis"}
              </button>
            </div>
          </div>
        </form>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-3 rounded-xl border border-[#1c2420] bg-[#0a0f0c]/96 p-3 shadow-lg shadow-black/15 lg:flex-row lg:items-center"
    >
      <div className="flex-1">
        <p className="mb-2 font-mono text-[12px] text-[#7c8d86]">Material input</p>
        <input
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          disabled={isDisabled}
          placeholder="Screen a material formula, e.g. LiFePO4"
          className="h-11 w-full rounded-md border border-[#1c2420] bg-[#0e1411] px-4 font-mono text-sm text-slate-100 outline-none transition placeholder:text-[#66746f] focus:border-[#4d6c63] disabled:cursor-not-allowed disabled:opacity-60"
        />
      </div>
      <button
        type="submit"
        disabled={isDisabled}
        className="h-11 rounded-md border border-[#34544e] bg-[#16211d] px-5 font-mono text-sm text-[#d7e6df] transition hover:border-[#bc687c] hover:bg-[#241518] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isDisabled ? "Analyzing..." : "Analyze"}
      </button>
    </form>
  );
}
