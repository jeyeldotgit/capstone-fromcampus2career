import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    hookTimeout: 60000,
    include: [
      "src/__tests__/schema-prepared-intelligence.test.ts",
      "src/seeds/__tests__/**/*.test.ts",
    ],
    testTimeout: 60000,
  },
});
