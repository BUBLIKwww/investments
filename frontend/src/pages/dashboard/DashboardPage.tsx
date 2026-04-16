import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getPortfolio, refreshFundPrices } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { GlassSurface } from "@/shared/ui/GlassSurface";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { PositionCard } from "@/shared/ui/PositionCard";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SummaryCard } from "@/shared/ui/SummaryCard";
import { ValidationBanner } from "@/shared/ui/ValidationBanner";
import { Button } from "@/shared/ui/Button";
import { formatPercent, formatRub } from "@/shared/lib/format";

import styles from "./DashboardPage.module.css";

export function DashboardPage() {
  const qc = useQueryClient();
  const [priceBanner, setPriceBanner] = useState<{ variant: "success" | "error"; title: string; message: string } | null>(
    null,
  );

  const portfolioQuery = useQuery({
    queryKey: queryKeys.portfolio,
    queryFn: getPortfolio,
  });

  const refreshMutation = useMutation({
    mutationFn: refreshFundPrices,
    onSuccess: async (data) => {
      setPriceBanner({
        variant: "success",
        title: "Цены обновлены",
        message: `Обновлено инструментов: ${data.updated}. Пересчитываем портфель и ребаланс…`,
      });
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.portfolio }),
        qc.invalidateQueries({ queryKey: queryKeys.rebalance }),
        qc.invalidateQueries({ queryKey: queryKeys.funds }),
      ]);
    },
    onError: (err: unknown) => {
      const e = getUserFacingApiError(err);
      setPriceBanner({ variant: "error", title: e.title, message: e.message });
    },
  });

  useEffect(() => {
    if (!priceBanner || priceBanner.variant !== "success") return;
    const t = window.setTimeout(() => setPriceBanner(null), 5000);
    return () => window.clearTimeout(t);
  }, [priceBanner]);

  if (portfolioQuery.isPending) {
    return (
      <div>
        <PageHeader title="Портфель" subtitle="Загружаем ваши данные" />
        <LoadingBlock label="Загружаем портфель…" />
      </div>
    );
  }

  if (portfolioQuery.isError) {
    const e = getUserFacingApiError(portfolioQuery.error);
    return (
      <div>
        <PageHeader title="Портфель" subtitle="Не удалось получить сводку" />
        <ErrorBlock title={e.title} message={e.message} onRetry={() => void portfolioQuery.refetch()} />
      </div>
    );
  }

  const data = portfolioQuery.data;
  const isEmpty = !data || data.positions.length === 0;
  const busyPrices = refreshMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Портфель"
        subtitle={isEmpty ? "Начните с пополнения или добавьте сделку вручную" : "Сводка по стратегии и рынку"}
      />

      {priceBanner ? (
        <div className={styles.bannerWrap}>
          <ValidationBanner variant={priceBanner.variant} title={priceBanner.title} message={priceBanner.message} />
        </div>
      ) : null}

      {!isEmpty ? (
        <section className={styles.hero} aria-label="Ключевые показатели">
          <GlassSurface variant="strong" className={styles.heroCard}>
            <p className={styles.heroEyebrow}>Оценка портфеля</p>
            <p className={styles.heroFigure}>{formatRub(data.total_current_amount)}</p>
            <div className={styles.heroMeta}>Вложено {formatRub(data.total_invested_amount)}</div>
          </GlassSurface>
        </section>
      ) : null}

      <div className={styles.toolbar}>
        <Button type="button" variant="secondary" size="sm" disabled={busyPrices} onClick={() => refreshMutation.mutate()}>
          {busyPrices ? "Обновление цен…" : "Обновить цены"}
        </Button>
        <p className={styles.toolbarHint}>Демо: случайное изменение цены каждого активного фонда на ±1–5%.</p>
      </div>

      {isEmpty ? (
        <EmptyState
          title="Портфель пока пустой"
          description="Пополните счёт или занесите покупку в журнал сделок — позиции пересчитаются автоматически."
          actions={
            <>
              <Link className={styles.pillLink} to="/topup">
                Пополнить
              </Link>
              <Link className={styles.pillGhost} to="/transactions">
                Сделки
              </Link>
              <Link className={styles.pillGhost} to="/rebalance">
                Ребаланс
              </Link>
            </>
          }
        />
      ) : (
        <>
          <div className={styles.summaryGrid}>
            <SummaryCard label="Вложено" value={formatRub(data.total_invested_amount)} hint="Сумма покупок по позициям" />
            <SummaryCard
              label="Текущая оценка"
              value={formatRub(data.total_current_amount)}
              hint="По ценам фондов на сервере"
            />
          </div>

          <div className={styles.actions}>
            <Link className={styles.pillLink} to="/topup">
              Пополнить
            </Link>
            <Link className={styles.pillGhost} to="/transactions">
              Сделки
            </Link>
            <Link className={styles.pillGhost} to="/rebalance">
              Ребаланс
            </Link>
          </div>

          <SectionHeader title="Категории" subtitle="Целевые и фактические доли" />
          <div className={styles.grid}>
            {data.categories.map((c) => (
              <PositionCard
                key={c.category_id}
                title={c.category_name}
                invested={c.invested_amount}
                currentWeightPercent={c.current_weight_percent}
                targetWeightPercent={c.target_percent}
              />
            ))}
          </div>

          <SectionHeader title="Позиции" subtitle="Фонды в портфеле" />
          <div className={styles.grid}>
            {data.positions.map((p) => (
              <GlassSurface key={p.id} className={styles.positionCard}>
                <div className={styles.posTop}>
                  <div>
                    <p className={styles.posTitle}>{p.fund.name}</p>
                    <p className={styles.posSub}>
                      {p.category_name} · {p.total_units} шт.
                    </p>
                  </div>
                  <span className={styles.ticker}>{p.fund.ticker}</span>
                </div>
                <div className={styles.posGrid}>
                  <div>
                    <p className={styles.k}>Вложено</p>
                    <p className={styles.v}>{formatRub(p.invested_amount)}</p>
                  </div>
                  <div>
                    <p className={styles.k}>Оценка</p>
                    <p className={styles.v}>{formatRub(p.current_amount)}</p>
                  </div>
                  <div>
                    <p className={styles.k}>Доля</p>
                    <p className={styles.v}>{formatPercent(p.current_weight_percent)}</p>
                  </div>
                  <div>
                    <p className={styles.k}>Средняя</p>
                    <p className={styles.v}>{formatRub(p.average_buy_price)}</p>
                  </div>
                </div>
              </GlassSurface>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
