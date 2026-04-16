/**
 * Базовый URL бэкенда (схема + хост, без пути к эндпоинтам).
 * В Vite переменные VITE_* подставляются на этапе сборки — на Railway задайте VITE_API_BASE_URL в Build Variables.
 *
 * Важно: в production нельзя оставлять VITE_API_BASE_URL=/api — на статическом хосте нет Vite proxy,
 * запросы уйдут на тот же origin и fetch упадёт («Нет соединения»). В таком случае ниже подставляется полный URL бэкенда.
 */
const PRODUCTION_FALLBACK_API = "https://investments-production-000e.up.railway.app";

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;
const trimmed = typeof fromEnv === "string" ? fromEnv.trim() : "";

function resolveBase(): string {
  let base = trimmed
    ? stripTrailingSlash(trimmed)
    : import.meta.env.DEV
      ? "/api"
      : stripTrailingSlash(PRODUCTION_FALLBACK_API);

  if (import.meta.env.PROD && (base === "" || base.startsWith("/"))) {
    return stripTrailingSlash(PRODUCTION_FALLBACK_API);
  }
  return base;
}

export const API_BASE_URL = resolveBase();
