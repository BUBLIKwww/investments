import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getFunds, getStrategy, updateStrategy } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { FundRead, StrategyCategoryRead, StrategyUpdateRequest } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatPercent, formatRub, parseDecimal } from "@/shared/lib/format";
import { Button } from "@/shared/ui/Button";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { ValidationBanner } from "@/shared/ui/ValidationBanner";
import { FundPickerModal } from "@/widgets/fund-picker/FundPickerModal";

import styles from "./SettingsPage.module.css";

export type StrategyCategoryFormRow = {
  id: number | null;
  name: string;
  target_percent: string;
  fund_id: number;
  sort_order: number;
  is_active: boolean;
};

function fromRead(c: StrategyCategoryRead): StrategyCategoryFormRow {
  return {
    id: c.id,
    name: c.name,
    target_percent: c.target_percent,
    fund_id: c.fund_id,
    sort_order: c.sort_order,
    is_active: c.is_active,
  };
}

function normalizePercentForSave(raw: string): string {
  const n = parseDecimal(raw);
  if (!Number.isFinite(n) || n < 0) return "0.0000";
  return n.toFixed(4);
}

function buildUpdatePayload(rows: StrategyCategoryFormRow[]): StrategyUpdateRequest {
  const sorted = [...rows].sort((a, b) => a.sort_order - b.sort_order);
  return {
    categories: sorted.map((r) => ({
      id: r.id === null ? null : r.id,
      name: r.name.trim(),
      target_percent: normalizePercentForSave(r.target_percent),
      fund_id: r.fund_id,
      sort_order: r.sort_order,
      is_active: r.is_active,
    })),
  };
}

function validate(rows: StrategyCategoryFormRow[]): { ok: boolean; messages: string[]; activeSum: number } {
  const messages: string[] = [];
  const activeRows = rows.filter((r) => r.is_active);
  let activeSum = 0;

  for (const r of rows) {
    const label = r.name.trim() || `категория #${r.id ?? "новая"}`;
    if (!r.name.trim()) {
      messages.push("Укажите название для каждой категории.");
    }
    if (!r.fund_id || r.fund_id <= 0) {
      messages.push(`«${label}»: выберите фонд.`);
    }
    const p = parseDecimal(r.target_percent);
    if (!Number.isFinite(p)) {
      messages.push(`«${label}»: введите корректный процент.`);
    } else if (p < 0) {
      messages.push(`«${label}»: процент не может быть отрицательным.`);
    }
    if (r.is_active && Number.isFinite(p)) {
      activeSum += p;
    }
  }

  if (activeRows.length === 0) {
    messages.push("Должна быть хотя бы одна активная категория.");
  } else if (Math.abs(activeSum - 100) > 0.0001) {
    messages.push(
      `Сумма долей активных категорий должна быть 100%. Сейчас: ${formatPercent(activeSum, 2)}.`,
    );
  }

  return { ok: messages.length === 0, messages: [...new Set(messages)], activeSum };
}

