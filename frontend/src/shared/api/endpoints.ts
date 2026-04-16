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

export async function getPortfolio(): Promise<PortfolioRead> {
  return apiRequest<PortfolioRead>("/api/v1/portfolio");
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
