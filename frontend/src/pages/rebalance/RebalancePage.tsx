import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  getRebalance,
  postRebalanceExecute,
  postRebalanceExecuteLive,
  postRebalancePreview,
} from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { RebalanceLiveExecuteResult, RebalanceSmartPreview } from "@/shared/api/types";
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

type RbMode = "simulation" | "live";
type CashMode = "all" | "fixed";

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
  const [rbMode, setRbMode] = useState<RbMode>("live");
  const [cashMode, setCashMode] = useState<CashMode>("all");
  const [amountStr, setAmountStr] = useState("");
  const [plan, setPlan] = useState<RebalanceSmartPreview | null>(null);
  const [planPayload, setPlanPayload] = useState<{ amount: number | null; mode: RbMode } | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [confirmLive, setConfirmLive] = useState(false);
  const [liveResult, setLiveResult] = useState<RebalanceLiveExecuteResult | null>(null);

  const { data, isPending, isError, error } = useQuery({
    queryKey: queryKeys.rebalance(rbMode),
    queryFn: () => getRebalance(rbMode),
  });

  const previewMutation = useMutation({
    mutationFn: (vars: { amount: number | null; mode: RbMode }) => postRebalancePreview(vars),
    onSuccess: (res, variables) => {
      setPlan(res);
      setPlanPayload(variables);
      setLocalError(null);
      setSuccessMsg(null);
      setLiveResult(null);
      setConfirmLive(false);
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
        qc.invalidateQueries({ queryKey: ["portfolio"] }),
        qc.invalidateQueries({ queryKey: ["rebalance"] }),
        qc.invalidateQueries({ queryKey: queryKeys.transactions }),
      ]);
    },
    onError: (e: unknown) => {
      setSuccessMsg(null);
      setLocalError(getUserFacingApiError(e).message);
    },
  });

  const liveExecuteMutation = useMutation({
    mutationFn: (p: { confirm: boolean; dryRun: boolean }) =>
      postRebalanceExecuteLive({
        amount: planPayload?.amount ?? null,
        plan_fingerprint: plan?.plan_fingerprint ?? "",
        confirm: p.confirm,
        dry_run: p.dryRun,
      }),
    onSuccess: async (res) => {
      setLiveResult(res);
      setLocalError(null);
      if (!res.dry_run) {
        setSuccessMsg(`Заявок: ${res.orders.length}.`);
        await Promise.all([
          qc.invalidateQueries({ queryKey: ["portfolio"] }),
          qc.invalidateQueries({ queryKey: ["rebalance"] }),
        ]);
      } else {
        setSuccessMsg("Dry-run: заявки не отправлялись.");
      }
    },
    onError: (e: unknown) => {
      setLiveResult(null);
      setSuccessMsg(null);
      setLocalError(getUserFacingApiError(e).message);
    },
  });

  const retry = () => {
    void qc.invalidateQueries({ queryKey: ["rebalance"] });
  };

  const onCalculate = () => {
    setSuccessMsg(null);
    setLiveResult(null);
    let amount: number | null = null;
    if (cashMode === "fixed") {
      const parsed = parseAmountPayload(amountStr);
      if ("error" in parsed) {
        setLocalError(parsed.error);
        setPlan(null);
        setPlanPayload(null);
        return;
      }
      amount = parsed.amount;
    } else {
      amount = null;
    }
    setLocalError(null);
    previewMutation.mutate({ amount, mode: rbMode });
  };

  const onApplySimulation = () => {
    if (!planPayload || planPayload.mode !== "simulation") return;
    setSuccessMsg(null);
    executeMutation.mutate({ amount: planPayload.amount });
  };

  const onLiveExecute = (dryRun: boolean) => {
    if (!planPayload || planPayload.mode !== "live" || !plan?.plan_fingerprint) return;
    if (!dryRun && !confirmLive) {
      setLocalError("Отметьте подтверждение перед реальными заявками.");
      return;
    }
    if (!dryRun) {
      const ok = window.confirm(
        "Отправить рыночные заявки в T‑Invest? Сначала продажи, затем покупки. Продолжить?",
      );
      if (!ok) return;
    }
    setLocalError(null);
    liveExecuteMutation.mutate({ confirm: !dryRun, dryRun });
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
  const busy =
    previewMutation.isPending || executeMutation.isPending || liveExecuteMutation.isPending;

  return (
    <div>
      <PageHeader
        title="Ребаланс"
        subtitle="Симуляция по журналу приложения или live по счёту T‑Invest (preview → подтверждение → заявки)"
      />

      <SectionHeader title="Режим" subtitle="Источник баланса и позиций для расчёта" />

      <GlassSurface variant="strong" className={styles.smartCard}>
        <div className={styles.smartRow}>
          <span className={styles.smartLabel}>Источник данных</span>
          <div className={styles.smartActions}>
            <Button
              type="button"
              variant={rbMode === "simulation" ? "primary" : "secondary"}
              size="sm"
              disabled={busy}
              onClick={() => {
                setRbMode("simulation");
                setPlan(null);
                setPlanPayload(null);
              }}
            >
              Симуляция
            </Button>
            <Button
              type="button"
              variant={rbMode === "live" ? "primary" : "secondary"}
              size="sm"
              disabled={busy}
              onClick={() => {
                setRbMode("live");
                setPlan(null);
                setPlanPayload(null);
              }}
            >
              Live (T‑Invest)
            </Button>
          </div>
        </div>
        <div className={styles.smartRow}>
          <span className={styles.smartLabel}>Использование кэша</span>
          <div className={styles.smartActions}>
            <Button
              type="button"
              variant={cashMode === "all" ? "primary" : "secondary"}
              size="sm"
              disabled={busy}
              onClick={() => setCashMode("all")}
            >
              Весь доступный
            </Button>
            <Button
              type="button"
              variant={cashMode === "fixed" ? "primary" : "secondary"}
              size="sm"
              disabled={busy}
              onClick={() => setCashMode("fixed")}
            >
              Моя сумма
            </Button>
          </div>
        </div>
      </GlassSurface>

      <SectionHeader
        title="Умный ребаланс"
        subtitle={
          rbMode === "live"
            ? "Кэш и позиции — с брокерского счёта; заявки только после preview и подтверждения"
            : "Баланс = пополнения − покупки + продажи (журнал приложения)"
        }
      />

      <GlassSurface variant="strong" className={styles.smartCard}>
        {cashMode === "fixed" ? (
          <div className={styles.smartRow}>
            <label className={styles.smartLabel} htmlFor="rebalance-amt">
              Сумма из доступного кэша (руб.)
            </label>
            <input
              id="rebalance-amt"
              className={styles.smartInput}
              inputMode="decimal"
              placeholder="Например 50000"
              value={amountStr}
              disabled={busy}
              onChange={(e) => setAmountStr(e.target.value)}
            />
          </div>
        ) : (
          <p className={styles.smartHint}>Будет использован весь доступный рублёвый остаток на счёте / в симуляции.</p>
        )}
        <div className={styles.smartActions}>
          <Button type="button" variant="primary" disabled={busy} onClick={onCalculate}>
            {previewMutation.isPending ? "Считаем…" : "Рассчитать preview"}
          </Button>
          {rbMode === "simulation" ? (
            <Button type="button" variant="secondary" disabled={busy || !planPayload} onClick={onApplySimulation}>
              {executeMutation.isPending ? "Применяем…" : "Применить (журнал)"}
            </Button>
          ) : null}
        </div>
        {rbMode === "live" && plan?.mode === "live" ? (
          <div className={styles.smartRow} style={{ marginTop: 12, flexDirection: "column", alignItems: "flex-start" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={confirmLive} disabled={busy} onChange={(e) => setConfirmLive(e.target.checked)} />
              Подтверждаю отправку рыночных заявок в T‑Invest
            </label>
            <div className={styles.smartActions} style={{ marginTop: 8 }}>
              <Button
                type="button"
                variant="secondary"
                disabled={busy || !planPayload}
                onClick={() => onLiveExecute(true)}
              >
                {liveExecuteMutation.isPending ? "…" : "Dry-run"}
              </Button>
              <Button type="button" variant="primary" disabled={busy || !planPayload} onClick={() => onLiveExecute(false)}>
                {liveExecuteMutation.isPending ? "Отправка…" : "Выполнить"}
              </Button>
            </div>
            {plan.account_id ? (
              <p className={styles.smartHint} style={{ marginTop: 8 }}>
                Счёт: <code>{plan.account_id}</code> · отпечаток плана: <code>{plan.plan_fingerprint.slice(0, 12)}…</code>
              </p>
            ) : null}
          </div>
        ) : null}
        {localError ? <ValidationBanner variant="error" title="Ошибка" message={localError} /> : null}
        {successMsg ? <ValidationBanner variant="success" title="Готово" message={successMsg} /> : null}
        {plan ? (
          <div className={styles.smartMeta}>
            <p>
              Режим: <strong>{plan.mode === "live" ? "live" : "симуляция"}</strong> · Баланс:{" "}
              <strong>{formatRub(plan.cash_balance)}</strong> · Доля плана:{" "}
              <strong>{formatPercent(parseDecimal(plan.scale) * 100, 1)}</strong> · Чистый отток кэша по плану:{" "}
              <strong>{formatRub(plan.total_used)}</strong>
            </p>
            <p className={styles.marketShare}>
              Оценка позиций в капитале (рынок / всё): <strong>{formatPercent(plan.before_percent, 1)}</strong>
              <span className={styles.arrowMid} aria-hidden>
                {" "}
                →{" "}
              </span>
              <strong>{formatPercent(plan.after_percent, 1)}</strong> после плана
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
                    <span className={styles.actionAmt}>
                      {a.lots} лот. · {a.quantity} шт.
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className={styles.smartHint}>
              {plan.mode === "live"
                ? "Live: preview обязателен перед «Выполнить»; на брокере сначала продажи, затем покупки (рыночные заявки)."
                : "«Применить» создаёт записи в журнале сделок без заявок в T‑Invest."}
            </p>
          </div>
        ) : null}
        {liveResult && liveResult.orders.length > 0 ? (
          <div className={styles.smartMeta} style={{ marginTop: 16 }}>
            <p className={styles.allocLead}>Результат по заявкам</p>
            <ul className={styles.actionList}>
              {liveResult.orders.map((o, i) => (
                <li key={`${i}-${o.ticker}-${o.action}`} className={styles.actionItem}>
                  <span className={o.success ? styles.actionBuy : styles.actionSell}>
                    {o.success ? "OK" : "Ошибка"}
                  </span>
                  <span className={styles.actionTicker}>
                    {o.action} {o.ticker} · {o.lots} лот.
                  </span>
                  <span className={styles.actionAmt}>{o.execution_status ?? ""}</span>
                  <span className={styles.actionAmt}>{o.message ?? ""}</span>
                </li>
              ))}
            </ul>
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
