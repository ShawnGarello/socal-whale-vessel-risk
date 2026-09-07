import { describe, expect, it } from "vitest";
import type { MapLayerAction } from "./map-layer-state";
import { startVerifiedGeoJsonLayerLoad } from "./verified-geojson-layer-lifecycle";

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

class FakeLayer {
  visible = false;
  destroyed = false;
  loadCallCount = 0;
  queryCallCount = 0;

  constructor(
    readonly id: string,
    private readonly loadResult: () => Promise<unknown> = async () => undefined,
    private readonly queryResult: () => Promise<number> = async () => 1,
  ) {}

  async load(options: { signal: AbortSignal }): Promise<unknown> {
    void options;
    this.loadCallCount += 1;
    return this.loadResult();
  }

  async queryFeatureCount(
    query: undefined,
    options: { signal: AbortSignal },
  ): Promise<number> {
    void query;
    void options;
    this.queryCallCount += 1;
    return this.queryResult();
  }

  destroy(): void {
    this.destroyed = true;
  }
}

class FakeMap {
  readonly added: FakeLayer[] = [];
  readonly removed: FakeLayer[] = [];
  layers: FakeLayer[] = [];

  findLayerById(id: string): FakeLayer | undefined {
    return this.layers.find((layer) => layer.id === id);
  }

  add(layer: FakeLayer): void {
    this.added.push(layer);
    this.layers.push(layer);
  }

  remove(layer: FakeLayer): void {
    this.removed.push(layer);
    this.layers = this.layers.filter((candidate) => candidate !== layer);
  }
}

interface HarnessOptions {
  readonly map: FakeMap;
  readonly layerRef: { current: FakeLayer | null };
  readonly actions: MapLayerAction[];
  readonly checksumStates: Array<boolean | null>;
  readonly createdObjectUrls: string[];
  readonly revokedObjectUrls: string[];
  readonly createLayer: (objectUrl: string) => FakeLayer;
  readonly verifyBytes?: (bytes: ArrayBuffer) => Promise<boolean>;
}

function startHarness({
  map,
  layerRef,
  actions,
  checksumStates,
  createdObjectUrls,
  revokedObjectUrls,
  createLayer,
  verifyBytes = async () => true,
}: HarnessOptions) {
  return startVerifiedGeoJsonLayerLoad({
    map,
    source: { layerId: "activity", title: "Activity" },
    url: "/activity.geojson",
    visibleRef: { current: true },
    layerRef,
    dispatch: (action) => actions.push(action),
    setChecksumVerified: (verified) => checksumStates.push(verified),
    fetchResponse: async () => ({
      ok: true,
      status: 200,
      arrayBuffer: async () => new Uint8Array([1, 2, 3]).buffer,
    }),
    createObjectUrl: () => {
      const objectUrl = `blob:test-${createdObjectUrls.length + 1}`;
      createdObjectUrls.push(objectUrl);
      return objectUrl;
    },
    revokeObjectUrl: (objectUrl) => revokedObjectUrls.push(objectUrl),
    createLayer,
    verifyBytes,
    assertFeatureCount: (featureCount) => {
      if (featureCount !== 1) throw new Error("unexpected feature count");
    },
    checksumError: () => false,
    failureMessage: "activity unavailable",
    checksumMessage: "activity checksum mismatch",
    loadTimeoutMs: 10_000,
  });
}

