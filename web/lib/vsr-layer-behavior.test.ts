import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import VsrLayerControl from "../components/VsrLayerControl";
import { releaseOwnedVsrLayer } from "./vsr-layer-lifecycle";
import {
  INITIAL_VSR_LAYER_STATE,
  VSR_MAP_UNAVAILABLE_MESSAGE,
  vsrLayerReducer,
  type VsrLayerState,
} from "./vsr-layer-state";

describe("VSR layer state", () => {
  it("tracks loading independently before making the layer interactive", () => {
    const loading = vsrLayerReducer(INITIAL_VSR_LAYER_STATE, {
      type: "load-started",
    });
    const ready = vsrLayerReducer(loading, {
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
    const hidden = vsrLayerReducer(INITIAL_VSR_LAYER_STATE, {
      type: "visibility-changed",
      visible: false,
    });
    const ready = vsrLayerReducer(hidden, {
      type: "load-succeeded",
      featureCount: 1,
    });

    expect(ready.visible).toBe(false);
  });

  it("shows a concise accessible layer warning without replacing the control", () => {
    const failed: VsrLayerState = {
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

    expect(markup).toContain('aria-label="Map layers"');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain("The basemap remains available.");
    expect(markup).toContain("2026 California VSR zone");
    expect(markup).toContain("disabled");
  });

  it("shows a truthful unavailable state when map initialization fails", () => {
    const previouslyReady: VsrLayerState = {
      status: "ready",
      visible: true,
      featureCount: 1,
      warning: null,
    };
    const unavailable = vsrLayerReducer(previouslyReady, {
      type: "map-unavailable",
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
    const ready: VsrLayerState = {
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

describe("VSR layer lifecycle", () => {
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

    releaseOwnedVsrLayer(map, staleLayer, layerRef);

    expect(removed).toEqual([staleLayer]);
    expect(staleLayer.destroyed).toBe(true);
    expect(replacementLayer.destroyed).toBe(false);
    expect(layerRef.current).toBe(replacementLayer);
  });
});
