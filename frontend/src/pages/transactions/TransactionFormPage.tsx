import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useMatch, useNavigate, useParams } from "react-router-dom";

import {
  createTransaction,
  deleteTransaction,
  getFunds,
  getTransaction,
  updateTransaction,
} from "@/shared/api/endpoints";
import { queryKeys } from "@/shared/api/query-keys";
import type { TransactionOperationType, InvestmentTransactionWritePayload } from "@/shared/api/types";
import { getUserFacingApiError } from "@/shared/lib/api-error-message";
import { formatRub, normalizeAmountForApi, parseDecimal } from "@/shared/lib/format";
import { AmountInput } from "@/shared/ui/AmountInput";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { GlassSurface } from "@/shared/ui/GlassSurface";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";
import { PageHeader } from "@/shared/ui/PageHeader";
import { ValidationBanner } from "@/shared/ui/ValidationBanner";
import { Button } from "@/shared/ui/Button";

import styles from "./TransactionFormPage.module.css";

function toDatetimeLocalValue(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultExecutedLocal(): string {
  return toDatetimeLocalValue(new Date().toISOString());
}

export function TransactionFormPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const matchNew = useMatch({ path: "/transactions/new", end: true });
  const isCreate = Boolean(matchNew);
  const { transactionId } = useParams();
  const editId = isCreate ? null : Number(transactionId);

  const fundsQ = useQuery({ queryKey: queryKeys.funds, queryFn: getFunds });
  const txQ = useQuery({
    queryKey: [...queryKeys.transactions, "detail", editId],
    queryFn: () => getTransaction(editId as number),
    enabled: !isCreate && Number.isFinite(editId) && (editId as number) > 0,
  });

  const activeFunds = useMemo(() => (fundsQ.data ?? []).filter((f) => f.is_active), [fundsQ.data]);

  const [fundId, setFundId] = useState<number | null>(null);
  const [operation, setOperation] = useState<TransactionOperationType>("buy");
  const [quantity, setQuantity] = useState(1);
  const [priceStr, setPriceStr] = useState("");
  const [executedLocal, setExecutedLocal] = useState(defaultExecutedLocal);
  const [note, setNote] = useState("");
  const [banner, setBanner] = useState<{ variant: "success" | "error"; title: string; message: string } | null>(null);

  useEffect(() => {
    if (!isCreate || activeFunds.length === 0 || fundId !== null) return;
    setFundId(activeFunds[0].id);
    setPriceStr(String(activeFunds[0].price));
  }, [isCreate, activeFunds, fundId]);

  useEffect(() => {
    if (!isCreate || fundId == null) return;
    const f = activeFunds.find((x) => x.id === fundId);
    if (f) setPriceStr(String(f.price));
  }, [fundId, isCreate, activeFunds]);

  useEffect(() => {
    const row = txQ.data;
    if (!row || isCreate) return;
    setFundId(row.fund_id);
    setOperation(row.operation_type);
    setQuantity(row.quantity);
    setPriceStr(String(row.price_per_unit));
    setNote(row.note ?? "");
    setExecutedLocal(toDatetimeLocalValue(row.executed_at));
  }, [txQ.data, isCreate]);

  const totalPreview = useMemo(() => {
    const p = parseDecimal(priceStr);
    if (!Number.isFinite(p) || quantity < 1) return null;
    const raw = (p * quantity).toFixed(2);
    const n = normalizeAmountForApi(raw);
    return n;
  }, [priceStr, quantity]);

  const invalidateAll = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: queryKeys.portfolio }),
      qc.invalidateQueries({ queryKey: queryKeys.rebalance }),
      qc.invalidateQueries({ queryKey: queryKeys.transactions }),
      qc.invalidateQueries({ queryKey: queryKeys.topupHistory }),
      qc.invalidateQueries({ queryKey: queryKeys.funds }),
    ]);
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (fundId == null) throw new Error("Выберите фонд");
      const total = normalizeAmountForApi(totalPreview ?? "");
      if (!total) throw new Error("Проверьте цену и количество — не удалось посчитать сумму сделки");
      const priceNorm = normalizeAmountForApi(priceStr);
      if (!priceNorm) throw new Error("Укажите цену за единицу");
      let executedAtIso: string;
      try {
        const d = new Date(executedLocal);
        if (Number.isNaN(d.getTime())) throw new Error("bad");
        executedAtIso = d.toISOString();
      } catch {
        throw new Error("Укажите корректную дату и время");
      }
      const base: InvestmentTransactionWritePayload = {
        fund_id: fundId,
        operation_type: operation,
        quantity,
        price_per_unit: priceNorm,
        total_amount: total,
        executed_at: executedAtIso,
        note: note.trim() ? note.trim() : null,
      };
      if (isCreate) {
        return createTransaction(base);
      }
      return updateTransaction(editId as number, base);
    },
    onSuccess: async () => {
      await invalidateAll();
      setBanner({ variant: "success", title: "Сохранено", message: "Портфель и ребаланс обновлены по новым данным." });
    },
    onError: (err: unknown) => {
      const e = getUserFacingApiError(err);
      setBanner({ variant: "error", title: e.title, message: e.message });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => deleteTransaction(editId as number),
    onSuccess: async () => {
      await invalidateAll();
      navigate("/transactions");
    },
    onError: (err: unknown) => {
      const e = getUserFacingApiError(err);
      setBanner({ variant: "error", title: e.title, message: e.message });
    },
  });

  useEffect(() => {
    if (!banner || banner.variant !== "success") return;
    const t = window.setTimeout(() => setBanner(null), 5000);
    return () => window.clearTimeout(t);
  }, [banner]);

  if (fundsQ.isPending || (!isCreate && txQ.isPending)) {
    return (
      <div>
        <PageHeader title={isCreate ? "Новая сделка" : "Сделка"} subtitle="Загрузка…" />
        <LoadingBlock label="Загружаем данные…" />
      </div>
    );
  }

  if (fundsQ.isError) {
    const e = getUserFacingApiError(fundsQ.error);
    return (
      <div>
        <PageHeader title={isCreate ? "Новая сделка" : "Сделка"} subtitle="Ошибка" />
        <ErrorBlock title={e.title} message={e.message} onRetry={() => void fundsQ.refetch()} />
      </div>
    );
  }

  if (!isCreate && txQ.isError) {
    const e = getUserFacingApiError(txQ.error);
    return (
      <div>
        <PageHeader title="Сделка" subtitle="Ошибка" />
        <ErrorBlock title={e.title} message={e.message} onRetry={() => void txQ.refetch()} />
      </div>
    );
  }

  if (!isCreate && !Number.isFinite(editId)) {
    return (
      <div>
        <PageHeader title="Сделка" subtitle="Некорректный адрес" />
        <ErrorBlock title="Не найдено" message="Проверьте ссылку." />
      </div>
    );
  }

  const busy = saveMutation.isPending || deleteMutation.isPending;

  const onDelete = () => {
    if (!window.confirm("Удалить эту сделку? Позиции портфеля будут пересчитаны.")) return;
    deleteMutation.mutate();
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setBanner(null);
    saveMutation.mutate();
  };

  const title = isCreate ? "Новая сделка" : "Редактирование";
  const subtitle = isCreate ? "Данные попадут в журнал и пересчитают портфель" : `Сделка #${editId}`;

  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} />
      <p className={styles.backWrap}>
        <Link className={styles.backLink} to="/transactions">
          ← К списку сделок
        </Link>
      </p>

      {banner ? (
        <div className={styles.bannerWrap}>
          <ValidationBanner variant={banner.variant} title={banner.title} message={banner.message} />
        </div>
      ) : null}

      <GlassSurface variant="strong" className={styles.formShell}>
        <form className={styles.form} onSubmit={onSubmit}>
        <div className={styles.selectWrap}>
          <span className={styles.label}>Фонд</span>
          <select
            className={styles.select}
            value={fundId ?? ""}
            disabled={busy}
            onChange={(e) => setFundId(Number(e.target.value))}
            required
          >
            <option value="" disabled>
              {activeFunds.length ? "Выберите фонд" : "Нет активных фондов"}
            </option>
            {activeFunds.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.ticker})
              </option>
            ))}
          </select>
        </div>

        <div className={styles.segment}>
          <span className={styles.label}>Операция</span>
          <div className={styles.segmentBtns}>
            <button
              type="button"
              className={[styles.segmentBtn, operation === "buy" ? styles.segmentBtnActive : ""].join(" ")}
              disabled={busy}
              onClick={() => setOperation("buy")}
            >
              Покупка
            </button>
            <button
              type="button"
              className={[styles.segmentBtn, operation === "sell" ? styles.segmentBtnActive : ""].join(" ")}
              disabled={busy}
              onClick={() => setOperation("sell")}
            >
              Продажа
            </button>
          </div>
        </div>

        <div className={styles.row2}>
          <div className={styles.selectWrap}>
            <label className={styles.label} htmlFor="tx-qty">
              Количество (шт.)
            </label>
            <input
              id="tx-qty"
              className={styles.numberField}
              type="number"
              min={1}
              step={1}
              value={quantity}
              disabled={busy}
              onChange={(e) => setQuantity(Math.max(1, Number.parseInt(e.target.value, 10) || 1))}
            />
          </div>
          <AmountInput id="tx-price" label="Цена за шт." value={priceStr} disabled={busy} onChange={setPriceStr} />
        </div>

        <div className={styles.totalBox}>
          <p className={styles.totalK}>Сумма сделки (кол-во × цена)</p>
          <p className={styles.totalV}>{totalPreview ? formatRub(totalPreview) : "—"}</p>
        </div>

        <div className={styles.selectWrap}>
          <label className={styles.label} htmlFor="tx-when">
            Дата и время
          </label>
          <input
            id="tx-when"
            className={styles.select}
            type="datetime-local"
            value={executedLocal}
            disabled={busy}
            onChange={(e) => setExecutedLocal(e.target.value)}
            required
          />
        </div>

        <div className={styles.selectWrap}>
          <label className={styles.label} htmlFor="tx-note">
            Комментарий (необязательно)
          </label>
          <textarea id="tx-note" className={styles.textarea} value={note} disabled={busy} onChange={(e) => setNote(e.target.value)} />
        </div>

        <div className={styles.actions}>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Сохранение…" : "Сохранить"}
          </Button>
          {!isCreate ? (
            <Button type="button" variant="ghost" disabled={busy} onClick={onDelete}>
              {deleteMutation.isPending ? "Удаление…" : "Удалить"}
            </Button>
          ) : null}
        </div>
        </form>
      </GlassSurface>
    </div>
  );
}
