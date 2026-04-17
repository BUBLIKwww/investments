export const queryKeys = {
  portfolio: (source: "simulation" | "live" = "live") => ["portfolio", source] as const,
  transactions: ["transactions"] as const,
  topupHistory: ["topupHistory"] as const,
  rebalance: (source: "simulation" | "live" = "live") => ["rebalance", source] as const,
  strategy: ["strategy"] as const,
  funds: ["funds"] as const,
  fundsSearch: (q: string) => ["funds", "search", q] as const,
  fundDetail: (fundId: number) => ["funds", "detail", fundId] as const,
  topupCalculation: ["topup", "calculation"] as const,
} as const;

export const TOPUP_CALCULATION_STORAGE_KEY = "invest_miniapp_topup_calc_v1";
