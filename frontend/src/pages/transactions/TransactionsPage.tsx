import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { getFunds, listTransactions } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { InvestmentTransactionRead } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatDateTime, formatRub } from "@/shared/lib/format";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { GlassSurface } from "@/shared/ui/GlassSurface";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";

import styles from "./TransactionsPage.module.css";

function fundNameById(funds: { id: number; name: string }[], fundId: number): string {
  return funds.find((f) => f.id === fundId)?.name ?? `Фонд #${fundId}`;
}

function opLabel(t: InvestmentTransactionRead): string {
  return t.operation_type === "buy" ? "Покупка" : "Продажа";
}

export function TransactionsPage() {
  const txQ = useQuery({
    queryKey: queryKeys.transactions,
    queryFn: listTransactions,
  });
  const fundsQ = useQuery({
    queryKey: queryKeys.funds,
    queryFn: getFunds,
  });

  if (txQ.isPending || fundsQ.isPending) {
    return (
      <div>
        <PageHeader title="Сделки" subtitle="Журнал операций" />
        <LoadingBlock label="Загружаем сделки…" />
      </div>
    );
  }

  if (txQ.isError) {
    const err = getUserFacingApiError(txQ.error);
    return (
      <div>
        <PageHeader title="Сделки" subtitle="Журнал операций" />
        <ErrorBlock title={err.title} message={err.message} onRetry={() => void txQ.refetch()} />
      </div>
    );
  }

  const rows = txQ.data ?? [];
  const funds = fundsQ.data ?? [];

  return (
    <div>
      <PageHeader title="Сделки" subtitle="Источник для расчёта портфеля" />
      <p className={styles.links}>
        <Link className={styles.inlineLink} to="/history">
          История пополнений
        </Link>
      </p>
      <div className={styles.toolbar}>
        <Link className={styles.primaryLink} to="/transactions/new">
          Добавить транзакцию
        </Link>
      </div>

      {rows.length === 0 ? (
        <EmptyState
          kicker="Журнал"
          title="Пока нет сделок"
          description="Добавьте покупку или продажу — позиции портфеля обновятся автоматически."
          actions={
            <Link className={styles.primaryLink} to="/transactions/new">
              Добавить транзакцию
            </Link>
          }
        />
      ) : (
        <div className={styles.list}>
          {rows.map((t) => (
            <Link key={t.id} className={styles.listLink} to={`/transactions/${t.id}`}>
              <GlassSurface variant="strong" className={styles.row}>
                <div className={styles.top}>
                  <div>
                    <p className={styles.title}>{fundNameById(funds, t.fund_id)}</p>
                    <p className={styles.sub}>{formatDateTime(t.executed_at)}</p>
                  </div>
                  <span
                    className={[
                      styles.pill,
                      t.operation_type === "buy" ? styles.pillBuy : styles.pillSell,
                    ].join(" ")}
                  >
                    {opLabel(t)}
                  </span>
                </div>
                <div className={styles.grid}>
                  <div>
                    <p className={styles.k}>Количество</p>
                    <p className={styles.v}>{t.quantity} шт.</p>
                  </div>
                  <div>
                    <p className={styles.k}>Сумма</p>
                    <p className={styles.v}>{formatRub(t.total_amount)}</p>
                  </div>
                </div>
              </GlassSurface>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
