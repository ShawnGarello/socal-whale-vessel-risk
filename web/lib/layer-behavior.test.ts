import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import VsrLayerControl from "../components/VsrLayerControl";
import WhaleLayerControl from "../components/WhaleLayerControl";
import { releaseOwnedLayer } from "./layer-lifecycle";
import {
  INITIAL_MAP_LAYER_STATE,
  mapLayerReducer,
  type MapLayerState,
} from "./map-layer-state";
import { VSR_MAP_UNAVAILABLE_MESSAGE } from "./vsr-source";
import { WHALE_SOURCE } from "./whale-source";

const WHALE_MAP_UNAVAILABLE_MESSAGE =
  "The modeled blue-whale density layer is unavailable because the map could " +
  "not be initialized.";

describe("map layer state", () => {
  it("tracks loading independently before making the layer interactive", () => {
    const loading = mapLayerReducer(INITIAL_MAP_LAYER_STATE, {
      type: "load-started",
    });
    const ready = mapLayerReducer(loading, {
      type: "load-succeeded",
      featureCount: 1,
    });

    expect(loading).toMatchObject({ status: "loading", visible: true });
    expect(ready).toMatchObject({
      status: "ready",
      visible: true,
      featureCount: 1,
      warning: null,
    });
  });

  it("preserves the requested visibility through state changes", () => {
    const hidden = mapLayerReducer(INITIAL_MAP_LAYER_STATE, {
      type: "visibility-changed",
      visible: false,
    });
    const ready = mapLayerReducer(hidden, {
      type: "load-succeeded",
      featureCount: 1,
    });

    expect(ready.visible).toBe(false);
  });

  it("drops a stale feature count when a layer later fails", () => {
    const ready: MapLayerState = {
      status: "ready",
      visible: true,
      featureCount: 4516,
      warning: null,
    };
    const failed = mapLayerReducer(ready, {
      type: "load-failed",
      warning: "unavailable",
    });

    expect(failed).toMatchObject({
      status: "error",
      featureCount: null,
      warning: "unavailable",
    });
  });
});

