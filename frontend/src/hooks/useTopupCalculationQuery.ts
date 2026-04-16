import { useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/shared/api/query-keys";
import { readTopupCalculationFromStorage } from "@/shared/api/topup-calculation-cache";
import type { TopupCalculateResponse } from "@/shared/api/types";

export function useTopupCalculationQuery() {
  const qc = useQueryClient();

  return useQuery({
    queryKey: queryKeys.topupCalculation,
    queryFn: async () => {
      const cached = qc.getQueryData<TopupCalculateResponse>(queryKeys.topupCalculation);
      if (cached) return cached;

      const stored = readTopupCalculationFromStorage();
      if (!stored) throw new Error("NO_CALCULATION");

      qc.setQueryData(queryKeys.topupCalculation, stored);
      return stored;
    },
    staleTime: Infinity,
    retry: false,
  });
}
