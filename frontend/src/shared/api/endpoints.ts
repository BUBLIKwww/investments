import { apiRequest } from "@/shared/api/client";
import { parseDecimal } from "@/shared/lib/format";
import type {
  FundAddPayload,
  FundRead,
  FundSearchHit,
  FundsPricesRefreshResponse,
  InvestmentTransactionRead,
  InvestmentTransactionWritePayload,
  PortfolioRead,
  RebalanceExecuteResult,
  RebalanceRead,
  RebalanceSmartPreview,
  StrategyRead,
  StrategyUpdateRequest,
  TopupCalculateRequest,
  TopupCalculateResponse,
  TopupHistoryRead,
} from "@/shared/api/types";

function decStr(v: unknown): string {
  if (v == null) return "0";
  if (typeof v === "string") return v;
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return String(v);
}

function normalizePortfolioPosition(p: Record<string, unknown>): PortfolioRead["positions"][number] {
  const fund = p.fund as PortfolioRead["positions"][number]["fund"];
  const invested = decStr(p.invested_amount);
  const currentAmt = decStr(p.current_amount);
  const currentPrice = p.current_price != null ? decStr(p.current_price) : decStr(fund?.price ?? "0");
  const qty = Number(p.quantity ?? p.total_units ?? 0);
  const currentVal = p.current_value != null ? decStr(p.current_value) : currentAmt;
  const investedVal = p.invested_value != null ? decStr(p.invested_value) : invested;
  const cv = parseDecimal(currentVal);
  const iv = parseDecimal(investedVal);
  const pnlRaw =
    p.pnl != null
      ? decStr(p.pnl)
      : Number.isFinite(cv) && Number.isFinite(iv)
        ? String(Number((cv - iv).toFixed(2)))
        : "0";
  const pnlPctRaw =
    p.pnl_percent != null
      ? decStr(p.pnl_percent)
      : iv > 0 && Number.isFinite(cv)
        ? String(Number((((cv - iv) / iv) * 100).toFixed(4)))
        : "0";
  return {
    id: Number(p.id),
    user_id: Number(p.user_id),
    category_id: Number(p.category_id),
    fund_id: Number(p.fund_id),
    category_name: String(p.category_name ?? ""),
    total_lots: Number(p.total_lots ?? 0),
    total_units: Number(p.total_units ?? 0),
    invested_amount: invested,
    average_buy_price: decStr(p.average_buy_price),
    current_amount: currentAmt,
    current_weight_percent: decStr(p.current_weight_percent),
    fund,
    current_price: currentPrice,
    quantity: qty,
    current_value: currentVal,
    invested_value: investedVal,
    pnl: pnlRaw,
    pnl_percent: pnlPctRaw,
    last_price_updated_at: p.last_price_updated_at == null ? null : String(p.last_price_updated_at),
  };
}

function normalizePortfolioRead(raw: unknown): PortfolioRead {
  if (!raw || typeof raw !== "object") {
    return {
      total_invested_amount: "0",
      total_current_amount: "0",
      total_pnl: "0",
      total_pnl_percent: "0",
      categories: [],
      positions: [],
    };
  }
  const o = raw as Record<string, unknown>;
  const cats = o.categories;
  const pos = o.positions;
  const positions = Array.isArray(pos) ? pos.map((x) => normalizePortfolioPosition(x as Record<string, unknown>)) : [];
  let totalPnl = decStr(o.total_pnl);
  let totalPnlPct = decStr(o.total_pnl_percent);
  if (o.total_pnl == null && positions.length) {
    const sum = positions.reduce((acc, p) => acc + (Number.isFinite(parseDecimal(p.pnl)) ? parseDecimal(p.pnl) : 0), 0);
    totalPnl = String(Number(sum.toFixed(2)));
  }
  if (o.total_pnl_percent == null) {
    const inv = parseDecimal(decStr(o.total_invested_amount));
    const pnlN = parseDecimal(totalPnl);
    totalPnlPct = inv > 0 && Number.isFinite(pnlN) ? String(Number(((pnlN / inv) * 100).toFixed(4))) : "0";
  }
  return {
    total_invested_amount: typeof o.total_invested_amount === "string" ? o.total_invested_amount : String(o.total_invested_amount ?? "0"),
    total_current_amount: typeof o.total_current_amount === "string" ? o.total_current_amount : String(o.total_current_amount ?? "0"),
    total_pnl: totalPnl,
    total_pnl_percent: totalPnlPct,
    categories: Array.isArray(cats) ? (cats as PortfolioRead["categories"]) : [],
    positions,
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

function normalizeRebalanceSmartPreview(raw: unknown): RebalanceSmartPreview {
  if (!raw || typeof raw !== "object") {
    return { cash_balance: "0", scale: "0", actions: [], total_used: "0", before_percent: "0", after_percent: "0", instruments: [] };
  }
  const o = raw as Record<string, unknown>;
  const acts = Array.isArray(o.actions) ? o.actions : [];
  const inst = Array.isArray(o.instruments) ? o.instruments : [];
  return {
    cash_balance: decStr(o.cash_balance),
    scale: decStr(o.scale),
    total_used: decStr(o.total_used),
    before_percent: decStr(o.before_percent),
    after_percent: decStr(o.after_percent),
    actions: acts.map((a) => {
      const r = a as Record<string, unknown>;
      return {
        fund_id: Number(r.fund_id),
        ticker: String(r.ticker ?? ""),
        action: r.action === "sell" ? "sell" : "buy",
        amount: decStr(r.amount),
      };
    }),
    instruments: inst.map((row) => {
      const r = row as Record<string, unknown>;
      return {
        ticker: String(r.ticker ?? ""),
        fund_id: Number(r.fund_id),
        current_percent: decStr(r.current_percent),
        target_percent: decStr(r.target_percent),
        after_percent: decStr(r.after_percent),
      };
    }),
  };
}

export async function postRebalancePreview(payload: { amount: number | null }): Promise<RebalanceSmartPreview> {
  const raw = await apiRequest<unknown>("/api/v1/portfolio/rebalance/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return normalizeRebalanceSmartPreview(raw);
}

export async function postRebalanceExecute(payload: { amount: number | null }): Promise<RebalanceExecuteResult> {
  return apiRequest<RebalanceExecuteResult>("/api/v1/portfolio/rebalance/execute", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

export async function searchFunds(query: string, limit = 15): Promise<FundSearchHit[]> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return apiRequest<FundSearchHit[]>(`/api/v1/funds/search?${params.toString()}`);
}

export async function addFund(payload: FundAddPayload): Promise<FundRead> {
  return apiRequest<FundRead>("/api/v1/funds/add", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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
