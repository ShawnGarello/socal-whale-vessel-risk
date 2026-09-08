import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ExposureLayerControl from "../components/ExposureLayerControl";
import {
  EXPOSURE_SOURCE,
  assertExpectedExposureFeatureCount,
  validateExposureManifest,
  verifyExposureLayerBytes,
} from "./exposure-source";
import type { MapLayerState } from "./map-layer-state";

function validManifest(): Record<string, unknown> {
  return {
    contract: "relative_exposure_display_manifest_v1",
    processing_version: "1.0.0",
    dataset_contract: "relative_exposure_display_v1",
    output: {
      name: "relative-exposure.geojson",
      media_type: "application/geo+json",
      feature_count: 2793,
      unique_cell_count: 2793,
      sha256: EXPOSURE_SOURCE.displaySha256,
    },
    geometry: {
      display_crs: "EPSG:4326",
      meaning: "exact receiver-domain-qualified 5 km water geometry",
      vsr_geometry: "not_included",
    },
    results: {
      contract: "relative_exposure_application_results_v1",
      results_id: EXPOSURE_SOURCE.resultsId,
      sha256: EXPOSURE_SOURCE.resultsSha256,
    },
    classification: {
      product: {
        available: true,
        percentile: 0.9,
        reference: "all_valid",
        field: "product_high_p90",
        threshold: 0.22859788468419606,
      },
      log_traffic: {
        available: true,
        percentile: 0.9,
        reference: "all_valid",
        field: "log_traffic_high_p90",
        threshold: 0.015312992704808721,
      },
    },
  };
}

describe("relative-exposure display source", () => {
  it("pins the exact display, manifest, results, and feature identities", () => {
    expect(EXPOSURE_SOURCE.displaySha256).toBe(
      "1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb",
    );
    expect(EXPOSURE_SOURCE.manifestSha256).toBe(
      "0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0",
    );
    expect(EXPOSURE_SOURCE.expectedFeatureCount).toBe(2793);
    expect(() => assertExpectedExposureFeatureCount(2792)).toThrow(/2792/);
  });

  it("accepts only the supported manifest and exact results pairing", () => {
    expect(() => validateExposureManifest(validManifest())).not.toThrow();
    const mismatched = validManifest();
    (mismatched.results as Record<string, unknown>).results_id =
      "exposure-results-mismatch";
    expect(() => validateExposureManifest(mismatched)).toThrow(/results_id/);
  });

  it("rejects malformed and semantically mismatched manifests before display", async () => {
    const bytes = new TextEncoder().encode("{}").buffer;
    await expect(
      verifyExposureLayerBytes(
        bytes,
        async () => ({
          ok: true,
          status: 200,
          arrayBuffer: async () => new TextEncoder().encode("not json").buffer,
        }),
        null,
      ),
    ).rejects.toThrow(/malformed JSON/);

    const mismatch = validManifest();
    (mismatch.output as Record<string, unknown>).feature_count = 12;
    await expect(
      verifyExposureLayerBytes(
        bytes,
        async () => ({
          ok: true,
          status: 200,
          arrayBuffer: async () =>
            new TextEncoder().encode(JSON.stringify(mismatch)).buffer,
        }),
        null,
      ),
    ).rejects.toThrow(/feature_count/);
  });

  it("renders an accessible default layer and plainly visible method sensitivity", () => {
    const ready: MapLayerState = {
      status: "ready",
      visible: true,
      featureCount: 2793,
      warning: null,
    };
    const markup = renderToStaticMarkup(
      createElement(ExposureLayerControl, {
        state: ready,
        method: "product",
        checksumVerified: true,
        onVisibilityChange: () => undefined,
        onMethodChange: () => undefined,
      }),
    );
    expect(markup).toContain("Relative exposure");
    expect(markup).toContain("Proportional product (primary)");
    expect(markup).toContain("Log-traffic sensitivity");
    expect(markup).toContain("release-relative index (0–1)");
    expect(markup).toContain("not the analytical high-exposure threshold");
    expect(markup).toContain("checked");
  });
});
