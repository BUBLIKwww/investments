export const queryKeys = {
  portfolio: ["portfolio"] as const,
  topupHistory: ["topupHistory"] as const,
  rebalance: ["rebalance"] as const,
  strategy: ["strategy"] as const,
  funds: ["funds"] as const,
  fundDetail: (fundId: number) => ["funds", "detail", fundId] as const,
  topupCalculation: ["topup", "calculation"] as const,
} as const;

export const TOPUP_CALCULATION_STORAGE_KEY = "invest_miniapp_topup_calc_v1";
