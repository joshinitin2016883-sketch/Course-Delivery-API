import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // The API's CORS_ORIGINS allows http://localhost:5173, so fail rather than quietly use another port.
  server: { port: 5173, strictPort: true },
});
