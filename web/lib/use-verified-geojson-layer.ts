"use client";

import type { Dispatch, MutableRefObject } from "react";
import { useEffect } from "react";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import type Map from "@arcgis/core/Map.js";
import type { MapLayerAction } from "./map-layer-state";
import { startVerifiedGeoJsonLayerLoad } from "./verified-geojson-layer-lifecycle";

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

    const load = startVerifiedGeoJsonLayerLoad({
      map,
      source,
      url,
      visibleRef,
      layerRef,
      dispatch,
      setChecksumVerified,
      fetchResponse: (requestUrl, options) => fetch(requestUrl, options),
      createObjectUrl: (bytes) =>
        URL.createObjectURL(new Blob([bytes], { type: "application/geo+json" })),
      revokeObjectUrl: (objectUrl) => URL.revokeObjectURL(objectUrl),
      createLayer,
      verifyBytes,
      assertFeatureCount,
      checksumError,
      failureMessage,
      checksumMessage,
      loadTimeoutMs,
      afterAdd,
    });
    return load.dispose;
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
