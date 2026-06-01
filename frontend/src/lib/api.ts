"use client";

function normalizeApiUrl(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.replace(/\/+$/, "") : null;
}

export const API_BASE_URL =
  normalizeApiUrl(process.env.NEXT_PUBLIC_API_URL) ?? "http://localhost:8000";
