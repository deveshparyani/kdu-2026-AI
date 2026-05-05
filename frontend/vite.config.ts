// Why this file exists:
// Vite reads this config when it starts the local React dev server.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()]
});
