import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frontendPort = Number(env.FRONTEND_PORT || env.VITE_PORT || 2734);

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: frontendPort,
    },
    preview: {
      host: "0.0.0.0",
      port: frontendPort,
    },
  };
});
