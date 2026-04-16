import type { TopupMode } from "@/shared/api/types";

const rubFormatter = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function parseDecimal(value: string): number {
  const cleaned = value.replace(/\s+/g, "").replace(",", ".");
  if (!cleaned) return Number.NaN;
  return Number(cleaned);
}

export function formatRub(amount: string | number): string {
  const n = typeof amount === "string" ? parseDecimal(amount) : amount;
  if (!Number.isFinite(n)) return "—";
  return rubFormatter.format(n);
}

export function formatPercent(value: string | number, fractionDigits = 1): string {
  const n = typeof value === "string" ? parseDecimal(value) : value;
  if (!Number.isFinite(n)) return "—";
  return `${n.toFixed(fractionDigits).replace(".", ",")}%`;
}

export function formatSignedPercent(value: string | number, fractionDigits = 1): string {
  const n = typeof value === "string" ? parseDecimal(value) : value;
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(fractionDigits).replace(".", ",")} п.п.`;
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(d);
}

export function formatTopupMode(mode: TopupMode): string {
  if (mode === "strict") return "Строго";
  if (mode === "maximize") return "Максимум";
  if (mode === "smart") return "Умный";
  return mode;
}

export function normalizeAmountForApi(raw: string): string | null {
  const cleaned = raw.replace(/\s+/g, "").replace(",", ".");
  if (!cleaned) return null;
  const n = Number(cleaned);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n.toFixed(2);
}
