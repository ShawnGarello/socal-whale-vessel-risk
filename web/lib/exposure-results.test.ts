import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ExposureResultsPanel from "../components/ExposureResultsPanel";
import {
  EXPOSURE_RESULTS_ID,
  EXPOSURE_RESULTS_SHA256,
  buildExposureResultsViewModel,
  parseExposureResults,
  parseExposureResultsText,
  type ExposureResults,
} from "./exposure-results";
import { loadExposureResults } from "./load-exposure-results";

const resultText = readFileSync(
  new URL("../../results/exposure-results.v1.json", import.meta.url),
  "utf8",
);

function resultObject(): Record<string, unknown> {
  return JSON.parse(resultText) as Record<string, unknown>;
}

function clonedResults(): ExposureResults {
  return structuredClone(parseExposureResultsText(resultText));
}

describe("exposure results contract", () => {
  it("accepts the exact supported generated results and build-time checksum", () => {
    const parsed = parseExposureResultsText(resultText);
    const loaded = loadExposureResults();
    expect(parsed.results_id).toBe(EXPOSURE_RESULTS_ID);
    expect(loaded).toMatchObject({ ok: true, sha256: EXPOSURE_RESULTS_SHA256 });
  });

  it("rejects an incompatible version, identity, and missing required field", () => {
    const wrongVersion = resultObject();
    wrongVersion.schema_version = 2;
    expect(() => parseExposureResults(wrongVersion)).toThrow(/schema version 1/);

    const wrongIdentity = resultObject();
    wrongIdentity.results_id = "exposure-results-changed";
    expect(() => parseExposureResults(wrongIdentity)).toThrow(/identity/);

    const missing = resultObject();
    const scenarios = missing.scenarios as Record<string, Record<string, unknown>>;
    delete scenarios["5km_product"].integrated_exposure;
    expect(() => parseExposureResults(missing)).toThrow(/integrated_exposure/);
  });

  it("selects the generated strings without transcribing or reformatting values", () => {
    const results = clonedResults();
    const view = buildExposureResultsViewModel(results);
    expect(view.primary.insideShare).toBe(
      results.scenarios["5km_product"].integrated_exposure.presentation
        .inside_share_percent_1dp,
    );
    expect(view.primary.p90InsideAreaShare).toBe("98.5%");
    expect(view.sensitivity.insideShare).toBe("74.9%");
    expect(view.formulaInsideChangePercentagePoints).toBe("-17.2741");
    expect(view.thresholdRows.map((row) => row.percentile)).toEqual([
      "p80",
      "p90",
      "p95",
    ]);
  });

  it("preserves legitimate zero, null, and excluded-area semantics", () => {
    const results = clonedResults();
    const primary = results.scenarios["5km_product"] as {
      integrated_exposure: ExposureResults["scenarios"]["5km_product"]["integrated_exposure"];
      high_exposure: ExposureResults["scenarios"]["5km_product"]["high_exposure"];
    };
    primary.integrated_exposure = {
      ...primary.integrated_exposure,
      total_qualified: 0,
      inside_vsr: 0,
      outside_vsr: 0,
      inside_share: null,
      outside_share: null,
      presentation: {
        inside_share_percent_1dp: null,
        outside_share_percent_1dp: null,
      },
    };
    const p90 = primary.high_exposure.all_valid[1] as ExposureThresholdMutable;
    p90.available = false;
    p90.threshold = null;
    p90.selected_water_area_km2 = null;
    p90.inside_share_of_selected_water = null;
    p90.outside_share_of_selected_water = null;
    p90.unavailable_reason = "all valid intensities are zero";
    p90.presentation = {
      inside_share_percent_1dp: null,
      outside_share_percent_1dp: null,
      selected_water_area_1dp: null,
      threshold_4dp: null,
    };

    const view = buildExposureResultsViewModel(parseExposureResults(results));
    expect(view.primary.insideShare).toMatch(/Not available/);
    expect(view.primary.p90Available).toBe(false);
    expect(view.limitationPoints.join(" ")).toMatch(/no analytical coverage/i);
    expect(results.nulls_and_exclusions.outside_domain).toMatch(/not low traffic/);

    const zeroInside = clonedResults();
    const zeroIntegrated = zeroInside.scenarios["5km_product"].integrated_exposure;
    (zeroInside.scenarios["5km_product"] as MutableScenario).integrated_exposure = {
      ...zeroIntegrated,
      inside_vsr: 0,
      outside_vsr: zeroIntegrated.total_qualified,
      inside_share: 0,
      outside_share: 1,
      presentation: {
        inside_share_percent_1dp: "0.0%",
        outside_share_percent_1dp: "100.0%",
      },
    };
    const zeroView = buildExposureResultsViewModel(parseExposureResults(zeroInside));
    expect(zeroView.primary.insideShare).toBe("0.0%");
    expect(zeroView.primary.insideShareFraction).toBe(0);
  });

  it("renders integrated and high-area shares as distinct measures with visible sensitivity and limitations", () => {
    const results = parseExposureResultsText(resultText);
    const markup = renderToStaticMarkup(
      createElement(ExposureResultsPanel, {
        load: { ok: true, results, sha256: EXPOSURE_RESULTS_SHA256 },
      }),
    );
    expect(markup).toContain("Share of integrated relative exposure");
    expect(markup).toContain("Share of high-exposure water area");
    expect(markup).toContain("74.9%");
    expect(markup).toContain("-17.2741");
    expect(markup).toContain("Modeled whale habitat, not observed individual whales");
    expect(markup).toContain("not empirically complete AIS coverage");
    expect(markup).toContain("Speed remains separate");
    expect(markup).not.toMatch(/collision zones|predicted strikes|VSR effectiveness/i);
  });
});

interface ExposureThresholdMutable {
  available: boolean;
  threshold: number | null;
  selected_water_area_km2: number | null;
  inside_share_of_selected_water: number | null;
  outside_share_of_selected_water: number | null;
  unavailable_reason: string | null;
  presentation: {
    inside_share_percent_1dp: string | null;
    outside_share_percent_1dp: string | null;
    selected_water_area_1dp: string | null;
    threshold_4dp: string | null;
  };
}

interface MutableScenario {
  integrated_exposure: ExposureResults["scenarios"]["5km_product"]["integrated_exposure"];
}
