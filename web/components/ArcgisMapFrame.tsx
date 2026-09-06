"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import esriConfig from "@arcgis/core/config.js";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import PopupTemplate from "@arcgis/core/PopupTemplate.js";
import ClassBreaksRenderer from "@arcgis/core/renderers/ClassBreaksRenderer.js";
import SimpleRenderer from "@arcgis/core/renderers/SimpleRenderer.js";
import SimpleFillSymbol from "@arcgis/core/symbols/SimpleFillSymbol.js";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
import type { ArcgisMap } from "@arcgis/map-components/components/arcgis-map";
import {
  INITIAL_VIEWPOINT,
  configureArcgisSdk,
  describeLoadErrors,
  resolveArcgisConfig,
} from "@/lib/arcgis-config";
import { releaseOwnedLayer } from "@/lib/layer-lifecycle";
import { INITIAL_MAP_LAYER_STATE, mapLayerReducer } from "@/lib/map-layer-state";
import {
  VSR_FAILURE_MESSAGE,
  VSR_MAP_UNAVAILABLE_MESSAGE,
  VSR_SOURCE,
  assertExpectedVsrFeatureCount,
} from "@/lib/vsr-source";
import {
  WHALE_SOURCE,
  WhaleLayerChecksumError,
  assertExpectedWhaleFeatureCount,
  resolveWhaleLayerUrl,
  sha256Hex,
  verifyWhaleLayerChecksum,
} from "@/lib/whale-source";
import MapLayerPanel from "./MapLayerPanel";
import VsrLayerControl from "./VsrLayerControl";
import WhaleLayerControl from "./WhaleLayerControl";
import styles from "./ArcgisMapFrame.module.css";

/*
 * This module is loaded only in the browser (see MapShell.tsx). The side-effect
 * imports above register the ArcGIS custom elements against
 * `window.customElements`, which does not exist while Next.js prerenders the
 * page during `next build`, so they must never be evaluated on the server.
 */

const config = resolveArcgisConfig({
  // Referenced literally: Next.js inlines `NEXT_PUBLIC_*` at build time and
  // cannot follow an indirect lookup such as `process.env[name]`.
  apiKey: process.env.NEXT_PUBLIC_ARCGIS_API_KEY,
  basemapId: process.env.NEXT_PUBLIC_ARCGIS_BASEMAP,
});

const whaleLayerUrl = resolveWhaleLayerUrl(process.env.NEXT_PUBLIC_WHALE_LAYER_URL);

// This is an anonymous public application: nobody signs in, and it reads only
// publicly shared content. Left at its default, the SDK answers a rejected
// request by opening its own username/password dialog and waiting, so a missing
// or unauthorized API key appears to the visitor as an indefinite "loading"
// state with a sign-in prompt over it. Turning identity off makes the request
// fail immediately instead, which the states below can report. Verified
// against SDK 5.1: without this, an unauthenticated basemap request returns 401
// and the view never becomes ready.
//
// The SDK also requires the key to be set before the first secured request.
// Module scope runs before the map element below is rendered, so both settings
// are applied in time.
configureArcgisSdk(esriConfig, config);

/**
 * How long to wait for the view before calling initialization failed.
 *
 * The SDK does not time out on its own, and not every failure raises an event —
 * so without this a stalled initialization would show "Loading map…" forever.
 * Generous enough for a cold cache on a slow connection; short enough that a
 * visitor is told something is wrong rather than left watching a spinner.
 */
const INITIALIZATION_TIMEOUT_MS = 20_000;

const TIMEOUT_MESSAGE =
  "The map view did not finish initializing within 20 seconds. The ArcGIS Maps " +
  "SDK or the basemap service may be unreachable, or the configured API key may " +
  "not be authorized for the requested basemap.";

const VSR_LOAD_TIMEOUT_MS = 15_000;

/**
 * The whale layer is one whole file, not a spatially paged service: the browser
 * downloads and parses every feature before the layer can be called ready. It
 * therefore gets a longer bound than the single filtered VSR feature does.
 */
const WHALE_LOAD_TIMEOUT_MS = 30_000;

const WHALE_FAILURE_MESSAGE =
  "The modeled blue-whale density layer could not be loaded. The basemap and " +
  "the VSR boundary remain available.";

const WHALE_CHECKSUM_MESSAGE =
  "The modeled blue-whale density layer was not displayed because the file " +
  "served does not match the checksum this build expects. The basemap and the " +
  "VSR boundary remain available.";

const WHALE_MAP_UNAVAILABLE_MESSAGE =
  "The modeled blue-whale density layer is unavailable because the map could " +
  "not be initialized.";

/**
 * Symbology for the modeled density surface.
 *
 * Per-cell outlines are deliberately absent: 4,516 stroked cells would read as
 * a mesh rather than a surface, and would compete with the VSR outline that
 * has to stay legible above the fill.
 */
