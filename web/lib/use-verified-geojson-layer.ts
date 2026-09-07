"use client";

import type { Dispatch, MutableRefObject } from "react";
import { useEffect } from "react";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import type Map from "@arcgis/core/Map.js";
import { releaseOwnedLayer } from "./layer-lifecycle";
import type { MapLayerAction } from "./map-layer-state";

interface VerifiedGeoJsonSource {
  readonly layerId: string;
  readonly title: string;
  readonly expectedFeatureCount: number;
}

interface UseVerifiedGeoJsonLayerOptions {
  readonly mapIsReady: boolean;
  readonly getMap: () => Map | null | undefined;
  readonly source: VerifiedGeoJsonSource;
  readonly url: string;
  readonly visibleRef: MutableRefObject<boolean>;
  readonly layerRef: MutableRefObject<GeoJSONLayer | null>;
  readonly dispatch: Dispatch<MapLayerAction>;
  readonly setChecksumVerified: Dispatch<boolean | null>;
  readonly createLayer: (objectUrl: string) => GeoJSONLayer;
  readonly verifyBytes: (bytes: ArrayBuffer) => Promise<boolean>;
  readonly assertFeatureCount: (featureCount: number) => void;
  readonly checksumError: (error: unknown) => boolean;
  readonly failureMessage: string;
  readonly checksumMessage: string;
  readonly mapUnavailableMessage: string;
  readonly loadTimeoutMs?: number;
  readonly afterAdd?: (map: Map) => void;
}

/**
 * Own one same-origin, checksum-bound GeoJSON layer from fetch through cleanup.
 *
 * Each invocation owns only the layer and blob URL it creates. A malformed or
 * missing file therefore changes only that layer's state, while abort and
 * cleanup prevent stale completions and duplicate layers.
 */
export function useVerifiedGeoJsonLayer({
  mapIsReady,
  getMap,
  source,
  url,
  visibleRef,
  layerRef,
  dispatch,
  setChecksumVerified,
  createLayer,
  verifyBytes,
  assertFeatureCount,
  checksumError,
  failureMessage,
  checksumMessage,
  mapUnavailableMessage,
  loadTimeoutMs = 30_000,
  afterAdd,
}: UseVerifiedGeoJsonLayerOptions): void {
  useEffect(() => {
    if (!mapIsReady) return;
    const map = getMap();
    if (!map) {
      dispatch({ type: "map-unavailable", warning: mapUnavailableMessage });
      return;
    }

    let disposed = false;
    let ownedLayer: GeoJSONLayer | null = null;
    let objectUrl: string | null = null;
    const abortController = new AbortController();
    const timeout = window.setTimeout(() => abortController.abort(), loadTimeoutMs);

    const loadLayer = async () => {
      dispatch({ type: "load-started" });
      setChecksumVerified(null);
      try {
        if (map.findLayerById(source.layerId)) {
          throw new Error(`${source.title} layer id is already in use.`);
        }
        const response = await fetch(url, {
          signal: abortController.signal,
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`${source.title} request returned HTTP ${response.status}.`);
        }
        const bytes = await response.arrayBuffer();
        setChecksumVerified(await verifyBytes(bytes));
        objectUrl = URL.createObjectURL(
          new Blob([bytes], { type: "application/geo+json" }),
        );
        ownedLayer = createLayer(objectUrl);
        ownedLayer.visible = visibleRef.current;
        layerRef.current = ownedLayer;
        map.add(ownedLayer);
        afterAdd?.(map);

        await ownedLayer.load({ signal: abortController.signal });
        const featureCount = await ownedLayer.queryFeatureCount(undefined, {
          signal: abortController.signal,
        });
        assertFeatureCount(featureCount);
        if (!disposed) dispatch({ type: "load-succeeded", featureCount });
      } catch (error) {
        releaseOwnedLayer(map, ownedLayer, layerRef);
        ownedLayer = null;
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = null;
        }
        if (!disposed) {
          setChecksumVerified(null);
          dispatch({
            type: "load-failed",
            warning: checksumError(error) ? checksumMessage : failureMessage,
          });
        }
      } finally {
        window.clearTimeout(timeout);
      }
    };

    void loadLayer();
    return () => {
      disposed = true;
      abortController.abort();
      window.clearTimeout(timeout);
      releaseOwnedLayer(map, ownedLayer, layerRef);
      ownedLayer = null;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [
    afterAdd,
    assertFeatureCount,
    checksumError,
    checksumMessage,
    createLayer,
    dispatch,
    failureMessage,
    getMap,
    layerRef,
    loadTimeoutMs,
    mapIsReady,
    mapUnavailableMessage,
    setChecksumVerified,
    source,
    url,
    verifyBytes,
    visibleRef,
  ]);
}
