export type TopupMode = "strict" | "maximize" | "smart";

export type FundRead = {
  id: number;
  name: string;
  ticker: string;
  figi_or_uid: string;
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
};

export type PortfolioRead = {
  total_invested_amount: string;
  total_current_amount: string;
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
  id: number;
  name: string;
  target_percent: string;
  fund_id: number;
  sort_order: number;
  is_active: boolean;
};

export type StrategyUpdateRequest = {
  categories: StrategyCategoryUpdatePayload[];
};
