import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  DEFAULT_WHALE_LAYER_URL,
  WHALE_DENSITY_CLASSES,
  WHALE_SOURCE,
  assertExpectedWhaleFeatureCount,
  classifyDensity,
  resolveWhaleLayerUrl,
} from "./whale-source";

const mapFrameSource = readFileSync(
  new URL("../components/ArcgisMapFrame.tsx", import.meta.url),
  "utf8",
);

describe("whale layer source configuration", () => {
  it("binds the build to one exact export and its validated analysis source", () => {
    expect(WHALE_SOURCE.exportSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(WHALE_SOURCE.analysisSourceSha256).toBe(
      "421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62",
    );
    expect(WHALE_SOURCE.expectedFeatureCount).toBe(4516);
  });

  it("uses a same-origin default path and honours a release override", () => {
    expect(DEFAULT_WHALE_LAYER_URL).toBe("/layers/blue-whale-density.geojson");
    expect(resolveWhaleLayerUrl(undefined)).toBe(DEFAULT_WHALE_LAYER_URL);
    expect(resolveWhaleLayerUrl("   ")).toBe(DEFAULT_WHALE_LAYER_URL);
    expect(resolveWhaleLayerUrl("/layers/blue-whale-density.831a5412.geojson")).toBe(
      "/layers/blue-whale-density.831a5412.geojson",
    );
  });

  it("rejects a truncated, empty, or changed export before display", () => {
    expect(() => assertExpectedWhaleFeatureCount(0)).toThrow(/received 0/);
    expect(() => assertExpectedWhaleFeatureCount(4515)).toThrow(/received 4515/);
    expect(() => assertExpectedWhaleFeatureCount(4516)).not.toThrow();
  });

  it("names the value field and its unit exactly as the export does", () => {
    expect(WHALE_SOURCE.valueField).toBe("modeled_density_animals_per_km2");
    expect(WHALE_SOURCE.valueUnit).toBe("animals/km²");
    expect(WHALE_SOURCE.objectIdField).toBe("object_id");
    expect(WHALE_SOURCE.featureIdField).toBe("cell_id");
  });

  it("gives every popup field a label, a unit, and a usable precision", () => {
    for (const field of WHALE_SOURCE.popupFields) {
      expect(field.label.length).toBeGreaterThan(0);
      expect(field.unit.length).toBeGreaterThan(0);
      expect(field.decimals).toBeGreaterThanOrEqual(3);
    }
    // Density spans 0.000834 to 0.007648, so fewer places would collapse most
    // of the surface onto a single displayed value.
    const density = WHALE_SOURCE.popupFields.find(
      (field) => field.name === WHALE_SOURCE.valueField,
    );
    expect(density?.decimals).toBe(6);
  });

  it("publishes no field the display export withholds", () => {
    const withheld = [
      "row_index",
      "column_index",
      "cell_x_min_m",
      "cell_y_min_m",
      "cell_x_max_m",
      "cell_y_max_m",
      "water_area_m2",
      "source_covered_water_area_m2",
      "source_covered_water_area_km2",
      "uncovered_water_area_m2",
      "uncovered_water_area_km2",
      "source_polygon_count",
    ];
    const popupNames = WHALE_SOURCE.popupFields.map((field) => field.name);
    for (const name of withheld) {
      expect(popupNames).not.toContain(name);
      expect(mapFrameSource).not.toContain(`name: "${name}"`);
    }
  });
});

describe("whale density classification", () => {
  it("covers the exported value range without a gap or an overlap", () => {
    expect(WHALE_DENSITY_CLASSES[0].min).toBe(0);
    expect(WHALE_DENSITY_CLASSES.at(-1)?.max).toBeNull();
    for (let index = 1; index < WHALE_DENSITY_CLASSES.length; index += 1) {
      expect(WHALE_DENSITY_CLASSES[index].min).toBe(
        WHALE_DENSITY_CLASSES[index - 1].max,
      );
    }
  });

  it("places the exported minimum and maximum in the first and last classes", () => {
    expect(classifyDensity(0.00083394)).toBe(WHALE_DENSITY_CLASSES[0]);
    expect(classifyDensity(0.007648247)).toBe(WHALE_DENSITY_CLASSES.at(-1));
  });

  it("assigns each break value to the class it opens", () => {
    expect(classifyDensity(0.002)).toBe(WHALE_DENSITY_CLASSES[1]);
    expect(classifyDensity(0.003)).toBe(WHALE_DENSITY_CLASSES[2]);
    expect(classifyDensity(0.004)).toBe(WHALE_DENSITY_CLASSES[3]);
    expect(classifyDensity(0.005)).toBe(WHALE_DENSITY_CLASSES[4]);
  });

  it("refuses to classify a negative or non-finite value", () => {
    expect(classifyDensity(-0.001)).toBeNull();
    expect(classifyDensity(Number.NaN)).toBeNull();
    expect(classifyDensity(Number.POSITIVE_INFINITY)).toBeNull();
  });

  it("keeps every class visually distinct and translucent enough to read the basemap", () => {
    const seen = new Set<string>();
    for (const entry of WHALE_DENSITY_CLASSES) {
      const [red, green, blue, alpha] = entry.color;
      expect(alpha).toBeGreaterThan(0.6);
      expect(alpha).toBeLessThan(0.9);
      seen.add(`${red},${green},${blue}`);
    }
    expect(seen.size).toBe(WHALE_DENSITY_CLASSES.length);
  });
});

describe("whale layer map integration", () => {
  it("draws the whale fill beneath the publisher VSR outline", () => {
    expect(mapFrameSource).toContain("map.add(ownedLayer, 0);");
  });

  it("bounds the whale request and isolates its failure from the rest of the map", () => {
    expect(mapFrameSource).toContain("WHALE_LOAD_TIMEOUT_MS");
    expect(mapFrameSource).toContain("assertExpectedWhaleFeatureCount(featureCount)");
    expect(mapFrameSource).toContain(
      'dispatchWhale({ type: "load-failed", warning: WHALE_FAILURE_MESSAGE });',
    );
    expect(mapFrameSource).toContain(
      "releaseOwnedLayer(map, ownedLayer, whaleLayerRef);",
    );
  });

  it("declares the layer schema explicitly instead of inferring it", () => {
    expect(mapFrameSource).toContain('geometryType: "polygon"');
    expect(mapFrameSource).toContain("spatialReference: { wkid: 4326 }");
    expect(mapFrameSource).toContain("objectIdField: WHALE_SOURCE.objectIdField");
  });

  it("credits the whale data source through the SDK attribution", () => {
    expect(mapFrameSource).toContain("copyright: WHALE_SOURCE.attribution");
  });

  it("keeps the publisher VSR service as a reference, never a copy", () => {
    expect(mapFrameSource).toContain("url: VSR_SOURCE.serviceUrl");
    expect(mapFrameSource).toContain(
      "definitionExpression: VSR_SOURCE.definitionExpression",
    );
  });
});
