"use client";

export interface ApiConfig {
  baseUrl: string;
  apiKey: string;
}

const STORAGE_KEY = "okf-api-config";

export const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: "http://localhost:8000",
  apiKey: "",
};

export function loadConfig(): ApiConfig {
  if (typeof window === "undefined") return DEFAULT_CONFIG;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_CONFIG;
    const parsed = JSON.parse(raw) as Partial<ApiConfig>;
    return { ...DEFAULT_CONFIG, ...parsed };
  } catch {
    return DEFAULT_CONFIG;
  }
}

export function saveConfig(config: ApiConfig): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}
