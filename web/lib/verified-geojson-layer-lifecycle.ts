import type { Dispatch, MutableRefObject } from "react";
import {
  releaseOwnedLayer,
  type DestroyableLayer,
  type LayerMapLike,
} from "./layer-lifecycle";
import type { MapLayerAction } from "./map-layer-state";

interface VerifiedGeoJsonSource {
  readonly layerId: string;
  readonly title: string;
}

interface FetchResponseLike {
  readonly ok: boolean;
  readonly status: number;
  arrayBuffer(): Promise<ArrayBuffer>;
}

export interface VerifiedGeoJsonLayerLike extends DestroyableLayer {
  visible: boolean;
  load(options: { signal: AbortSignal }): Promise<unknown>;
  queryFeatureCount(
    query: undefined,
    options: { signal: AbortSignal },
  ): Promise<number>;
}

export interface VerifiedGeoJsonMapLike<Layer> extends LayerMapLike<Layer> {
  findLayerById(id: string): unknown;
  add(layer: Layer): void;
}

interface StartVerifiedGeoJsonLayerLoadOptions<
  Layer extends VerifiedGeoJsonLayerLike,
  LayerMap extends VerifiedGeoJsonMapLike<Layer>,
> {
  readonly map: LayerMap;
  readonly source: VerifiedGeoJsonSource;
  readonly url: string;
  readonly visibleRef: MutableRefObject<boolean>;
  readonly layerRef: MutableRefObject<Layer | null>;
  readonly dispatch: Dispatch<MapLayerAction>;
  readonly setChecksumVerified: Dispatch<boolean | null>;
  readonly fetchResponse: (
    url: string,
    options: { signal: AbortSignal; cache: "no-store" },
  ) => Promise<FetchResponseLike>;
  readonly createObjectUrl: (bytes: ArrayBuffer) => string;
  readonly revokeObjectUrl: (url: string) => void;
  readonly createLayer: (objectUrl: string) => Layer;
  readonly verifyBytes: (bytes: ArrayBuffer) => Promise<boolean>;
  readonly assertFeatureCount: (featureCount: number) => void;
  readonly checksumError: (error: unknown) => boolean;
  readonly failureMessage: string;
  readonly checksumMessage: string;
  readonly loadTimeoutMs: number;
  readonly afterAdd?: (map: LayerMap) => void;
}

export interface VerifiedGeoJsonLayerLoadHandle {
  /** Settles after this execution has either loaded or cleaned up. */
  readonly settled: Promise<void>;
  /** Cancels and releases only the resources owned by this execution. */
  dispose(): void;
}

class InactiveLayerLoadError extends Error {
  constructor() {
    super("Verified GeoJSON layer load is no longer active.");
    this.name = "InactiveLayerLoadError";
  }
}

/**
 * Runs one independently owned verified-GeoJSON load.
 *
 * React cleanup can occur while any awaited operation is pending. Every async
 * continuation therefore proves that this execution is still active before it
 * mutates state or creates, publishes, or adds a resource. Cleanup also clears
 * its local ownership variables so a late rejection cannot release twice or
 * touch a replacement installed by a newer execution.
 */
export function startVerifiedGeoJsonLayerLoad<
  Layer extends VerifiedGeoJsonLayerLike,
  LayerMap extends VerifiedGeoJsonMapLike<Layer>,
>({
  map,
  source,
  url,
  visibleRef,
  layerRef,
  dispatch,
  setChecksumVerified,
  fetchResponse,
  createObjectUrl,
  revokeObjectUrl,
  createLayer,
  verifyBytes,
  assertFeatureCount,
  checksumError,
  failureMessage,
  checksumMessage,
  loadTimeoutMs,
  afterAdd,
}: StartVerifiedGeoJsonLayerLoadOptions<
  Layer,
  LayerMap
>): VerifiedGeoJsonLayerLoadHandle {
  let disposed = false;
  let ownedLayer: Layer | null = null;
  let objectUrl: string | null = null;
  const abortController = new AbortController();
  const timeout = globalThis.setTimeout(() => abortController.abort(), loadTimeoutMs);

  const requireActive = () => {
    if (disposed || abortController.signal.aborted) {
      throw new InactiveLayerLoadError();
    }
  };

  const releaseResources = () => {
    releaseOwnedLayer(map, ownedLayer, layerRef);
    ownedLayer = null;
    if (objectUrl) {
      revokeObjectUrl(objectUrl);
      objectUrl = null;
    }
  };

  const loadLayer = async () => {
    dispatch({ type: "load-started" });
    setChecksumVerified(null);
    try {
      if (map.findLayerById(source.layerId)) {
        throw new Error(`${source.title} layer id is already in use.`);
      }
      const response = await fetchResponse(url, {
        signal: abortController.signal,
        cache: "no-store",
      });
      requireActive();
      if (!response.ok) {
        throw new Error(`${source.title} request returned HTTP ${response.status}.`);
      }

      const bytes = await response.arrayBuffer();
      requireActive();
      const checksumVerified = await verifyBytes(bytes);
      requireActive();
      setChecksumVerified(checksumVerified);

      requireActive();
      objectUrl = createObjectUrl(bytes);
      requireActive();
      ownedLayer = createLayer(objectUrl);
      ownedLayer.visible = visibleRef.current;
      requireActive();
      layerRef.current = ownedLayer;
      map.add(ownedLayer);
      afterAdd?.(map);

      await ownedLayer.load({ signal: abortController.signal });
      requireActive();
      const featureCount = await ownedLayer.queryFeatureCount(undefined, {
        signal: abortController.signal,
      });
      requireActive();
      assertFeatureCount(featureCount);
      dispatch({ type: "load-succeeded", featureCount });
    } catch (error) {
      releaseResources();
      if (!disposed) {
        setChecksumVerified(null);
        dispatch({
          type: "load-failed",
          warning: checksumError(error) ? checksumMessage : failureMessage,
        });
      }
    } finally {
      globalThis.clearTimeout(timeout);
    }
  };

  const settled = loadLayer();
  return {
    settled,
    dispose() {
      if (disposed) return;
      disposed = true;
      abortController.abort();
      globalThis.clearTimeout(timeout);
      releaseResources();
    },
  };
}
