export type TopupMode = "strict" | "maximize" | "smart";

export type FundRead = {
  id: number;
  name: string;
  ticker: string;
  figi_or_uid: string;
  instrument_uid?: string | null;
  figi?: string | null;
  lot: number;
  price: string;
  currency: string;
  last_price_updated_at: string;
  is_active: boolean;
};

export type FundsPricesRefreshResponse = {
  updated: number;
  funds: FundRead[];
};

export type FundSearchHit = {
  name: string;
  ticker: string;
  instrument_uid: string;
  figi: string | null;
  lot: number;
  currency: string;
  last_price: string | null;
};

export type FundAddPayload = {
  instrument_uid: string;
  ticker: string;
  name: string;
  figi: string | null;
  lot: number;
  currency: string;
};

export type CategorySummary = {
  category_id: number;
  category_name: string;
  target_percent: string;
  current_weight_percent: string;
  current_amount: string;
  invested_amount: string;
};

export type PortfolioPositionRead = {
  id: number;
  user_id: number;
  category_id: number;
  fund_id: number;
  category_name: string;
  total_lots: number;
  total_units: number;
  invested_amount: string;
  average_buy_price: string;
  current_amount: string;
  current_weight_percent: string;
  fund: FundRead;
  current_price: string;
  quantity: number;
  current_value: string;
  invested_value: string;
  pnl: string;
  pnl_percent: string;
  last_price_updated_at?: string | null;
};

export type PortfolioRead = {
  source?: "simulation" | "live";
  total_invested_amount: string;
  total_current_amount: string;
  total_pnl: string;
  total_pnl_percent: string;
  categories: CategorySummary[];
  positions: PortfolioPositionRead[];
};

export type TopupItemResult = {
  category_id: number;
  category_name: string;
  fund_id: number;
  fund_name: string;
  ticker: string;
  target_percent: string;
  target_amount: string;
  price_used: string;
  lot_size: number;
  purchased_lots: number;
  purchased_units: number;
  actual_allocated_amount: string;
  cash_remainder: string;
};

export type TopupCalculateResponse = {
  total_amount: string;
  mode: TopupMode;
  items: TopupItemResult[];
  total_allocated_amount: string;
  total_cash_remainder: string;
};

export type TopupCalculateRequest = {
  total_amount: string;
  mode: TopupMode;
};

export type TopupHistoryItemRead = {
  id: number;
  category_id: number;
  fund_id: number;
  target_amount: string;
  actual_allocated_amount: string;
  cash_remainder: string;
  price_used: string;
  lot_size: number;
  purchased_lots: number;
  purchased_units: number;
};

export type TopupHistoryRead = {
  id: number;
  user_id: number;
  total_amount: string;
  mode: TopupMode;
  total_allocated_amount: string;
  total_cash_remainder: string;
  created_at: string;
  items: TopupHistoryItemRead[];
};

export type RebalanceCategoryRead = {
  category_id: number;
  category_name: string;
  fund_ticker: string;
  target_weight_percent: string;
  current_weight_percent: string;
  delta_percent: string;
  current_amount: string;
};

export type RebalanceRead = {
  categories: RebalanceCategoryRead[];
  underweight: number[];
  overweight: number[];
};

export type RebalanceSmartAction = {
  fund_id: number;
  ticker: string;
  action: "buy" | "sell";
  amount: string;
  quantity: number;
  lots: number;
  instrument_id: string;
};

export type RebalanceSmartInstrument = {
  ticker: string;
  fund_id: number;
  current_percent: string;
  target_percent: string;
  after_percent: string;
};

export type RebalanceSmartPreview = {
  cash_balance: string;
  scale: string;
  actions: RebalanceSmartAction[];
  total_used: string;
  before_percent: string;
  after_percent: string;
  instruments: RebalanceSmartInstrument[];
  mode: "simulation" | "live";
  plan_fingerprint: string;
  account_id: string | null;
};

export type RebalanceExecuteResult = {
  created_transaction_ids: number[];
};

export type RebalanceLiveOrderResult = {
  ticker: string;
  action: "buy" | "sell";
  instrument_id: string;
  lots: number;
  success: boolean;
  order_id: string | null;
  execution_status: string | null;
  message: string | null;
};

export type RebalanceLiveExecuteResult = {
  orders: RebalanceLiveOrderResult[];
  dry_run: boolean;
};

export type BrokerAccountRead = {
  id: string;
  name: string;
  type: string;
  status: string;
  access_level: string;
};

export type BrokerSettingsRead = {
  selected_account_id: string | null;
  default_account_id_env: string | null;
};

export type StrategyCategoryRead = {
  id: number;
  user_id: number;
  fund_id: number;
  name: string;
  target_percent: string;
  sort_order: number;
  is_active: boolean;
  fund: FundRead;
};

export type StrategyRead = {
  categories: StrategyCategoryRead[];
};

export type StrategyCategoryUpdatePayload = {
  id: number | null;
  name: string;
  target_percent: string;
  fund_id: number;
  sort_order: number;
  is_active: boolean;
};

export type StrategyUpdateRequest = {
  categories: StrategyCategoryUpdatePayload[];
};

export type TransactionOperationType = "buy" | "sell";

export type InvestmentTransactionRead = {
  id: number;
  user_id: number;
  category_id: number;
  fund_id: number;
  operation_type: TransactionOperationType;
  quantity: number;
  price_per_unit: string;
  total_amount: string;
  executed_at: string;
  note: string | null;
  created_at: string;
  updated_at: string;
};

/** Тело POST/PUT сделки (Decimal на backend сериализуются строкой). */
export type InvestmentTransactionWritePayload = {
  fund_id: number;
  category_id?: number | null;
  operation_type: TransactionOperationType;
  quantity: number;
  price_per_unit: string;
  total_amount: string;
  executed_at: string;
  note?: string | null;
};
