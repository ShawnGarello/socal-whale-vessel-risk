import { describe, expect, it } from "vitest";
import nextConfig from "../next.config";
import packageJson from "../package.json";

describe("static application boundaries", () => {
  it("keeps the production build as a directory-friendly static export", () => {
    expect(nextConfig).toMatchObject({
      output: "export",
      trailingSlash: true,
      images: { unoptimized: true },
    });
  });

  it("does not expose a Node production-server command", () => {
    expect(packageJson.scripts).not.toHaveProperty("start");
    expect(packageJson.scripts.build).toBe("next build");
  });
});

describe("clean-checkout verification", () => {
  it("generates Next route types before standalone TypeScript checking", () => {
    expect(packageJson.scripts.typegen).toBe("next typegen");
    expect(packageJson.scripts.typecheck).toBe(
      "npm run typegen && npm run typecheck:generated",
    );
    expect(packageJson.scripts["typecheck:generated"]).toBe("tsc --noEmit");
  });

  it("runs clean-checkout gates in their required order", () => {
    expect(packageJson.scripts["verify:clean"].split(" && ")).toEqual([
      "npm ci",
      "npm run typegen",
      "npm run format:check",
      "npm run lint",
      "npm run typecheck:generated",
      "npm test",
      "npm run build",
    ]);
  });
});
