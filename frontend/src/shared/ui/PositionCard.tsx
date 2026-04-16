import { formatPercent, formatRub, parseDecimal } from "@/shared/lib/format";
import { GlassSurface } from "@/shared/ui/GlassSurface";

import styles from "./PositionCard.module.css";

type PositionCardProps = {
  title: string;
  invested: string;
  currentWeightPercent: string;
  targetWeightPercent: string;
  badge?: string;
};

export function PositionCard({ title, invested, currentWeightPercent, targetWeightPercent, badge }: PositionCardProps) {
  const cur = parseDecimal(currentWeightPercent);
  const tgt = parseDecimal(targetWeightPercent);
  const delta = Number.isFinite(cur) && Number.isFinite(tgt) ? cur - tgt : Number.NaN;
  const deltaCls = Number.isFinite(delta) ? (delta > 0 ? styles.deltaPos : delta < 0 ? styles.deltaNeg : "") : "";

  return (
    <GlassSurface className={styles.inner}>
      <div className={styles.top}>
        <p className={styles.name}>{title}</p>
        {badge ? <span className={styles.pill}>{badge}</span> : null}
      </div>
      <div className={styles.grid}>
        <div>
          <p className={styles.k}>Вложено</p>
          <p className={styles.v}>{formatRub(invested)}</p>
        </div>
        <div>
          <p className={styles.k}>Текущая доля</p>
          <p className={styles.v}>{formatPercent(currentWeightPercent)}</p>
        </div>
        <div>
          <p className={styles.k}>Целевая доля</p>
          <p className={styles.v}>{formatPercent(targetWeightPercent)}</p>
        </div>
        <div>
          <p className={styles.k}>Отклонение</p>
          <p className={`${styles.v} ${deltaCls}`}>
            {Number.isFinite(delta) ? `${delta > 0 ? "+" : ""}${delta.toFixed(1).replace(".", ",")} п.п.` : "—"}
          </p>
        </div>
      </div>
    </GlassSurface>
  );
}
