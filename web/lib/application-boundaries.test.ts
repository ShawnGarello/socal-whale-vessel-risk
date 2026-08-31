import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import EsriAttribution from "../components/EsriAttribution";
import nextConfig from "../next.config";
import packageJson from "../package.json";

const mapShellSource = readFileSync(
  new URL("../components/MapShell.tsx", import.meta.url),
  "utf8",
);
const mapFrameSource = readFileSync(
  new URL("../components/ArcgisMapFrame.tsx", import.meta.url),
  "utf8",
);
const mapFrameStyles = readFileSync(
  new URL("../components/ArcgisMapFrame.module.css", import.meta.url),
  "utf8",
);
const layoutSource = readFileSync(
  new URL("../app/layout.tsx", import.meta.url),
  "utf8",
);
const faviconSource = readFileSync(
  new URL("../public/favicon.svg", import.meta.url),
  "utf8",
);

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

  it("declares a shipped favicon instead of triggering a missing default request", () => {
    expect(layoutSource).toContain('icon: "/favicon.svg"');
    expect(faviconSource).toMatch(/^<svg[^>]+viewBox="0 0 32 32"/);
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

describe("Esri attribution boundary", () => {
  it("renders the required application-level attribution as accessible text", () => {
    const markup = renderToStaticMarkup(createElement(EsriAttribution));

    expect(markup).toContain(">Powered by Esri</p>");
  });

  it("keeps fallback attribution until the SDK reports its attribution available", () => {
    expect(mapShellSource).toContain(
      "{!sdkAttributionAvailable && <EsriAttribution />}",
    );
    expect(mapFrameSource).toContain("onSdkAttributionChange(true);");
    expect(mapFrameSource.match(/onSdkAttributionChange\(false\);/g)).toHaveLength(2);
  });

  it("leaves the SDK automatic attribution enabled for ready maps", () => {
    expect(mapFrameSource).not.toMatch(/\bhideAttribution\s*=|hide-attribution\s*=/);
  });

  it("clips the interactive SDK surface to the map frame", () => {
    expect(mapFrameStyles).toMatch(/\.frame\s*\{[\s\S]*?contain:\s*paint;/);
  });
});
