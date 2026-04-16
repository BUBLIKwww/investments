import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useTopupCalculationQuery } from "@/hooks/useTopupCalculationQuery";
import { createTopup } from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import { clearTopupCalculation } from "@/shared/api/topup-calculation-cache";
import type { TopupCalculateRequest, TopupCalculateResponse } from "@/shared/api/types";
import { getUserFacingApiError, type UserFacingApiError } from "@/shared/lib/api-error-message";
import { formatRub, formatTopupMode, parseDecimal } from "@/shared/lib/format";
import { Button } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { TopupItemCard } from "@/shared/ui/TopupItemCard";
import { ValidationBanner } from "@/shared/ui/ValidationBanner";

import styles from "./CalculationPage.module.css";

function buildPayload(data: TopupCalculateResponse): TopupCalculateRequest {
  return { total_amount: data.total_amount, mode: data.mode };
}

export function CalculationPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const calcQuery = useTopupCalculationQuery();
  const [success, setSuccess] = useState(false);
  const [saveError, setSaveError] = useState<UserFacingApiError | null>(null);

  const saveMutation = useMutation({
    mutationFn: createTopup,
    onSuccess: async () => {
      setSaveError(null);
      clearTopupCalculation(qc);
      await Promise.all([
        qc.invalidateQueries({ queryKey: queryKeys.portfolio }),
        qc.invalidateQueries({ queryKey: queryKeys.topupHistory }),
        qc.invalidateQueries({ queryKey: queryKeys.transactions }),
        qc.invalidateQueries({ queryKey: queryKeys.rebalance }),
      ]);
      setSuccess(true);
    },
    onError: (err: unknown) => {
      setSaveError(getUserFacingApiError(err));
    },
  });

  useEffect(() => {
    if (!success) return;
    const t = window.setTimeout(() => navigate("/"), 1100);
    return () => window.clearTimeout(t);
  }, [navigate, success]);

  const data = calcQuery.data;

  const allocationHint = useMemo(() => {
    if (!data || success) return null;
    const total = parseDecimal(data.total_amount);
    const rem = parseDecimal(data.total_cash_remainder);
    const alloc = parseDecimal(data.total_allocated_amount);
    const nothingBought = data.items.length > 0 && data.items.every((i) => i.purchased_units === 0);
    if (nothingBought) {
      return {
        variant: "error" as const,
        title: "Покупок нет",
        message:
          "По выбранной сумме не удалось купить ни одного лота. Увеличьте сумму или проверьте цены и размер лотов в карточках фондов.",
      };
    }
    if (!Number.isFinite(total) || total <= 0) return null;
    const remRatio = Number.isFinite(rem) ? rem / total : 0;
    if (remRatio >= 0.3) {
      return {
        variant: "info" as const,
        title: "Большой остаток",
        message: `Свободными остаются около ${(remRatio * 100).toFixed(0)}% суммы (${formatRub(
          data.total_cash_remainder,
        )}). Это из‑за целых лотов: часть денег нельзя распределить без дробных покупок. Попробуйте увеличить сумму или режим «Максимум».`,
      };
    }
    if (Number.isFinite(alloc) && alloc > 0 && alloc / total < 0.2 && remRatio > 0.15) {
      return {
        variant: "info" as const,
        title: "Мало ушло в покупки",
        message: `Распределено ${formatRub(data.total_allocated_amount)} из ${formatRub(
          data.total_amount,
        )}. Остаток ${formatRub(data.total_cash_remainder)} — при малых суммах это ожидаемо, если лоты дорогие.`,
      };
    }
    return null;
  }, [data, success]);

  if (calcQuery.isPending) {
    return (
      <div>
        <PageHeader title="Расчёт пополнения" subtitle="Проверяем последний расчёт" />
        <LoadingBlock label="Загружаем расчёт…" />
      </div>
    );
  }

  if (calcQuery.isError) {
    const msg = calcQuery.error instanceof Error ? calcQuery.error.message : "Ошибка";
    if (msg === "NO_CALCULATION") {
      return (
        <div>
          <PageHeader title="Расчёт пополнения" subtitle="Нет сохранённого результата" />
          <EmptyState
            title="Сначала сделайте расчёт"
            description="Мы не нашли последний расчёт в памяти приложения. Вернитесь к вводу суммы и нажмите «Рассчитать»."
            actions={
              <Link className={styles.pillLink} to="/topup">
                К пополнению
              </Link>
            }
          />
        </div>
      );
    }

    const e = getUserFacingApiError(calcQuery.error);
    return (
      <div>
        <PageHeader title="Расчёт пополнения" subtitle="Не удалось открыть расчёт" />
        <ErrorBlock title={e.title} message={e.message} onRetry={() => void calcQuery.refetch()} />
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="Расчёт пополнения" subtitle="Нет данных" />
        <ErrorBlock
          message="Не удалось отобразить расчёт."
          onRetry={() => void qc.invalidateQueries({ queryKey: queryKeys.topupCalculation })}
        />
      </div>
    );
  }

  if (success) {
    return (
      <div>
        <PageHeader title="Готово" subtitle="Пополнение записано в историю" />
        <div className={styles.success}>
          <p className={styles.successTitle}>Пополнение подтверждено</p>
          <p className={styles.successText}>
            Портфель, категории и история обновлены. Сейчас откроется главный экран с новыми суммами.
          </p>
        </div>
      </div>
    );
  }

  const payload = buildPayload(data);

  return (
    <div>
      <PageHeader
        title="Подтверждение пополнения"
        subtitle="Ниже — предварительный расчёт с backend: фонды, лоты, акции и остаток. Деньги спишутся только после подтверждения."
      />

      <div className={styles.previewBanner}>
        <ValidationBanner
          variant="info"
          title="Предварительный расчёт"
          message="Пока вы не нажали «Подтвердить пополнение», сделки не выполняются и портфель не меняется."
        />
      </div>

      <div className={styles.panel}>
        <div className={styles.kpis}>
          <div className={styles.kpi}>
            <p className={styles.k}>Сумма</p>
            <p className={styles.v}>{formatRub(data.total_amount)}</p>
          </div>
          <div className={styles.kpi}>
            <p className={styles.k}>Распределено</p>
            <p className={styles.v}>{formatRub(data.total_allocated_amount)}</p>
          </div>
          <div className={styles.kpi}>
            <p className={styles.k}>Остаток</p>
            <p className={styles.v}>{formatRub(data.total_cash_remainder)}</p>
          </div>
          <div className={styles.kpi}>
            <p className={styles.k}>Режим</p>
            <p className={styles.v} style={{ fontSize: 14 }}>
              {formatTopupMode(data.mode)}
            </p>
          </div>
        </div>
        {allocationHint ? (
          <div className={styles.hintBanner}>
            <ValidationBanner
              variant={allocationHint.variant}
              title={allocationHint.title}
              message={allocationHint.message}
            />
          </div>
        ) : null}
      </div>

      <SectionHeader title="По фондам и категориям" subtitle="Сколько уйдёт в покупку и сколько акций купится по каждой позиции" />
      <div className={styles.list}>
        {data.items.map((item) => (
          <TopupItemCard key={`${item.category_id}-${item.fund_id}`} item={item} />
        ))}
      </div>

      {saveError ? (
        <div className={styles.errorWrap}>
          <ErrorBlock title={saveError.title} message={saveError.message} onRetry={() => saveMutation.mutate(payload)} />
        </div>
      ) : null}

      {saveMutation.isPending ? <LoadingBlock label="Сохраняем пополнение…" /> : null}

      <div className={styles.actions}>
        <Button variant="primary" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(payload)}>
          Подтвердить пополнение
        </Button>
        <Button variant="secondary" disabled={saveMutation.isPending} onClick={() => navigate("/topup")}>
          Пересчитать
        </Button>
        <Button variant="ghost" disabled={saveMutation.isPending} onClick={() => navigate("/topup")}>
          Назад
        </Button>
      </div>
    </div>
  );
}
