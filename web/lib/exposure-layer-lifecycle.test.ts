import { describe, expect, it } from "vitest";
import { ExposureLayerPairingError } from "./exposure-source";
import type { MapLayerAction } from "./map-layer-state";
import { startVerifiedGeoJsonLayerLoad } from "./verified-geojson-layer-lifecycle";

class FakeLayer {
  visible = true;
  destroyed = false;

  constructor(readonly id: string) {}
  async load(): Promise<void> {}
  async queryFeatureCount(): Promise<number> {
    return 2793;
  }
  destroy(): void {
    this.destroyed = true;
  }
}

class FakeMap {
  layers: FakeLayer[] = [];
  findLayerById(id: string): FakeLayer | undefined {
    return this.layers.find((layer) => layer.id === id);
  }
  add(layer: FakeLayer): void {
    this.layers.push(layer);
  }
  remove(layer: FakeLayer): void {
    this.layers = this.layers.filter((candidate) => candidate !== layer);
  }
}

describe("relative-exposure lifecycle isolation", () => {
  it("reports a pairing failure without disturbing unrelated input layers", async () => {
    const map = new FakeMap();
    const whale = new FakeLayer("whale");
    const vessel = new FakeLayer("vessel");
    map.layers = [whale, vessel];
    const actions: MapLayerAction[] = [];
    const layerRef = { current: null as FakeLayer | null };
    let created = false;

    const load = startVerifiedGeoJsonLayerLoad({
      map,
      source: { layerId: "exposure", title: "Relative exposure" },
      url: "/layers/relative-exposure.geojson",
      visibleRef: { current: true },
      layerRef,
      dispatch: (action) => actions.push(action),
      setChecksumVerified: () => undefined,
      fetchResponse: async () => ({
        ok: true,
        status: 200,
        arrayBuffer: async () => new Uint8Array([1]).buffer,
      }),
      createObjectUrl: () => "blob:exposure",
      revokeObjectUrl: () => undefined,
      createLayer: () => {
        created = true;
        return new FakeLayer("exposure");
      },
      verifyBytes: async () => {
        throw new ExposureLayerPairingError("results checksum mismatch");
      },
      assertFeatureCount: () => undefined,
      checksumError: (error) => error instanceof ExposureLayerPairingError,
      failureMessage: "exposure unavailable",
      checksumMessage: "exposure pairing mismatch",
      loadTimeoutMs: 10_000,
    });
    await load.settled;

    expect(created).toBe(false);
    expect(layerRef.current).toBeNull();
    expect(map.layers).toEqual([whale, vessel]);
    expect(whale.destroyed).toBe(false);
    expect(vessel.destroyed).toBe(false);
    expect(actions).toEqual([
      { type: "load-started" },
      { type: "load-failed", warning: "exposure pairing mismatch" },
    ]);
  });
});