describe("verified GeoJSON asynchronous ownership", () => {
  it("does nothing after cleanup while checksum verification is pending", async () => {
    const map = new FakeMap();
    const layerRef = { current: null as FakeLayer | null };
    const actions: MapLayerAction[] = [];
    const checksumStates: Array<boolean | null> = [];
    const createdObjectUrls: string[] = [];
    const revokedObjectUrls: string[] = [];
    const verificationStarted = deferred<void>();
    const verificationResult = deferred<boolean>();
    let createLayerCalls = 0;

    const handle = startHarness({
      map,
      layerRef,
      actions,
      checksumStates,
      createdObjectUrls,
      revokedObjectUrls,
      createLayer: () => {
        createLayerCalls += 1;
        return new FakeLayer("activity");
      },
      verifyBytes: async () => {
        verificationStarted.resolve();
        return verificationResult.promise;
      },
    });

    await verificationStarted.promise;
    handle.dispose();
    verificationResult.resolve(true);
    await handle.settled;

    expect(actions).toEqual([{ type: "load-started" }]);
    expect(checksumStates).toEqual([null]);
    expect(createdObjectUrls).toEqual([]);
    expect(revokedObjectUrls).toEqual([]);
    expect(createLayerCalls).toBe(0);
    expect(map.added).toEqual([]);
    expect(layerRef.current).toBeNull();
  });

  it("prevents an older load from interfering with its ready replacement", async () => {
    const map = new FakeMap();
    const layerRef = { current: null as FakeLayer | null };
    const actions: MapLayerAction[] = [];
    const checksumStates: Array<boolean | null> = [];
    const createdObjectUrls: string[] = [];
    const revokedObjectUrls: string[] = [];
    const oldLoadStarted = deferred<void>();
    const oldLoadResult = deferred<unknown>();
    const oldLayer = new FakeLayer("activity", async () => {
      oldLoadStarted.resolve();
      return oldLoadResult.promise;
    });
    const replacementLayer = new FakeLayer("activity");

    const oldHandle = startHarness({
      map,
      layerRef,
      actions,
      checksumStates,
      createdObjectUrls,
      revokedObjectUrls,
      createLayer: () => oldLayer,
    });
    await oldLoadStarted.promise;
    oldHandle.dispose();

    const replacementHandle = startHarness({
      map,
      layerRef,
      actions,
      checksumStates,
      createdObjectUrls,
      revokedObjectUrls,
      createLayer: () => replacementLayer,
    });
    await replacementHandle.settled;
    oldLoadResult.resolve(undefined);
    await oldHandle.settled;

    expect(oldLayer.destroyed).toBe(true);
    expect(oldLayer.queryCallCount).toBe(0);
    expect(replacementLayer.destroyed).toBe(false);
    expect(replacementLayer.queryCallCount).toBe(1);
    expect(map.added).toEqual([oldLayer, replacementLayer]);
    expect(map.removed).toEqual([oldLayer]);
    expect(map.layers).toEqual([replacementLayer]);
    expect(layerRef.current).toBe(replacementLayer);
    expect(revokedObjectUrls).toEqual(["blob:test-1"]);
    expect(actions).toEqual([
      { type: "load-started" },
      { type: "load-started" },
      { type: "load-succeeded", featureCount: 1 },
    ]);

    replacementHandle.dispose();
    expect(layerRef.current).toBeNull();
    expect(map.layers).toEqual([]);
    expect(revokedObjectUrls).toEqual(["blob:test-1", "blob:test-2"]);
  });

  it("removes only the failed layer and leaves unrelated layers intact", async () => {
    const map = new FakeMap();
    const unrelatedLayer = new FakeLayer("unrelated");
    map.layers = [unrelatedLayer];
    const failedLayer = new FakeLayer("activity", async () => {
      throw new Error("parse failed");
    });
    const layerRef = { current: null as FakeLayer | null };
    const actions: MapLayerAction[] = [];
    const checksumStates: Array<boolean | null> = [];
    const createdObjectUrls: string[] = [];
    const revokedObjectUrls: string[] = [];

    const handle = startHarness({
      map,
      layerRef,
      actions,
      checksumStates,
      createdObjectUrls,
      revokedObjectUrls,
      createLayer: () => failedLayer,
    });
    await handle.settled;

    expect(map.layers).toEqual([unrelatedLayer]);
    expect(map.removed).toEqual([failedLayer]);
    expect(failedLayer.destroyed).toBe(true);
    expect(unrelatedLayer.destroyed).toBe(false);
    expect(layerRef.current).toBeNull();
    expect(revokedObjectUrls).toEqual(["blob:test-1"]);
    expect(checksumStates).toEqual([null, true, null]);
    expect(actions).toEqual([
      { type: "load-started" },
      { type: "load-failed", warning: "activity unavailable" },
    ]);
  });
});
