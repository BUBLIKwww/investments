import { apiRequest } from "@/shared/api/client";
import type {
  FundRead,
  FundsPricesRefreshResponse,
  InvestmentTransactionRead,
  InvestmentTransactionWritePayload,
  PortfolioRead,
  RebalanceRead,
  StrategyRead,
  StrategyUpdateRequest,
  TopupCalculateRequest,
  TopupCalculateResponse,
  TopupHistoryRead,
} from "@/shared/api/types";

function normalizePortfolioRead(raw: unknown): PortfolioRead {
  if (!raw || typeof raw !== "object") {
    return {
      total_invested_amount: "0",
      total_current_amount: "0",
      categories: [],
      positions: [],
    };
  }
  const o = raw as Record<string, unknown>;
  const cats = o.categories;
  const pos = o.positions;
  return {
    total_invested_amount: typeof o.total_invested_amount === "string" ? o.total_invested_amount : String(o.total_invested_amount ?? "0"),
    total_current_amount: typeof o.total_current_amount === "string" ? o.total_current_amount : String(o.total_current_amount ?? "0"),
    categories: Array.isArray(cats) ? (cats as PortfolioRead["categories"]) : [],
    positions: Array.isArray(pos) ? (pos as PortfolioRead["positions"]) : [],
  };
}

export async function getPortfolio(): Promise<PortfolioRead> {
  const raw = await apiRequest<unknown>("/api/v1/portfolio");
  return normalizePortfolioRead(raw);
}

export async function calculateTopup(payload: TopupCalculateRequest): Promise<TopupCalculateResponse> {
  return apiRequest<TopupCalculateResponse>("/api/v1/topups/calculate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createTopup(payload: TopupCalculateRequest): Promise<TopupCalculateResponse> {
  return apiRequest<TopupCalculateResponse>("/api/v1/topups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTopupHistory(): Promise<TopupHistoryRead[]> {
  return apiRequest<TopupHistoryRead[]>("/api/v1/topups/history");
}

export async function getRebalance(): Promise<RebalanceRead> {
  return apiRequest<RebalanceRead>("/api/v1/rebalance");
}

export async function getStrategy(): Promise<StrategyRead> {
  return apiRequest<StrategyRead>("/api/v1/strategy");
}

export async function updateStrategy(payload: StrategyUpdateRequest): Promise<StrategyRead> {
  return apiRequest<StrategyRead>("/api/v1/strategy", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getFunds(): Promise<FundRead[]> {
  return apiRequest<FundRead[]>("/api/v1/funds");
}

export async function refreshFundPrices(): Promise<FundsPricesRefreshResponse> {
  return apiRequest<FundsPricesRefreshResponse>("/api/v1/funds/refresh-prices", {
    method: "POST",
    body: "{}",
  });
}

export async function getFundById(fundId: number): Promise<FundRead> {
  return apiRequest<FundRead>(`/api/v1/funds/${fundId}`);
}

export async function listTransactions(): Promise<InvestmentTransactionRead[]> {
  return apiRequest<InvestmentTransactionRead[]>("/api/v1/transactions");
}

export async function getTransaction(transactionId: number): Promise<InvestmentTransactionRead> {
  return apiRequest<InvestmentTransactionRead>(`/api/v1/transactions/${transactionId}`);
}

export async function createTransaction(payload: InvestmentTransactionWritePayload): Promise<InvestmentTransactionRead> {
  return apiRequest<InvestmentTransactionRead>("/api/v1/transactions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateTransaction(
  transactionId: number,
  payload: InvestmentTransactionWritePayload,
): Promise<InvestmentTransactionRead> {
  return apiRequest<InvestmentTransactionRead>(`/api/v1/transactions/${transactionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteTransaction(transactionId: number): Promise<void> {
  return apiRequest<void>(`/api/v1/transactions/${transactionId}`, {
    method: "DELETE",
  });
}
