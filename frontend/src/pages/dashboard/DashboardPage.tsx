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
import { formatDateTime, formatPercent, formatRub, formatSignedRub, parseDecimal } from "@/shared/lib/format";

import styles from "./DashboardPage.module.css";

export function DashboardPage() {
  const qc = useQueryClient();
  const [priceBanner, setPriceBanner] = useState<{ variant: "success" | "error"; title: string; message: string } | null>(
    null,
  );

  const portfolioQuery = useQuery({
    queryKey: queryKeys.portfolio("live"),
    queryFn: () => getPortfolio("live"),
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
        qc.invalidateQueries({ queryKey: ["portfolio"] }),
        qc.invalidateQueries({ queryKey: ["rebalance"] }),
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
  const isEmpty =
    !data ||
    !Array.isArray(data.positions) ||
    data.positions.length === 0;
  const busyPrices = refreshMutation.isPending;
  const totalCurrent = data?.total_current_amount ?? 0;
  const totalInvested = data?.total_invested_amount ?? 0;
  const totalPnlStr = data?.total_pnl ?? "0";
  const totalPnlPctStr = data?.total_pnl_percent ?? "0";
  const totalPnlN = parseDecimal(totalPnlStr);
  const pnlTone =
    !Number.isFinite(totalPnlN) || totalPnlN === 0 ? "" : totalPnlN > 0 ? styles.pnlPos : styles.pnlNeg;

  return (
    <div>
      <PageHeader
        title="Портфель"
        subtitle={
          isEmpty
            ? "Начните с пополнения или добавьте сделку вручную"
            : data?.source === "live"
              ? "Позиции с брокерского счёта T‑Invest; категории — по вашей стратегии в приложении"
              : "Сводка по журналу приложения (симуляция)"
        }
      />

      {priceBanner ? (
        <div className={styles.bannerWrap}>
          <ValidationBanner variant={priceBanner.variant} title={priceBanner.title} message={priceBanner.message} />
        </div>
      ) : null}

      <section className={styles.hero} aria-label="Ключевые показатели">
        <GlassSurface variant="strong" elevated className={styles.heroCard}>
          <p className={styles.heroEyebrow}>Оценка портфеля</p>
          <p className={styles.heroFigure}>{formatRub(totalCurrent)}</p>
          {!isEmpty && data ? (
            <p className={[styles.heroPnl, pnlTone].filter(Boolean).join(" ")} aria-label="Прибыль или убыток">
              {formatSignedRub(totalPnlStr)} <span className={styles.heroPnlPct}>({formatPercent(totalPnlPctStr, 2)})</span>
            </p>
          ) : null}
          <div className={styles.heroMeta}>
            Вложено {formatRub(totalInvested)}
            {isEmpty ? <span className={styles.heroHint}> · добавьте сделку или пополнение</span> : null}
          </div>
        </GlassSurface>
      </section>

      <div className={styles.toolbar}>
        <Button type="button" variant="secondary" size="sm" disabled={busyPrices} onClick={() => refreshMutation.mutate()}>
          {busyPrices ? "Обновление цен…" : "Обновить цены"}
        </Button>
        <p className={styles.toolbarHint}>
          Котировки обновляются через T‑Invest API (last price). Убедитесь, что на сервере задан TINVEST_TOKEN.
        </p>
      </div>

      {isEmpty ? (
        <EmptyState
          kicker="Старт"
          title="Портфель пока пустой"
          description="Пополните счёт или занесите покупку в журнал сделок — позиции пересчитаются автоматически."
          icon={
            <svg viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7Z"
                stroke="currentColor"
                strokeWidth="1.65"
              />
              <path d="M4 10h16" stroke="currentColor" strokeWidth="1.65" />
              <circle cx="16.5" cy="13.5" r="1.25" fill="currentColor" />
            </svg>
          }
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
            <SummaryCard label="Вложено" value={formatRub(totalInvested)} hint="Сумма покупок по позициям" />
            <SummaryCard
              label="Текущая оценка"
              value={formatRub(totalCurrent)}
              hint="По ценам фондов на сервере"
            />
            <SummaryCard
              label="PnL"
              value={formatSignedRub(totalPnlStr)}
              hint={`Доля от вложений: ${formatPercent(totalPnlPctStr, 2)}`}
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
            {data.positions.map((p) => {
              const pnlN = parseDecimal(p.pnl);
              const pnlCls =
                !Number.isFinite(pnlN) || pnlN === 0 ? styles.pnlZero : pnlN > 0 ? styles.pnlPos : styles.pnlNeg;
              return (
                <GlassSurface key={p.id} variant="strong" className={styles.positionCard}>
                  <div className={styles.posTop}>
                    <div>
                      <p className={styles.posTitle}>{p.fund.name}</p>
                      <p className={styles.posSub}>
                        {p.category_name} · {p.quantity} шт. · цена {formatRub(p.current_price)}
                        {p.last_price_updated_at ? (
                          <>
                            {" "}
                            · кот. {formatDateTime(p.last_price_updated_at)}
                          </>
                        ) : null}
                      </p>
                    </div>
                    <span className={styles.ticker}>{p.fund.ticker}</span>
                  </div>
                  <div className={styles.posPnlRow}>
                    <p className={styles.k}>Результат</p>
                    <p className={[styles.posPnlValue, pnlCls].join(" ")}>
                      {formatSignedRub(p.pnl)} <span className={styles.posPnlBracket}>({formatPercent(p.pnl_percent, 2)})</span>
                    </p>
                  </div>
                  <div className={styles.posGrid}>
                    <div>
                      <p className={styles.k}>Вложено</p>
                      <p className={styles.v}>{formatRub(p.invested_value)}</p>
                    </div>
                    <div>
                      <p className={styles.k}>Оценка</p>
                      <p className={styles.v}>{formatRub(p.current_value)}</p>
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
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