function createWhaleRenderer(): ClassBreaksRenderer {
  return new ClassBreaksRenderer({
    field: WHALE_SOURCE.valueField,
    classBreakInfos: WHALE_SOURCE.classes.map((entry) => ({
      minValue: entry.min,
      maxValue: entry.max ?? Number.MAX_VALUE,
      label: entry.label,
      symbol: new SimpleFillSymbol({
        color: [...entry.color],
        outline: { width: 0 },
      }),
    })),
  });
}

function createWhalePopupTemplate(): PopupTemplate {
  return new PopupTemplate({
    title: `${WHALE_SOURCE.title} — cell {${WHALE_SOURCE.featureIdField}}`,
    content: [
      {
        type: "fields",
        fieldInfos: WHALE_SOURCE.popupFields.map((field) => ({
          fieldName: field.name,
          label: `${field.label} (${field.unit})`,
          format: { places: field.decimals, digitSeparator: false },
        })),
      },
      {
        type: "text",
        text: `<ul>${WHALE_SOURCE.statements
          .map((statement) => `<li>${statement}</li>`)
          .join("")}</ul>`,
      },
    ],
    outFields: [
      WHALE_SOURCE.featureIdField,
      ...WHALE_SOURCE.popupFields.map((field) => field.name),
    ],
  });
}

type Status = "initializing" | "ready" | "error";

interface ArcgisMapFrameProps {
  /** Whether the SDK has a ready view that can display its own attribution. */
  onSdkAttributionChange: (available: boolean) => void;
}

