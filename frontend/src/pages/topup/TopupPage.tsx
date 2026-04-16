import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { calculateTopup } from "@/shared/api/endpoints";
import { persistTopupCalculation } from "@/shared/api/topup-calculation-cache";
import type { TopupMode } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { normalizeAmountForApi } from "@/shared/lib/format";
import { AmountInput } from "@/shared/ui/AmountInput";
import { Button } from "@/shared/ui/Button";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { ModeSelector } from "@/shared/ui/ModeSelector";
import { PageHeader } from "@/shared/ui/PageHeader";

import styles from "./TopupPage.module.css";

const QUICK_AMOUNTS = [1000, 3000, 5000, 10000] as const;

export function TopupPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState<TopupMode>("strict");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<{ title: string; message: string } | null>(null);

  const normalized = useMemo(() => normalizeAmountForApi(amount), [amount]);

  const calcMutation = useMutation({
    mutationFn: calculateTopup,
    onSuccess: (data) => {
      setFieldError(null);
      setApiError(null);
      persistTopupCalculation(qc, data);
      navigate("/calculation");
    },
    onError: (err: unknown) => {
      const e = getUserFacingApiError(err);
      const title = e.status === 400 ? "Не удалось рассчитать" : e.title;
      setApiError({ title, message: e.message });
    },
  });

  const onCalculate = () => {
    const value = normalizeAmountForApi(amount);
    if (!value) {
      setFieldError("Введите сумму больше 0 ₽");
      return;
    }
    setFieldError(null);
    setApiError(null);
    calcMutation.mutate({ total_amount: value, mode });
  };

  return (
    <div>
      <PageHeader
        title="Пополнение"
        subtitle="Введите сумму и режим — после «Рассчитать» откроется предварительный расчёт по фондам, затем можно подтвердить пополнение."
      />

      <div className={styles.panel}>
        <AmountInput
          id="amount"
          label="Сумма, ₽"
          value={amount}
          disabled={calcMutation.isPending}
          onChange={(v) => {
            setAmount(v);
            if (fieldError) setFieldError(null);
            if (apiError) setApiError(null);
          }}
          placeholder="Например, 25 000"
          error={fieldError}
        />

        <div className={styles.chips} aria-label="Быстрые суммы">
          {QUICK_AMOUNTS.map((v) => (
            <button
              key={v}
              type="button"
              className={styles.chip}
              disabled={calcMutation.isPending}
              onClick={() => setAmount(String(v))}
            >
              {v.toLocaleString("ru-RU")} ₽
            </button>
          ))}
        </div>

        <p className={styles.sectionTitle}>Режим</p>
        <ModeSelector value={mode} onChange={setMode} disabled={calcMutation.isPending} />

        <div className={styles.row}>
          <Button variant="primary" onClick={onCalculate} disabled={calcMutation.isPending || !normalized}>
            {calcMutation.isPending ? "Считаем…" : "Рассчитать"}
          </Button>
          <Button variant="ghost" onClick={() => setAmount("")} disabled={calcMutation.isPending}>
            Сбросить
          </Button>
        </div>

        {apiError ? (
          <div style={{ marginTop: 12 }}>
            <ErrorBlock title={apiError.title} message={apiError.message} onRetry={onCalculate} />
          </div>
        ) : null}

        <p className={styles.hint}>
          Сначала сервер посчитает распределение по лотам, ценам фондов и вашей стратегии. На следующем шаге вы сможете
          проверить цифры и подтвердить пополнение — до подтверждения портфель не меняется.
        </p>
      </div>
    </div>
  );
}
