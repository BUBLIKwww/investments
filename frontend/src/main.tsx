import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/App";
import { AppProviders } from "@/app/providers/AppProviders";
import { useTelegramViewport } from "@/hooks/useTelegramViewport";

import "@/styles/global.css";

function Root() {
  useTelegramViewport();
  return <App />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders>
      <Root />
    </AppProviders>
  </StrictMode>,
);
