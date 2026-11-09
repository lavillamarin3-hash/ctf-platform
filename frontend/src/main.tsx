import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import FreshApp from "./fresh/App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {import.meta.env.VITE_FRESH_INSTALL === "true" ? <FreshApp /> : <App />}
  </StrictMode>,
);

