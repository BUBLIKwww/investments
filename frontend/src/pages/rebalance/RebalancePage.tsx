import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getRebalance, postRebalanceExecute, postRebalancePreview } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { RebalanceSmartPreview } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatPercent, formatRub, parseDecimal } from "@/shared/lib/format";
import { Button } from "@/shared/ui/Button";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { GlassSurface } from "@/shared/ui/GlassSurface";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { ValidationBanner } from "@/shared/ui/ValidationBanner";

import styles from "./RebalancePage.module.css";

function parseAmountPayload(raw: string): { amount: number | null } | { error: string } {
  const t = raw.trim();
  if (!t) return { amount: null };
  const n = parseDecimal(t);
  if (!Number.isFinite(n) || n < 0) {
    return { error: "Введите неотрицательную сумму или оставьте поле пустым (весь баланс)." };
  }
  return { amount: n };
}

export function RebalancePage() {
  const qc = useQueryClient();
  const { data, isPending, isError, error } = useQuery({
    queryKey: queryKeys.rebalance,
    queryFn: getRebalance,
  });

  const [amountStr, setAmountStr] = useState("");
  const [plan, setPlan] = useState<RebalanceSmartPreview | null>(null);
  const [planPayload, setPlanPayload] = useState<{ amount: number | null } | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const previewMutation = useMutation({
    mutationFn: postRebalancePreview,
    onSuccess: (res, variables) => {
      setPlan(res);
      setPlanPayload(variables);
      setLocalError(null);
      setSuccessMsg(null);
    },
    onError: (e: unknown) => {
      setPlan(null);
      setPlanPayload(null);
      setLocalError(getUserFacingApiError(e).message);
    },
  });

  const executeMutation = useMutation({
    mutationFn: postRebalanceExecute,
    onSuccess: async (res) => {
      setSuccessMsg(`Создано сделок: ${res.created_transaction_ids.length}.`);
      setLocalError(null);
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.portfolio }),
        qc.invalidateQueries({ queryKey: queryKeys.rebalance }),
        qc.invalidateQueries({ queryKey: queryKeys.transactions }),
      ]);
    },
    onError: (e: unknown) => {
      setSuccessMsg(null);
      setLocalError(getUserFacingApiError(e).message);
    },
  });

  const retry = () => {
    void qc.invalidateQueries({ queryKey: queryKeys.rebalance });
  };

  const onCalculate = () => {
    setSuccessMsg(null);
    const parsed = parseAmountPayload(amountStr);
    if ("error" in parsed) {
      setLocalError(parsed.error);
      setPlan(null);
      setPlanPayload(null);
      return;
    }
    setLocalError(null);
    previewMutation.mutate(parsed);
  };

  const onApply = () => {
    if (!planPayload) return;
    setSuccessMsg(null);
    executeMutation.mutate(planPayload);
  };

  if (isPending) {
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов и план с учётом баланса" />
        <LoadingBlock label="Загружаем ребаланс…" />
      </div>
    );
  }

  if (isError) {
    const err = getUserFacingApiError(error);
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов и план с учётом баланса" />
        <ErrorBlock title={err.title} message={err.message} onRetry={retry} />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="Ребаланс" subtitle="Сравнение весов и план с учётом баланса" />
        <ErrorBlock message="Нет данных" onRetry={retry} />
      </div>
    );
  }

  const nameById = new Map(data.categories.map((c) => [c.category_id, c.category_name] as const));
  const busy = previewMutation.isPending || executeMutation.isPending;

  return (
    <div>
      <PageHeader title="Ребаланс" subtitle="Текущие и целевые доли; симуляция сделок без заявок в брокере" />

      <SectionHeader title="Умный ребаланс" subtitle="Баланс = пополнения − покупки + продажи; план по целям стратегии" />

      <GlassSurface variant="strong" className={styles.smartCard}>
        <div className={styles.smartRow}>
          <label className={styles.smartLabel} htmlFor="rebalance-amt">
            Сумма из баланса (пусто — весь баланс)
          </label>
          <input
            id="rebalance-amt"
            className={styles.smartInput}
            inputMode="decimal"
            placeholder="Например 50000 или пусто"
            value={amountStr}
            disabled={busy}
            onChange={(e) => setAmountStr(e.target.value)}
          />
        </div>
        <div className={styles.smartActions}>
          <Button type="button" variant="primary" disabled={busy} onClick={onCalculate}>
            {previewMutation.isPending ? "Считаем…" : "Рассчитать"}
          </Button>
          <Button type="button" variant="secondary" disabled={busy || !planPayload} onClick={onApply}>
            {executeMutation.isPending ? "Применяем…" : "Применить"}
          </Button>
        </div>
        {localError ? <ValidationBanner variant="error" title="Ошибка" message={localError} /> : null}
        {successMsg ? <ValidationBanner variant="success" title="Готово" message={successMsg} /> : null}
        {plan ? (
          <div className={styles.smartMeta}>
            <p>
              Баланс: <strong>{formatRub(plan.cash_balance)}</strong> · Доля плана:{" "}
              <strong>{formatPercent(parseDecimal(plan.scale) * 100, 1)}</strong> · Чистый отток кэша по плану:{" "}
              <strong>{formatRub(plan.total_used)}</strong>
            </p>
            <p className={styles.marketShare}>
              Оценка позиций в капитале (рынок / всё):{" "}
              <strong>{formatPercent(plan.before_percent, 1)}</strong>
              <span className={styles.arrowMid} aria-hidden>
                {" "}
                →{" "}
              </span>
              <strong>{formatPercent(plan.after_percent, 1)}</strong> после симуляции
            </p>
            {plan.instruments.length > 0 ? (
              <div className={styles.allocSection}>
                <p className={styles.allocLead}>По инструментам (доля капитала): текущая → цель → после плана</p>
                <ul className={styles.allocList}>
                  {plan.instruments.map((row) => {
                    const cur = Math.min(100, Math.max(0, parseDecimal(row.current_percent)));
                    const tgt = Math.min(100, Math.max(0, parseDecimal(row.target_percent)));
                    const aft = Math.min(100, Math.max(0, parseDecimal(row.after_percent)));
                    return (
                      <li key={`${row.fund_id}-${row.ticker}`} className={styles.allocItem}>
                        <div className={styles.allocTop}>
                          <span className={styles.allocTicker}>{row.ticker}</span>
                          <span className={styles.allocFlow}>
                            {formatPercent(row.current_percent, 1)}
                            <span className={styles.arrowMid} aria-hidden>
                              {" "}
                              →{" "}
                            </span>
                            {formatPercent(row.target_percent, 1)}
                            <span className={styles.arrowMid} aria-hidden>
                              {" "}
                              →{" "}
                            </span>
                            {formatPercent(row.after_percent, 1)}
                          </span>
                        </div>
                        <div className={styles.allocTrack} aria-hidden>
                          <div className={styles.allocFill} style={{ width: `${cur}%` }} />
                          <div className={styles.allocGoal} style={{ left: `clamp(0%, ${tgt}%, 100%)` }} title="Цель" />
                          <div className={styles.allocAfter} style={{ left: `clamp(0%, ${aft}%, 100%)` }} title="После плана" />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}
            {plan.actions.length === 0 ? (
              <p className={styles.smartEmpty}>Нет операций (уже на цели или нулевой сдвиг).</p>
            ) : (
              <ul className={styles.actionList}>
                {plan.actions.map((a, i) => (
                  <li key={`${i}-${a.action}-${a.fund_id}`} className={styles.actionItem}>
                    <span className={a.action === "buy" ? styles.actionBuy : styles.actionSell}>
                      {a.action === "buy" ? "Купить" : "Продать"}
                    </span>
                    <span className={styles.actionTicker}>{a.ticker}</span>
                    <span className={styles.actionAmt}>{formatRub(a.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
            <p className={styles.smartHint}>
              «Применить» создаёт записи в журнале сделок (симуляция), без выставления заявок в T‑Invest.
            </p>
          </div>
        ) : null}
      </GlassSurface>

      <SectionHeader title="Сводка" subtitle="Категории ниже цели / выше цели" />

      <div className={styles.chips}>
        <span className={styles.chip}>
          Ниже цели:{" "}
          {data.underweight.length ? data.underweight.map((id) => nameById.get(id) ?? id).join(", ") : "—"}
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
