/**
 * Базовый URL бэкенда (схема + хост, без пути к эндпоинтам).
 * В Vite переменные VITE_* подставляются на этапе сборки — на Railway задайте VITE_API_BASE_URL в Build Variables.
 */
const PRODUCTION_FALLBACK_API = "https://investments-production-000e.up.railway.app";

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;
const trimmed = typeof fromEnv === "string" ? fromEnv.trim() : "";

export const API_BASE_URL = trimmed
  ? stripTrailingSlash(trimmed)
  : import.meta.env.DEV
    ? "/api"
    : stripTrailingSlash(PRODUCTION_FALLBACK_API);
