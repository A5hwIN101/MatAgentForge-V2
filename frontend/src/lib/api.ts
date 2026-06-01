"use client";

const DEV_API_URL = "http://localhost:8000";
const PROD_API_URL = "https://matagentforge-v2-production.up.railway.app";

function normalizeApiUrl(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.replace(/\/+$/, "") : null;
}

export const API_BASE_URL =
  normalizeApiUrl(process.env.NEXT_PUBLIC_API_URL) ??
  (process.env.NODE_ENV === "development" ? DEV_API_URL : PROD_API_URL);
