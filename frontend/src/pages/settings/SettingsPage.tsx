import { useTheme, type ThemeMode } from "@/hooks/useTheme";
import { PageHeader } from "@/shared/ui/PageHeader";

import { StrategyEditor } from "./StrategyEditor";
import styles from "./SettingsPage.module.css";

export function SettingsPage() {
  const { mode, setMode } = useTheme();

  return (
    <div>
      <PageHeader title="Настройки" subtitle="Стратегия, тема и будущие разделы" />
      <div className={styles.stack}>
        <StrategyEditor />

        <section className={styles.section} aria-label="Тема оформления">
          <h2 className={styles.sectionTitle}>Тема</h2>
          <p className={styles.muted}>По умолчанию синхронизируется с темой Telegram.</p>
          <div className={styles.row}>
            <span className={styles.muted}>Режим</span>
            <div className={styles.segmented} role="group" aria-label="Выбор темы">
              {(
                [
                  { id: "system" as const, label: "Системная" },
                  { id: "light" as const, label: "Светлая" },
                  { id: "dark" as const, label: "Тёмная" },
                ] satisfies { id: ThemeMode; label: string }[]
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={[styles.segBtn, mode === item.id ? styles.segBtnActive : ""].join(" ")}
                  onClick={() => setMode(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className={styles.section} aria-label="Уведомления">
          <h2 className={styles.sectionTitle}>Уведомления</h2>
          <div className={styles.row}>
            <div>
              <div className={styles.itemTitle}>Напоминания о пополнении</div>
              <p className={styles.muted}>Скоро: расписание и каналы доставки.</p>
            </div>
            <span className={styles.muted}>—</span>
          </div>
        </section>

        <section className={styles.section} aria-label="Безопасность">
          <h2 className={styles.sectionTitle}>Безопасность</h2>
          <div className={styles.row}>
            <div>
              <div className={styles.itemTitle}>Сессии и доступы</div>
              <p className={styles.muted}>Скоро: список устройств и политика доступа к данным.</p>
            </div>
            <span className={styles.muted}>—</span>
          </div>
        </section>
      </div>
    </div>
  );
}