describe("VSR layer control", () => {
  it("shows a concise accessible layer warning without replacing the control", () => {
    const failed: MapLayerState = {
      status: "error",
      visible: true,
      featureCount: null,
      warning:
        "The 2026 California VSR zone could not be loaded. The basemap remains available.",
    };
    const markup = renderToStaticMarkup(
      createElement(VsrLayerControl, {
        state: failed,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain("The basemap remains available.");
    expect(markup).toContain("2026 California VSR zone");
    expect(markup).toContain("disabled");
  });

  it("shows a truthful unavailable state when map initialization fails", () => {
    const previouslyReady: MapLayerState = {
      status: "ready",
      visible: true,
      featureCount: 1,
      warning: null,
    };
    const unavailable = mapLayerReducer(previouslyReady, {
      type: "map-unavailable",
      warning: VSR_MAP_UNAVAILABLE_MESSAGE,
    });
    const markup = renderToStaticMarkup(
      createElement(VsrLayerControl, {
        state: unavailable,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(unavailable).toMatchObject({
      status: "error",
      featureCount: null,
      warning: VSR_MAP_UNAVAILABLE_MESSAGE,
    });
    expect(markup).toContain("Boundary unavailable");
    expect(markup).toContain(VSR_MAP_UNAVAILABLE_MESSAGE);
    expect(markup).not.toContain("The basemap remains available");
    expect(markup).toContain("disabled");
  });

  it("exposes an enabled checked control, legend, source, and disclosure when ready", () => {
    const ready: MapLayerState = {
      status: "ready",
      visible: true,
      featureCount: 1,
      warning: null,
    };
    const markup = renderToStaticMarkup(
      createElement(VsrLayerControl, {
        state: ready,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain('type="checkbox"');
    expect(markup).toContain("checked");
    expect(markup).not.toContain("disabled");
    expect(markup).toContain("VSR boundary");
    expect(markup).toContain("<details");
    expect(markup).toContain("Created by Danielle Alvarez, with CMSF and BWBS.");
    expect(markup).toContain("View publisher item");
  });
});

describe("whale layer control", () => {
  const ready: MapLayerState = {
    status: "ready",
    visible: true,
    featureCount: 4516,
    warning: null,
  };

  it("states the displayed units and every class break in the legend", () => {
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: ready,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain("Modeled density (animals/km²)");
    for (const entry of WHALE_SOURCE.classes) {
      expect(markup).toContain(entry.label);
    }
    expect(markup).toContain("4,516 grid cells");
    expect(markup).toContain('type="checkbox"');
    expect(markup).toContain("checked");
    expect(markup).not.toContain("disabled");
  });

  it("discloses the source, method, citations, and displayed artifact identity", () => {
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: ready,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain("<details");
    expect(markup).toContain("NOAA Fisheries");
    expect(markup).toContain("Becker EA");
    expect(markup).toContain("https://doi.org/10.25923/3znq-yx13");
    expect(markup).toContain("https://www.fisheries.noaa.gov/inport/item/64349");
    expect(markup).toContain("Blue_whale_summer_fall");
    expect(markup).toContain("2026-08-25");
    expect(markup).toContain(WHALE_SOURCE.exportSha256);
    expect(markup).toContain(WHALE_SOURCE.analysisSourceSha256);
  });

  it("states the classification as a display choice, not a result", () => {
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: ready,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain("A display choice");
    expect(markup).toContain("equal 0.001 animals/km² classes");
  });

  it("says the values are modeled and claims no exposure or strike risk", () => {
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: ready,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain("modeled densities, not observed whales");
    expect(markup).toContain("no vessel exposure");
    expect(markup).toContain("no collision probability");
    expect(markup).toContain("no strike risk");
    expect(markup).toContain("uncertainty is not propagated");
    expect(markup).toContain("reporting grid");
  });

  it("keeps the control present and disabled when the layer fails", () => {
    const failed = mapLayerReducer(ready, {
      type: "load-failed",
      warning:
        "The modeled blue-whale density layer could not be loaded. The " +
        "basemap and the VSR boundary remain available.",
    });
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: failed,
        checksumVerified: null,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain("Density grid unavailable");
    expect(markup).toContain("the VSR boundary remain available");
    expect(markup).toContain("disabled");
    expect(markup).not.toContain("grid cells");
  });

  it("reports the map failure without blaming the whale export", () => {
    const unavailable = mapLayerReducer(ready, {
      type: "map-unavailable",
      warning: WHALE_MAP_UNAVAILABLE_MESSAGE,
    });
    const markup = renderToStaticMarkup(
      createElement(WhaleLayerControl, {
        state: unavailable,
        checksumVerified: null,
        onVisibilityChange: () => undefined,
      }),
    );

    expect(markup).toContain(WHALE_MAP_UNAVAILABLE_MESSAGE);
    expect(markup).toContain("disabled");
  });
});

describe("owned layer lifecycle", () => {
  it("keeps a replacement layer when stale-effect cleanup releases its own layer", () => {
    class FakeLayer {
      destroyed = false;

      destroy() {
        this.destroyed = true;
      }
    }

    const staleLayer = new FakeLayer();
    const replacementLayer = new FakeLayer();
    const removed: FakeLayer[] = [];
    const map = { remove: (layer: FakeLayer) => removed.push(layer) };
    const layerRef = { current: replacementLayer as FakeLayer | null };

    releaseOwnedLayer(map, staleLayer, layerRef);

    expect(removed).toEqual([staleLayer]);
    expect(staleLayer.destroyed).toBe(true);
    expect(replacementLayer.destroyed).toBe(false);
    expect(layerRef.current).toBe(replacementLayer);
  });
});
