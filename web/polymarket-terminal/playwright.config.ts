import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(webDir, "../..");
const pythonPath = ["fincept-qt/scripts", "fincept-qt/scripts/algo_trading"].join(path.delimiter);

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:4177",
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command:
        "python -m uvicorn polymarket_web_api.app:create_app --factory --host 127.0.0.1 --port 8765",
      cwd: repoRoot,
      env: {
        PYTHONPATH: pythonPath,
        POLYMARKET_WEB_DB: ".polymarket-web.sqlite"
      },
      reuseExistingServer: false,
      timeout: 30_000,
      url: "http://127.0.0.1:8765/api/bot/status"
    },
    {
      command: "npm run dev",
      cwd: webDir,
      env: {
        VITE_POLYMARKET_API_BASE: "http://127.0.0.1:8765"
      },
      reuseExistingServer: false,
      timeout: 30_000,
      url: "http://127.0.0.1:4177"
    }
  ]
});
