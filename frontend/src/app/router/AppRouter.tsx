import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/app/layouts/AppLayout";
import { CalculationPage } from "@/pages/calculation/CalculationPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { FundDetailsPage } from "@/pages/fund-details/FundDetailsPage";
import { HistoryPage } from "@/pages/history/HistoryPage";
import { RebalancePage } from "@/pages/rebalance/RebalancePage";
import { SettingsPage } from "@/pages/settings/SettingsPage";
import { TopupPage } from "@/pages/topup/TopupPage";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="topup" element={<TopupPage />} />
        <Route path="calculation" element={<CalculationPage />} />
        <Route path="rebalance" element={<RebalancePage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="funds/:fundId" element={<FundDetailsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
