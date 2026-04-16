import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { BottomNav } from "@/widgets/bottom-nav/BottomNav";

import styles from "./AppLayout.module.css";

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const isFundDetails = location.pathname.startsWith("/funds/");

  return (
    <div className={[styles.shell, isFundDetails ? styles.shellDense : ""].filter(Boolean).join(" ")}>
      <div className={styles.frame}>
        {isFundDetails ? (
          <div className={styles.topRow}>
            <button type="button" className={styles.back} onClick={() => navigate(-1)}>
              Назад
            </button>
          </div>
        ) : null}
        <Outlet />
      </div>
      {!isFundDetails ? <BottomNav /> : null}
    </div>
  );
}
