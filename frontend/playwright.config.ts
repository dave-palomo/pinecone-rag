import { defineConfig, devices } from "@playwright/test";

const useExternalServer = process.env.PLAYWRIGHT_EXTERNAL_SERVER === "1";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: useExternalServer
    ? undefined
    : {
        command:
          "node ./node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --webpack",
        url: "http://127.0.0.1:3000",
        reuseExistingServer: true,
        env: {
          NEXT_DIST_DIR: ".next-e2e",
          NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:3000/api-test",
        },
      },
});
