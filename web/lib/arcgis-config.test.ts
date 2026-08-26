import { describe, expect, it } from "vitest";
import {
  DEFAULT_BASEMAP_ID,
  INITIAL_VIEWPOINT,
  describeLoadErrors,
  resolveArcgisConfig,
} from "./arcgis-config";

describe("resolveArcgisConfig", () => {
  it("keeps a usable API key and reports no problems", () => {
    const config = resolveArcgisConfig({
      apiKey: "a-key",
      basemapId: "arcgis/streets",
    });

    expect(config.apiKey).toBe("a-key");
    expect(config.basemapId).toBe("arcgis/streets");
    expect(config.warnings).toEqual([]);
  });

  it("trims surrounding whitespace from provided values", () => {
    const config = resolveArcgisConfig({
      apiKey: "  a-key  ",
      basemapId: "  arcgis/streets  ",
    });

    expect(config.apiKey).toBe("a-key");
    expect(config.basemapId).toBe("arcgis/streets");
    expect(config.warnings).toEqual([]);
  });

  it("treats an unset API key as absent and warns", () => {
    const config = resolveArcgisConfig({});

    expect(config.apiKey).toBeNull();
    expect(config.warnings).toHaveLength(1);
    expect(config.warnings[0]).toContain("NEXT_PUBLIC_ARCGIS_API_KEY");
  });

  it("treats a blank API key the same as an unset one", () => {
    // A variable declared in the hosting platform but left empty is the most
    // likely deployment mistake, and must not be sent as a literal empty token.
    expect(resolveArcgisConfig({ apiKey: "" }).apiKey).toBeNull();
    expect(resolveArcgisConfig({ apiKey: "   " }).apiKey).toBeNull();
    expect(resolveArcgisConfig({ apiKey: "\n" }).apiKey).toBeNull();
  });

  it("warns about a key containing whitespace rather than silently using it", () => {
    // A pasted value that kept its line break still looks set, but the service
    // rejects it; the warning points at the cause instead of the symptom.
    const config = resolveArcgisConfig({ apiKey: "a-key\nwith-a-break" });

    expect(config.apiKey).toBe("a-key\nwith-a-break");
    expect(config.warnings).toHaveLength(1);
    expect(config.warnings[0]).toContain("whitespace");
  });

  it("falls back to the default basemap when none is configured", () => {
    expect(resolveArcgisConfig({ apiKey: "a-key" }).basemapId).toBe(DEFAULT_BASEMAP_ID);
    expect(resolveArcgisConfig({ apiKey: "a-key", basemapId: "  " }).basemapId).toBe(
      DEFAULT_BASEMAP_ID,
    );
  });
});

describe("describeLoadErrors", () => {
  it("returns nothing when nothing failed", () => {
    expect(describeLoadErrors([])).toEqual([]);
  });

  it("combines the source label with the reported reason", () => {
    expect(
      describeLoadErrors([
        { title: "Basemap", loadError: { message: "Token Required." } },
      ]),
    ).toEqual(["Basemap: Token Required."]);
  });

  it("falls back to the source type when it has no title", () => {
    expect(
      describeLoadErrors([{ type: "vector-tile", loadError: { message: "404" } }]),
    ).toEqual(["vector-tile: 404"]);
  });

  it("reports a failure that carries no message rather than dropping it", () => {
    // A silent failure must never be indistinguishable from a success.
    expect(describeLoadErrors([{ title: "Basemap" }])).toEqual([
      "Basemap: failed to load, with no reported reason.",
    ]);
    expect(describeLoadErrors([{}])).toEqual([
      "A map resource failed to load, with no reported reason.",
    ]);
  });

  it("describes every failed source, not just the first", () => {
    expect(
      describeLoadErrors([
        { title: "Basemap", loadError: { message: "Token Required." } },
        { title: "Ground", loadError: { message: "Unreachable." } },
      ]),
    ).toHaveLength(2);
  });
});

describe("INITIAL_VIEWPOINT", () => {
  it("sits over the Southern California Bight", () => {
    // Guards against a transposed or sign-flipped coordinate pair, which would
    // still build and still render — just somewhere else entirely.
    const [longitude, latitude] = INITIAL_VIEWPOINT.center;

    expect(longitude).toBeGreaterThan(-122);
    expect(longitude).toBeLessThan(-116);
    expect(latitude).toBeGreaterThan(31);
    expect(latitude).toBeLessThan(35);
  });
});