export function StrategyEditor() {
  const qc = useQueryClient();
  const [rows, setRows] = useState<StrategyCategoryFormRow[]>([]);
  const [dirty, setDirty] = useState(false);
  const [pickerIndex, setPickerIndex] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const strategyQuery = useQuery({
    queryKey: queryKeys.strategy,
    queryFn: getStrategy,
  });

  const fundsQuery = useQuery({
    queryKey: queryKeys.funds,
    queryFn: getFunds,
  });

  useEffect(() => {
    if (strategyQuery.data && !dirty) {
      const sorted = [...strategyQuery.data.categories].sort((a, b) => a.sort_order - b.sort_order);
      setRows(sorted.map(fromRead));
    }
  }, [strategyQuery.data, dirty]);

  useEffect(() => {
    if (!saveSuccess) return;
    const t = window.setTimeout(() => setSaveSuccess(false), 4000);
    return () => window.clearTimeout(t);
  }, [saveSuccess]);

  const fundById = useMemo(() => {
    const m = new Map<number, FundRead>();
    for (const f of fundsQuery.data ?? []) {
      m.set(f.id, f);
    }
    return m;
  }, [fundsQuery.data]);

  const validation = useMemo(() => validate(rows), [rows]);

  const saveMutation = useMutation({
    mutationFn: updateStrategy,
    onSuccess: async (data) => {
      const sorted = [...data.categories].sort((a, b) => a.sort_order - b.sort_order);
      setRows(sorted.map(fromRead));
      setDirty(false);
      setSaveError(null);
      setSaveSuccess(true);
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.strategy }),
        qc.invalidateQueries({ queryKey: queryKeys.portfolio }),
        qc.invalidateQueries({ queryKey: queryKeys.rebalance }),
      ]);
    },
    onError: (e: unknown) => {
      const err = getUserFacingApiError(e);
      setSaveError(`${err.title}: ${err.message}`);
    },
  });

  const canSave = dirty && validation.ok && !saveMutation.isPending;
  const formLocked = saveMutation.isPending;

  function updateRow(index: number, patch: Partial<StrategyCategoryFormRow>) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function handleReset() {
    const data = strategyQuery.data;
    if (!data) return;
    const sorted = [...data.categories].sort((a, b) => a.sort_order - b.sort_order);
    setRows(sorted.map(fromRead));
    setDirty(false);
    setSaveError(null);
  }

  function handleSave() {
    const v = validate(rows);
    if (!v.ok) return;
    setSaveError(null);
    saveMutation.mutate(buildUpdatePayload(rows));
  }

  if (strategyQuery.isPending) {
    return (
      <section className={styles.section} aria-label="Стратегия">
        <SectionHeader title="Стратегия" subtitle="Целевые доли и привязка к фондам" />
        <LoadingBlock label="Загрузка стратегии…" />
      </section>
    );
  }

  if (strategyQuery.isError) {
    const err = getUserFacingApiError(strategyQuery.error);
    return (
      <section className={styles.section} aria-label="Стратегия">
        <SectionHeader title="Стратегия" subtitle="Целевые доли и привязка к фондам" />
        <ErrorBlock title={err.title} message={err.message} onRetry={() => void strategyQuery.refetch()} />
      </section>
    );
  }

  return (
    <section className={styles.section} aria-label="Стратегия">
      <SectionHeader title="Стратегия" subtitle="Целевые доли и привязка к фондам" />

      <div className={styles.strategyStack}>
        {saveSuccess ? (
          <ValidationBanner variant="success" title="Сохранено" message="Стратегия обновлена." />
        ) : null}
        {saveError ? <ValidationBanner variant="error" title="Ошибка сохранения" message={saveError} /> : null}
        {!validation.ok ? (
          <ValidationBanner variant="error" title="Проверьте данные" messages={validation.messages} />
        ) : null}

        <div className={styles.summary} aria-live="polite">
          <div className={styles.summaryRow}>
            <p className={styles.summaryLabel}>Сумма активных долей</p>
            <p className={styles.summaryValue}>{formatPercent(validation.activeSum, 2)}</p>
          </div>
          <div className={styles.summaryRow}>
            <p className={styles.summaryLabel}>Статус</p>
            <p className={validation.ok ? styles.statusOk : styles.statusBad}>
              {validation.ok ? "Корректно" : "Есть ошибки"}
            </p>
          </div>
        </div>

        {rows.length === 0 ? (
          <p className={styles.emptyHint}>Категории стратегии не заданы. Добавьте категории и привяжите к инструментам из каталога (сначала добавьте инструмент через сделку или обновите список фондов).</p>
        ) : (
          rows.map((row, index) => {
            const fund = fundById.get(row.fund_id);
            return (
              <article key={row.id ?? `new-${index}-${row.sort_order}`} className={styles.categoryCard}>
                <div className={styles.categoryHead}>
                  <p className={styles.categoryTitle}>Категория</p>
                </div>

                <div className={styles.field}>
                  <label className={styles.fieldLabel} htmlFor={`cat-name-${row.id}`}>
                    Название
                  </label>
                  <input
                    id={`cat-name-${row.id}`}
                    className={styles.input}
                    value={row.name}
                    disabled={formLocked}
                    onChange={(e) => {
                      setDirty(true);
                      updateRow(index, { name: e.target.value });
                    }}
                    autoComplete="off"
                  />
                </div>

                <div className={styles.field}>
                  <span className={styles.fieldLabel}>Целевая доля, %</span>
                  <div className={styles.percentRow}>
                    <input
                      className={styles.input}
                      inputMode="decimal"
                      aria-label={`Целевая доля для ${row.name || "категории"}`}
                      value={row.target_percent}
                      disabled={formLocked}
                      onChange={(e) => {
                        setDirty(true);
                        updateRow(index, { target_percent: e.target.value });
                      }}
                    />
                  </div>
                </div>

                <div className={styles.fundLine}>
                  <span className={styles.fieldLabel}>Фонд</span>
                  {fund ? (
                    <>
                      <span className={styles.fundName}>{fund.name}</span>
                      <span className={styles.fundMeta}>
                        {fund.ticker} · {formatRub(fund.price)} · лот {fund.lot}
                      </span>
                    </>
                  ) : (
                    <span className={styles.fundMeta}>Фонд #{row.fund_id} (нет в списке загрузки)</span>
                  )}
                </div>

                <div className={styles.actionsRow}>
                  <Button type="button" size="sm" disabled={formLocked} onClick={() => setPickerIndex(index)}>
                    Выбрать фонд
                  </Button>
                  <Link
                    className={[styles.linkBtn, formLocked ? styles.linkBtnDisabled : ""].filter(Boolean).join(" ")}
                    to={`/funds/${row.fund_id}`}
                    tabIndex={formLocked ? -1 : undefined}
                    aria-disabled={formLocked}
                    onClick={(e) => {
                      if (formLocked) e.preventDefault();
                    }}
                  >
                    Открыть фонд
                  </Link>
                </div>

                <div className={styles.toggleRow}>
                  <span className={styles.toggleLabel}>Активна</span>
                  <label className={styles.switch}>
                    <input
                      type="checkbox"
                      checked={row.is_active}
                      disabled={formLocked}
                      onChange={(e) => {
                        setDirty(true);
                        updateRow(index, { is_active: e.target.checked });
                      }}
                    />
                    <span className={styles.slider} />
                  </label>
                </div>
              </article>
            );
          })
        )}

        <div className={styles.saveBar}>
          <div className={styles.saveBarInner}>
            <Button
              type="button"
              variant="secondary"
              disabled={formLocked || (fundsQuery.data?.length ?? 0) === 0}
              onClick={() => {
                const first = fundsQuery.data?.[0];
                if (!first) return;
                setDirty(true);
                setRows((prev) => [
                  ...prev,
                  {
                    id: null,
                    name: "Новая категория",
                    target_percent: "0.0000",
                    fund_id: first.id,
                    sort_order: prev.length + 1,
                    is_active: true,
                  },
                ]);
              }}
            >
              Добавить категорию
            </Button>
            <Button type="button" variant="primary" disabled={!canSave || saveMutation.isPending} onClick={handleSave}>
              {saveMutation.isPending ? "Сохранение…" : "Сохранить стратегию"}
            </Button>
            <Button type="button" variant="secondary" disabled={!dirty || saveMutation.isPending} onClick={handleReset}>
              Сбросить изменения
            </Button>
          </div>
        </div>
      </div>

      <FundPickerModal
        open={pickerIndex !== null}
        funds={fundsQuery.data}
        isLoading={fundsQuery.isPending}
        isError={fundsQuery.isError}
        errorMessage={fundsQuery.error instanceof Error ? fundsQuery.error.message : undefined}
        selectedFundId={pickerIndex !== null ? rows[pickerIndex]?.fund_id : undefined}
        onClose={() => setPickerIndex(null)}
        onRetry={() => void fundsQuery.refetch()}
        onSelect={(fundId) => {
          if (pickerIndex === null) return;
          setDirty(true);
          updateRow(pickerIndex, { fund_id: fundId });
        }}
      />
    </section>
  );
}
