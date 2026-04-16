import { useEffect } from "react";

import { getTelegramWebApp } from "@/lib/telegram";

export function useTelegramViewport() {
  useEffect(() => {
    const tg = getTelegramWebApp();
    if (!tg) return;
    tg.ready();
    tg.expand();
  }, []);
}
