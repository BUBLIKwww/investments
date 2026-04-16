import { NavLink } from "react-router-dom";

import styles from "./BottomNav.module.css";

const items = [
  { to: "/", label: "Главная", end: true, icon: IconHome },
  { to: "/transactions", label: "Сделки", end: false, icon: IconChart },
  { to: "/topup", label: "Пополнение", end: false, icon: IconPlus },
  { to: "/history", label: "История", end: false, icon: IconHistory },
  { to: "/settings", label: "Настройки", end: false, icon: IconGear },
] as const;

export function BottomNav() {
  return (
    <nav className={styles.nav} aria-label="Основная навигация">
      <div className={styles.shell}>
        <div className={styles.inner}>
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => [styles.item, isActive ? styles.itemActive : ""].join(" ")}
            >
              <span className={styles.icon} aria-hidden="true">
                <item.icon />
              </span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}

function IconHome() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconChart() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M4 19h16M7 15V9m5 6V5m5 10v-4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M12 5v14M5 12h14"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconHistory() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M12 7v6l4 2"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 21a9 9 0 1 0-9-9"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </svg>
  );
}

function IconGear() {
  return (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <path
        d="M19.4 15a7.9 7.9 0 0 0 .1-1l2-1.2-2-3.4-2.3.5a8.1 8.1 0 0 0-1.7-1l-.3-2.4H10.8l-.3 2.4a8.1 8.1 0 0 0-1.7 1L6.5 8.4l-2 3.4 2 1.2a7.9 7.9 0 0 0 0 2l-2 1.2 2 3.4 2.3-.5a8.1 8.1 0 0 0 1.7 1l.3 2.4h4.6l.3-2.4a8.1 8.1 0 0 0 1.7-1l2.3.5 2-3.4-2-1.2Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        opacity="0.9"
      />
    </svg>
  );
}
