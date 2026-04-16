import type { QueryClient } from "@tanstack/react-query";

import { queryKeys, TOPUP_CALCULATION_STORAGE_KEY } from "@/shared/api/query-keys";
import type { TopupCalculateResponse } from "@/shared/api/types";

export function persistTopupCalculation(qc: QueryClient, data: TopupCalculateResponse) {
  qc.setQueryData(queryKeys.topupCalculation, data);
  try {
    sessionStorage.setItem(TOPUP_CALCULATION_STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

export function readTopupCalculationFromStorage(): TopupCalculateResponse | null {
  try {
    const raw = sessionStorage.getItem(TOPUP_CALCULATION_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as TopupCalculateResponse;
  } catch {
    return null;
  }
}

export function clearTopupCalculation(qc: QueryClient) {
  qc.removeQueries({ queryKey: queryKeys.topupCalculation });
  try {
    sessionStorage.removeItem(TOPUP_CALCULATION_STORAGE_KEY);
  } catch {
    // ignore
  }
}
