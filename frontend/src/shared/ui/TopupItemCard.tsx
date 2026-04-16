import type { TopupItemResult } from "@/shared/api/types";
import { formatPercent, formatRub } from "@/shared/lib/format";

import styles from "./TopupItemCard.module.css";

type TopupItemCardProps = {
  item: TopupItemResult;
};

export function TopupItemCard({ item }: TopupItemCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <div>
          <p className={styles.title}>{item.category_name}</p>
          <p className={styles.sub}>{item.fund_name}</p>
          <p className={styles.unitsLead}>
            К покупке: <strong>{item.purchased_units}</strong> акций (лотов: {item.purchased_lots}, в лоте{" "}
            {item.lot_size} шт.)
          </p>
        </div>
        <span className={styles.ticker}>{item.ticker}</span>
      </div>
      <div className={styles.grid}>
        <div>
          <p className={styles.k}>Целевая доля</p>
          <p className={styles.v}>{formatPercent(item.target_percent)}</p>
        </div>
        <div>
          <p className={styles.k}>Целевая сумма</p>
          <p className={styles.v}>{formatRub(item.target_amount)}</p>
        </div>
        <div>
          <p className={styles.k}>Цена (за 1)</p>
          <p className={styles.v}>{formatRub(item.price_used)}</p>
        </div>
        <div>
          <p className={styles.k}>Размер лота</p>
          <p className={styles.v}>{item.lot_size}</p>
        </div>
        <div>
          <p className={styles.k}>Лотов</p>
          <p className={styles.v}>{item.purchased_lots}</p>
        </div>
        <div>
          <p className={styles.k}>Акций</p>
          <p className={styles.v}>{item.purchased_units}</p>
        </div>
        <div>
          <p className={styles.k}>Фактически</p>
          <p className={styles.v}>{formatRub(item.actual_allocated_amount)}</p>
        </div>
        <div>
          <p className={styles.k}>Остаток по категории</p>
          <p className={styles.v}>{formatRub(item.cash_remainder)}</p>
        </div>
      </div>
    </div>
  );
}
