import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getTelegramWebApp } from "@/lib/telegram";

export type ThemeMode = "light" | "dark" | "system";

type ThemeContextValue = {
  mode: ThemeMode;
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function resolveScheme(mode: ThemeMode): "light" | "dark" {
  if (mode !== "system") return mode;
  const tg = getTelegramWebApp();
  if (tg?.colorScheme) return tg.colorScheme;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("system");
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolveScheme("system"));

  const applyDomTheme = useCallback((scheme: "light" | "dark") => {
    document.documentElement.dataset.theme = scheme;
    document.documentElement.style.colorScheme = scheme;
  }, []);

  useEffect(() => {
    applyDomTheme(resolveScheme(mode));
    setResolved(resolveScheme(mode));
  }, [applyDomTheme, mode]);

  useEffect(() => {
    const tg = getTelegramWebApp();
    if (!tg || mode !== "system") return;

    const sync = () => {
      const next = resolveScheme("system");
      setResolved(next);
      applyDomTheme(next);
    };

    sync();
    tg.onEvent("themeChanged", sync);
    return () => tg.offEvent("themeChanged", sync);
  }, [applyDomTheme, mode]);

  useEffect(() => {
    if (mode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (getTelegramWebApp()) return;
      const next = resolveScheme("system");
      setResolved(next);
      applyDomTheme(next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [applyDomTheme, mode]);

  const setMode = useCallback(
    (next: ThemeMode) => {
      setModeState(next);
      const scheme = resolveScheme(next);
      setResolved(scheme);
      applyDomTheme(scheme);
    },
    [applyDomTheme],
  );

  const value = useMemo(() => ({ mode, resolved, setMode }), [mode, resolved, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
