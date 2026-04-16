import { API_BASE_URL } from "@/shared/api/config";

export class ApiError extends Error {
  readonly status: number;
  readonly body?: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function joinUrl(base: string, path: string) {
  if (path.startsWith("http")) return path;

  if (base.startsWith("http")) {
    return `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  }

  if (path.startsWith("/api/")) {
    return path;
  }

  const b = base.replace(/\/$/, "");
  const p = path.replace(/^\//, "");
  if (!b) return `/${p}`;
  return `${b}/${p}`;
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const url = joinUrl(API_BASE_URL, path);
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(url, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "Не удалось подключиться к серверу. Проверьте сеть, VPN или что backend запущен.",
      undefined,
    );
  }

  if (!res.ok) {
    let message = res.statusText || "Request failed";
    let body: unknown;
    try {
      body = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail?: unknown }).detail;
        message = typeof d === "string" ? d : JSON.stringify(d);
      }
    } catch {
      try {
        message = await res.text();
      } catch {
        // ignore
      }
    }
    throw new ApiError(res.status, message, body);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}
