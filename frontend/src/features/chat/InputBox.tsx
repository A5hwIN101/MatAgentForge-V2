"use client";

import { type FormEvent, useState } from "react";

type InputBoxProps = {
  disabled?: boolean;
  onSubmit: (formula: string) => void | Promise<void>;
};

export function InputBox({ disabled = false, onSubmit }: InputBoxProps) {
  const [value, setValue] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formula = value.trim();
    if (!formula || disabled) {
      return;
    }

    await onSubmit(formula);
    setValue("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-3 rounded-[1.75rem] border border-slate-800 bg-slate-900/85 p-4 shadow-xl shadow-slate-950/30 sm:flex-row sm:items-center"
    >
      <input
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        disabled={disabled}
        placeholder="Enter material formula, e.g. LiCoO2"
        className="h-12 flex-1 rounded-full border border-slate-700 bg-slate-950/80 px-5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled}
        className="h-12 rounded-full bg-emerald-400 px-6 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {disabled ? "Screening..." : "Analyze"}
      </button>
    </form>
  );
}
