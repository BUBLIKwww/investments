import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/shared/api/client";
import { getFundById } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import { formatDateTime, formatRub } from "@/shared/lib/format";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";

import styles from "./FundDetailsPage.module.css";

export function FundDetailsPage() {
  const { fundId } = useParams();
  const qc = useQueryClient();

  const numericId = useMemo(() => {
    if (!fundId) return Number.NaN;
    const n = Number(fundId);
    return Number.isInteger(n) && n > 0 ? n : Number.NaN;
  }, [fundId]);

  const { data, isPending, isError, error } = useQuery({
    queryKey: queryKeys.fundDetail(numericId),
    queryFn: () => getFundById(numericId),
    enabled: Number.isFinite(numericId),
  });

  const retry = () => {
    void qc.invalidateQueries({ queryKey: queryKeys.fundDetail(numericId) });
  };

  if (!Number.isFinite(numericId)) {
    return (
      <div>
        <PageHeader title="Фонд" subtitle="Карточка инструмента" />
        <ErrorBlock title="Некорректная ссылка" message="Укажите корректный числовой идентификатор фонда." />
      </div>
    );
  }

  if (isPending) {
    return (
      <div>
        <PageHeader title="Фонд" subtitle="Загрузка…" />
        <LoadingBlock label="Загрузка карточки фонда…" />
      </div>
    );
  }

  if (isError) {
    const err = error;
    const is404 = err instanceof ApiError && err.status === 404;
    return (
      <div>
        <PageHeader title="Фонд" subtitle="Карточка инструмента" />
        <ErrorBlock
          title={is404 ? "Фонд не найден" : "Не удалось загрузить"}
          message={is404 ? "Проверьте ссылку или выберите фонд из списка." : err instanceof Error ? err.message : "Ошибка"}
          onRetry={is404 ? undefined : retry}
        />
      </div>
    );
  }

  const f = data;
  if (!f) {
    return (
      <div>
        <PageHeader title="Фонд" subtitle="Карточка инструмента" />
        <ErrorBlock message="Нет данных" onRetry={retry} />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={f.name} subtitle={`Тикер ${f.ticker}`} />

      <div className={styles.hero}>
        <div className={styles.heroTop}>
          <div>
            <p className={styles.priceLabel}>Текущая цена</p>
            <p className={styles.priceValue}>{formatRub(f.price)}</p>
            <p className={styles.currency}>{f.currency}</p>
          </div>
          <span className={[styles.status, f.is_active ? styles.statusOn : styles.statusOff].join(" ")}>
            {f.is_active ? "Активен" : "Неактивен"}
          </span>
        </div>
        <p className={styles.updated}>Обновление цены: {formatDateTime(f.last_price_updated_at)}</p>
      </div>

      <div className={styles.grid}>
        <div className={styles.kpi}>
          <p className={styles.kpiLabel}>Тикер</p>
          <p className={styles.kpiValue}>{f.ticker}</p>
        </div>
        <div className={styles.kpi}>
          <p className={styles.kpiLabel}>Лот</p>
          <p className={styles.kpiValue}>{f.lot}</p>
        </div>
        <div className={styles.kpi}>
          <p className={styles.kpiLabel}>Валюта</p>
          <p className={styles.kpiValue}>{f.currency}</p>
        </div>
        <div className={styles.kpi}>
          <p className={styles.kpiLabel}>FIGI / UID</p>
          <p className={styles.kpiValueMono}>{f.figi_or_uid}</p>
        </div>
      </div>
    </div>
  );
}
