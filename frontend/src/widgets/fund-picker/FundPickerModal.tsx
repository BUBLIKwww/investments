import { useEffect } from "react";

import type { FundRead } from "@/shared/api/types";
import { formatRub } from "@/shared/lib/format";
import { Button } from "@/shared/ui/Button";
import { ErrorBlock } from "@/shared/ui/ErrorBlock";
import { LoadingBlock } from "@/shared/ui/LoadingBlock";

import styles from "./FundPickerModal.module.css";

type FundPickerModalProps = {
  open: boolean;
  funds: FundRead[] | undefined;
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  selectedFundId?: number;
  onClose: () => void;
  onSelect: (fundId: number) => void;
  onRetry?: () => void;
};

export function FundPickerModal({
  open,
  funds,
  isLoading,
  isError,
  errorMessage,
  selectedFundId,
  onClose,
  onSelect,
  onRetry,
}: FundPickerModalProps) {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className={styles.backdrop} role="presentation" onMouseDown={onClose}>
      <div
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-labelledby="fund-picker-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className={styles.head}>
          <h2 id="fund-picker-title" className={styles.title}>
            Выбор фонда
          </h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>
        <div className={styles.body}>
          {isLoading ? <LoadingBlock label="Загрузка фондов…" /> : null}
          {isError ? (
            <ErrorBlock
              title="Не удалось загрузить фонды"
              message={errorMessage ?? "Ошибка"}
              onRetry={onRetry}
            />
          ) : null}
          {!isLoading && !isError && (!funds || funds.length === 0) ? (
            <p style={{ margin: 8, color: "var(--muted)", fontSize: 13 }}>Список фондов пуст.</p>
          ) : null}
          {!isLoading && !isError && funds?.length
            ? funds.map((f) => {
                const selected = f.id === selectedFundId;
                return (
                  <button
                    key={f.id}
                    type="button"
                    className={[styles.row, selected ? styles.rowSelected : ""].filter(Boolean).join(" ")}
                    onClick={() => {
                      onSelect(f.id);
                      onClose();
                    }}
                  >
                    <span className={styles.rowTitle}>{f.name}</span>
                    <span className={styles.rowMeta}>
                      <span>{f.ticker}</span>
                      <span>·</span>
                      <span>{formatRub(f.price)}</span>
                      <span>·</span>
                      <span>лот {f.lot}</span>
                      {!f.is_active ? (
                        <span className={[styles.badge, styles.badgeOff].join(" ")}>неактивен</span>
                      ) : null}
                    </span>
                  </button>
                );
              })
            : null}
          {!isLoading && !isError && funds?.length ? (
            <div style={{ marginTop: 10 }}>
              <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                Отмена
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