export default function ArcgisMapFrame({
  onSdkAttributionChange,
}: ArcgisMapFrameProps) {
  const [status, setStatus] = useState<Status>("initializing");
  const [failures, setFailures] = useState<readonly string[]>([]);
  const [mapIsReady, setMapIsReady] = useState(false);
  const [vsrState, dispatchVsr] = useReducer(mapLayerReducer, INITIAL_MAP_LAYER_STATE);
  const [whaleState, dispatchWhale] = useReducer(
    mapLayerReducer,
    INITIAL_MAP_LAYER_STATE,
  );
  // `null` until a load attempt finishes: true when the bytes were hashed and
  // matched, false when this browser exposes no SubtleCrypto to hash them.
  const [whaleChecksumVerified, setWhaleChecksumVerified] = useState<boolean | null>(
    null,
  );
  const mapRef = useRef<ArcgisMap | null>(null);
  const vsrLayerRef = useRef<FeatureLayer | null>(null);
  const vsrVisibleRef = useRef(vsrState.visible);
  const whaleLayerRef = useRef<GeoJSONLayer | null>(null);
  const whaleVisibleRef = useRef(whaleState.visible);

  const handleReadyChange = useCallback(() => {
    const element = mapRef.current;
    if (!element?.ready) return;
    // A view can be ready while a resource inside it failed — a rejected
    // basemap request is the common case. Report that instead of showing an
    // empty map that looks like it worked.
    setFailures(describeLoadErrors(element.loadErrorSources ?? []));
    onSdkAttributionChange(true);
    setStatus("ready");
    setMapIsReady(true);
  }, [onSdkAttributionChange]);

  const handleReadyError = useCallback(() => {
    const element = mapRef.current;
    const described = describeLoadErrors(element?.loadErrorSources ?? []);
    setFailures(
      described.length > 0
        ? described
        : ["The map view reported an initialization error with no further detail."],
    );
    onSdkAttributionChange(false);
    setStatus("error");
    setMapIsReady(false);
    dispatchVsr({ type: "map-unavailable", warning: VSR_MAP_UNAVAILABLE_MESSAGE });
    dispatchWhale({
      type: "map-unavailable",
      warning: WHALE_MAP_UNAVAILABLE_MESSAGE,
    });
  }, [onSdkAttributionChange]);

  useEffect(() => {
    if (status !== "initializing") return;
    const timer = window.setTimeout(() => {
      const element = mapRef.current;
      const described = describeLoadErrors(element?.loadErrorSources ?? []);
      setFailures(described.length > 0 ? described : [TIMEOUT_MESSAGE]);
      onSdkAttributionChange(false);
      setStatus("error");
      setMapIsReady(false);
      dispatchVsr({
        type: "map-unavailable",
        warning: VSR_MAP_UNAVAILABLE_MESSAGE,
      });
      dispatchWhale({
        type: "map-unavailable",
        warning: WHALE_MAP_UNAVAILABLE_MESSAGE,
      });
    }, INITIALIZATION_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [onSdkAttributionChange, status]);

  /*
   * The two layer effects below are deliberately parallel rather than shared.
   * Each owns exactly the layer it created, bounds its own load, and reports
   * its own failure, so neither the basemap nor the other layer is affected
   * when one source is unreachable.
   */

  // Project-derived whale layer. Added at index 0 so the publisher's VSR
  // outline always draws above this fill, whichever layer finishes loading
  // first.
  useEffect(() => {
    if (!mapIsReady) return;

    const map = mapRef.current?.map;
    if (!map) {
      dispatchWhale({
        type: "map-unavailable",
        warning: WHALE_MAP_UNAVAILABLE_MESSAGE,
      });
      return;
    }

    let disposed = false;
    let ownedLayer: GeoJSONLayer | null = null;
    let objectUrl: string | null = null;
    const abortController = new AbortController();
    const timeout = window.setTimeout(
      () => abortController.abort(),
      WHALE_LOAD_TIMEOUT_MS,
    );

    const loadLayer = async () => {
      dispatchWhale({ type: "load-started" });
      setWhaleChecksumVerified(null);

      try {
        const existingLayer = map.findLayerById(WHALE_SOURCE.layerId);
        if (existingLayer && !(existingLayer instanceof GeoJSONLayer)) {
          throw new Error("The whale layer id is already used by another layer.");
        }
        let layer: GeoJSONLayer;
        if (existingLayer) {
          layer = existingLayer;
        } else {
          // Fetch the file here rather than handing the URL to the SDK, so the
          // exact bytes that will be displayed are the bytes that get hashed.
          // The layer then reads them back from a blob URL, so this is still a
          // single download.
          const response = await fetch(whaleLayerUrl, {
            signal: abortController.signal,
            cache: "no-store",
          });
          if (!response.ok) {
            throw new Error(
              `The whale layer request returned HTTP ${response.status}.`,
            );
          }
          const bytes = await response.arrayBuffer();
          setWhaleChecksumVerified(verifyWhaleLayerChecksum(await sha256Hex(bytes)));
          objectUrl = URL.createObjectURL(
            new Blob([bytes], { type: "application/geo+json" }),
          );

          ownedLayer = new GeoJSONLayer({
            id: WHALE_SOURCE.layerId,
            title: WHALE_SOURCE.title,
            url: objectUrl,
            // Declared explicitly rather than inferred from the first feature,
            // so a truncated or altered export fails to load instead of
            // rendering with a silently different schema.
            geometryType: "polygon",
            spatialReference: { wkid: 4326 },
            objectIdField: WHALE_SOURCE.objectIdField,
            fields: [
              { name: "object_id", alias: "Display id", type: "oid" },
              { name: "cell_id", alias: "Grid cell", type: "string" },
              {
                name: "modeled_density_animals_per_km2",
                alias: "Modeled density (animals/km2)",
                type: "double",
              },
              {
                name: "modeled_abundance_allocation_animals",
                alias: "Modeled abundance allocation (animals)",
                type: "double",
              },
              {
                name: "water_area_km2",
                alias: "Supporting water area (km2)",
                type: "double",
              },
              {
                name: "source_coverage_fraction",
                alias: "Source-model support",
                type: "double",
              },
              {
                name: "coverage_status",
                alias: "Source support status",
                type: "string",
              },
            ],
            copyright: WHALE_SOURCE.attribution,
            visible: whaleVisibleRef.current,
            renderer: createWhaleRenderer(),
            popupTemplate: createWhalePopupTemplate(),
          });
          layer = ownedLayer;
          map.add(ownedLayer, 0);
        }
        whaleLayerRef.current = layer;

        await layer.load({ signal: abortController.signal });
        const featureCount = await layer.queryFeatureCount(undefined, {
          signal: abortController.signal,
        });

        assertExpectedWhaleFeatureCount(featureCount);
        if (!disposed) {
          dispatchWhale({ type: "load-succeeded", featureCount });
        }
      } catch (error) {
        releaseOwnedLayer(map, ownedLayer, whaleLayerRef);
        ownedLayer = null;
        // Nothing will read the blob now, so release it rather than holding a
        // copy of the file until this component unmounts.
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = null;
        }
        if (!disposed) {
          setWhaleChecksumVerified(null);
          dispatchWhale({
            type: "load-failed",
            warning:
              error instanceof WhaleLayerChecksumError
                ? WHALE_CHECKSUM_MESSAGE
                : WHALE_FAILURE_MESSAGE,
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
      releaseOwnedLayer(map, ownedLayer, whaleLayerRef);
      ownedLayer = null;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
    };
  }, [mapIsReady]);

  // Publisher-hosted VSR boundary. No geometry from this service is stored,
  // transformed, or republished by this application.
  useEffect(() => {
    if (!mapIsReady) return;

    const map = mapRef.current?.map;
    if (!map) {
      dispatchVsr({
        type: "map-unavailable",
        warning: VSR_MAP_UNAVAILABLE_MESSAGE,
      });
      return;
    }

    let disposed = false;
    let ownedLayer: FeatureLayer | null = null;
    const abortController = new AbortController();
    const timeout = window.setTimeout(
      () => abortController.abort(),
      VSR_LOAD_TIMEOUT_MS,
    );

    const loadLayer = async () => {
      dispatchVsr({ type: "load-started" });

      try {
        const existingLayer = map.findLayerById(VSR_SOURCE.layerId);
        if (existingLayer && !(existingLayer instanceof FeatureLayer)) {
          throw new Error("The VSR layer id is already used by another layer.");
        }
        let layer: FeatureLayer;
        if (existingLayer) {
          layer = existingLayer;
        } else {
          ownedLayer = new FeatureLayer({
            id: VSR_SOURCE.layerId,
            title: VSR_SOURCE.title,
            url: VSR_SOURCE.serviceUrl,
            definitionExpression: VSR_SOURCE.definitionExpression,
            outFields: ["FID"],
            visible: vsrVisibleRef.current,
            popupEnabled: false,
            renderer: new SimpleRenderer({
              symbol: new SimpleFillSymbol({
                color: [255, 180, 91, 0.08],
                outline: {
                  color: [255, 180, 91, 0.95],
                  width: 2,
                },
              }),
            }),
          });
          layer = ownedLayer;
          map.add(ownedLayer);
        }
        vsrLayerRef.current = layer;

        await layer.load({ signal: abortController.signal });
        const featureCount = await layer.queryFeatureCount(undefined, {
          signal: abortController.signal,
        });

        assertExpectedVsrFeatureCount(featureCount);
        if (!disposed) {
          dispatchVsr({ type: "load-succeeded", featureCount });
        }
      } catch {
        releaseOwnedLayer(map, ownedLayer, vsrLayerRef);
        ownedLayer = null;
        if (!disposed) {
          dispatchVsr({ type: "load-failed", warning: VSR_FAILURE_MESSAGE });
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
      releaseOwnedLayer(map, ownedLayer, vsrLayerRef);
      ownedLayer = null;
    };
  }, [mapIsReady]);

  const handleVsrVisibilityChange = useCallback((visible: boolean) => {
    vsrVisibleRef.current = visible;
    if (vsrLayerRef.current) vsrLayerRef.current.visible = visible;
    dispatchVsr({ type: "visibility-changed", visible });
  }, []);

  const handleWhaleVisibilityChange = useCallback((visible: boolean) => {
    whaleVisibleRef.current = visible;
    if (whaleLayerRef.current) whaleLayerRef.current.visible = visible;
    dispatchWhale({ type: "visibility-changed", visible });
  }, []);

  const problems = [...config.warnings, ...failures];

  return (
    <div className={styles.frame}>
      {/*
       * Unmounting this component removes the element from the document, and
       * the map component destroys its view and associated resources on
       * disconnect (`autoDestroyDisabled` defaults to false). React also
       * detaches the two event listeners below, so no handler can fire against
       * an unmounted component. Do not set `autoDestroyDisabled` without also
       * calling `destroy()` here.
       */}
      <arcgis-map
        ref={mapRef}
        className={styles.map}
        basemap={config.basemapId}
        center={`${INITIAL_VIEWPOINT.center[0]}, ${INITIAL_VIEWPOINT.center[1]}`}
        zoom={INITIAL_VIEWPOINT.zoom}
        onarcgisViewReadyChange={handleReadyChange}
        onarcgisViewReadyError={handleReadyError}
      >
        <arcgis-zoom slot="top-left" />
      </arcgis-map>

      <MapLayerPanel>
        <WhaleLayerControl
          state={whaleState}
          checksumVerified={whaleChecksumVerified}
          onVisibilityChange={handleWhaleVisibilityChange}
        />
        <VsrLayerControl
          state={vsrState}
          onVisibilityChange={handleVsrVisibilityChange}
        />
      </MapLayerPanel>

      {status === "initializing" && (
        <div className={styles.overlay} role="status" aria-live="polite">
          <p className={styles.overlayTitle}>Loading map…</p>
          <p className={styles.overlayBody}>
            Initializing the ArcGIS map view over the Southern California Bight.
          </p>
        </div>
      )}

      {status === "error" && (
        <div className={styles.overlay} role="alert">
          <p className={styles.overlayTitle}>The map could not be initialized.</p>
          <ul className={styles.reasons}>
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </div>
      )}

      {/*
       * Configuration problems are known before the map finishes trying, so
       * show them straight away rather than making the visitor wait out the
       * initialization timeout to learn the key is missing.
       */}
      {status !== "error" && problems.length > 0 && (
        <div className={styles.notice} role="alert">
          <p className={styles.noticeTitle}>
            {status === "ready"
              ? "The map loaded with problems."
              : "Configuration problem detected."}
          </p>
          <ul className={styles.reasons}>
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
