import "@fontsource-variable/geist";
import "@fontsource-variable/outfit";
import "@fontsource-variable/playfair-display";
import "@fontsource-variable/cinzel";
import "@fontsource-variable/roboto-slab";
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource/gloria-hallelujah/400.css";
import "@fontsource/ribeye/400.css";
import "@fontsource/rowdies/400.css";
import "@fontsource/goudy-bookletter-1911/400.css";
import "@fontsource/bai-jamjuree/400.css";
import "@fontsource/bai-jamjuree/700.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "@tanstack/react-router";
import { router } from "@/src/router";
import "@/src/styles.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

createRoot(rootElement).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
