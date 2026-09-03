import { describe, expect, it } from "vitest";
import { assertExpectedVsrFeatureCount, VSR_SOURCE } from "./vsr-source";

describe("VSR source configuration", () => {
  it("identifies the publisher item and exact feature service", () => {
    expect(VSR_SOURCE.itemId).toBe("b400c7f418b04dc5a9d7ce5015adae32");
    expect(VSR_SOURCE.serviceUrl).toBe(
      "https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0",
    );
  });

  it("uses the accepted filter exactly", () => {
    expect(VSR_SOURCE.definitionExpression).toBe("FID = 126");
    expect(VSR_SOURCE.expectedFeatureCount).toBe(1);
  });

  it("retains the publisher attribution and complete use warning", () => {
    expect(VSR_SOURCE.attribution).toBe(
      "Created by Danielle Alvarez, with CMSF and BWBS.",
    );
    expect(VSR_SOURCE.disclaimer).toContain("should not be used for navigation");
    expect(VSR_SOURCE.disclaimer).toContain("Mariners should operate");
    expect(VSR_SOURCE.disclaimer).toContain("may not be comprehensive");
    expect(VSR_SOURCE.disclaimer).toContain("absence of a VSR Zone");
    expect(VSR_SOURCE.disclaimer).toContain("Area to Be Avoided (ATBA)");
    expect(VSR_SOURCE.disclaimer).toContain("Traffic Separation Scheme (TSS)");
  });

  it("rejects an empty or changed filtered response", () => {
    expect(() => assertExpectedVsrFeatureCount(0)).toThrow(/received 0/);
    expect(() => assertExpectedVsrFeatureCount(2)).toThrow(/received 2/);
    expect(() => assertExpectedVsrFeatureCount(1)).not.toThrow();
  });
});
