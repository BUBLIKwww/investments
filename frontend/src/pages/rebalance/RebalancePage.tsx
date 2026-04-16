import { useQuery, useQueryClient } from "@tanstack/react-query";

import { getRebalance } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { GlassSurface } from "@/shared/ui/GlassSurface";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatPercent, formatRub, parseDecimal } from "@/shared/lib/format";

import styles from "./RebalancePage.module.css";

export function RebalancePage() {
  const qc = useQueryClient();
  const { data, isPending, isError, error } = useQuery({
    queryKey: queryKeys.rebalance,
    queryFn: getRebalance,
  });

  const retry = () => {
    void qc.invalidateQueries({ queryKey: queryKeys.rebalance });
  };

  if (isPending) {
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов" />
        <LoadingBlock label="Загружаем ребаланс…" />
      </div>
    );
  }

  if (isError) {
    const err = getUserFacingApiError(error);
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов" />
        <ErrorBlock title={err.title} message={err.message} onRetry={retry} />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов" />
        <ErrorBlock message="Нет данных" onRetry={retry} />
      </div>
    );
  }

  const nameById = new Map(data.categories.map((c) => [c.category_id, c.category_name] as const));

  return (
    <div>
      <PageHeader title="Ребаланс" subtitle="Текущие и целевые доли по mock‑ценам" />

      <SectionHeader title="Сводка" subtitle="Категории ниже цели / выше цели" />

      <div className={styles.chips}>
        <span className={styles.chip}>
          Ниже цели:{" "}
          {data.underweight.length
            ? data.underweight.map((id) => nameById.get(id) ?? id).join(", ")
            : "—"}
        </span>
        <span className={[styles.chip, styles.chipMuted].join(" ")}>
          Выше цели:{" "}
          {data.overweight.length ? data.overweight.map((id) => nameById.get(id) ?? id).join(", ") : "—"}
        </span>
      </div>

      <SectionHeader title="Категории" subtitle="Текущая доля, цель и отклонение" />
      <div className={styles.list}>
        {data.categories.map((c) => {
          const d = parseDecimal(c.delta_percent);
          const cls = Number.isFinite(d) ? (d > 0 ? styles.deltaPos : d < 0 ? styles.deltaNeg : "") : "";
          return (
            <GlassSurface key={c.category_id} variant="strong" className={styles.card}>
              <div className={styles.head}>
                <div>
                  <p className={styles.name}>{c.category_name}</p>
                  <p className={styles.sub}>Тикер: {c.fund_ticker}</p>
                </div>
                <span className={styles.ticker}>{c.fund_ticker}</span>
              </div>
              <div className={styles.grid}>
                <div>
                  <p className={styles.k}>Текущая доля</p>
                  <p className={styles.v}>{formatPercent(c.current_weight_percent)}</p>
                </div>
                <div>
                  <p className={styles.k}>Целевая доля</p>
                  <p className={styles.v}>{formatPercent(c.target_weight_percent)}</p>
                </div>
                <div>
                  <p className={styles.k}>Дельта</p>
                  <p className={`${styles.v} ${cls}`}>{formatPercent(c.delta_percent)}</p>
                </div>
                <div>
                  <p className={styles.k}>Оценка</p>
                  <p className={styles.v}>{formatRub(c.current_amount)}</p>
                </div>
              </div>
            </GlassSurface>
          );
        })}
      </div>
    </div>
  );
}
