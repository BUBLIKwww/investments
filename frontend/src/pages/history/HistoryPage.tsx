import { useQuery } from "@tanstack/react-query";

import { getTopupHistory } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatDateTime, formatRub, formatTopupMode } from "@/shared/lib/format";

import styles from "./HistoryPage.module.css";

export function HistoryPage() {
  const q = useQuery({
    queryKey: queryKeys.topupHistory,
    queryFn: getTopupHistory,
  });

  if (q.isPending) {
    return (
      <div>
        <PageHeader title="История" subtitle="Сохранённые пополнения" />
        <LoadingBlock label="Загружаем историю…" />
      </div>
    );
  }

  if (q.isError) {
    const err = getUserFacingApiError(q.error);
    return (
      <div>
        <PageHeader title="История" subtitle="Сохранённые пополнения" />
        <ErrorBlock title={err.title} message={err.message} onRetry={() => void q.refetch()} />
      </div>
    );
  }

  const rows = q.data ?? [];

  if (rows.length === 0) {
    return (
      <div>
        <PageHeader title="История" subtitle="Сохранённые пополнения" />
        <EmptyState
          title="Пока нет пополнений"
          description="После сохранения пополнения оно появится в этом списке."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="История" subtitle="Сохранённые пополнения" />
      <div className={styles.list}>
        {rows.map((t) => (
          <div key={t.id} className={styles.card}>
            <div className={styles.top}>
              <div>
                <p className={styles.title}>{formatRub(t.total_amount)}</p>
                <p className={styles.sub}>{formatDateTime(t.created_at)}</p>
              </div>
              <span className={styles.pill}>{formatTopupMode(t.mode)}</span>
            </div>
            <div className={styles.grid}>
              <div>
                <p className={styles.k}>Распределено</p>
                <p className={styles.v}>{formatRub(t.total_allocated_amount)}</p>
              </div>
              <div>
                <p className={styles.k}>Остаток</p>
                <p className={styles.v}>{formatRub(t.total_cash_remainder)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
