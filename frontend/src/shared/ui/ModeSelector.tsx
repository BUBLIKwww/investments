import type { TopupMode } from "@/shared/api/types";

import styles from "./ModeSelector.module.css";

const OPTIONS: { id: TopupMode; title: string; description: string }[] = [
  {
    id: "strict",
    title: "Строго",
    description: "Делим сумму по целевым долям и покупаем целые лоты. Остаток остаётся наличными.",
  },
  {
    id: "maximize",
    title: "Максимум",
    description: "Сначала как в строгом режиме, затем пытаемся докупить самые дешёвые доступные лоты за счёт остатка.",
  },
  {
    id: "smart",
    title: "Умный",
    description: "Если портфель уже есть — слегка смещаем распределение в сторону недовложенных категорий. Если портфеля нет — как строгий.",
  },
];

type ModeSelectorProps = {
  value: TopupMode;
  onChange: (mode: TopupMode) => void;
  disabled?: boolean;
};

export function ModeSelector({ value, onChange, disabled = false }: ModeSelectorProps) {
  return (
    <div className={styles.wrap} role="radiogroup" aria-label="Режим расчёта">
      {OPTIONS.map((opt) => {
        const active = opt.id === value;
        return (
          <button
            key={opt.id}
            type="button"
            disabled={disabled}
            className={[styles.option, active ? styles.active : "", active ? styles.on : ""].filter(Boolean).join(" ")}
            onClick={() => onChange(opt.id)}
            aria-checked={active}
            role="radio"
          >
            <div className={styles.titleRow}>
              <p className={styles.title}>{opt.title}</p>
              <span className={styles.dot} aria-hidden="true" />
            </div>
            <p className={styles.desc}>{opt.description}</p>
          </button>
        );
      })}
    </div>
  );
}
