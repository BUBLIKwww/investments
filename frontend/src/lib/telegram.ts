export type TelegramColorScheme = "light" | "dark";

export interface TelegramThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
}

export interface TelegramWebApp {
  ready: () => void;
  expand: () => void;
  colorScheme: TelegramColorScheme;
  themeParams: TelegramThemeParams;
  onEvent: (event: "themeChanged", handler: () => void) => void;
  offEvent: (event: "themeChanged", handler: () => void) => void;
}

export interface TelegramNamespace {
  WebApp: TelegramWebApp;
}

declare global {
  interface Window {
    Telegram?: TelegramNamespace;
  }
}

export function getTelegramWebApp(): TelegramWebApp | undefined {
  return window.Telegram?.WebApp;
}
