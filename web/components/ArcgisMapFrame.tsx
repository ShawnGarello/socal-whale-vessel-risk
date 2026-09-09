"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import esriConfig from "@arcgis/core/config.js";
import FeatureLayer from "@arcgis/core/layers/FeatureLayer.js";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import PopupTemplate from "@arcgis/core/PopupTemplate.js";
import ClassBreaksRenderer from "@arcgis/core/renderers/ClassBreaksRenderer.js";
import SimpleRenderer from "@arcgis/core/renderers/SimpleRenderer.js";
import SimpleFillSymbol from "@arcgis/core/symbols/SimpleFillSymbol.js";
import type Map from "@arcgis/core/Map.js";
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
  DOMAIN_SOURCE,
  DomainLayerChecksumError,
  assertExpectedDomainFeatureCount,
  resolveDomainLayerUrl,
  verifyDomainLayerBytes,
} from "@/lib/domain-source";
import {
  EXPOSURE_SOURCE,
  ExposureLayerPairingError,
  assertExpectedExposureFeatureCount,
  exposureMethodConfig,
  resolveExposureLayerUrl,
  resolveExposureManifestUrl,
  verifyExposureLayerBytes,
  type ExposureMethod,
} from "@/lib/exposure-source";
import { useVerifiedGeoJsonLayer } from "@/lib/use-verified-geojson-layer";
import {
  VESSEL_SOURCE,
  VesselLayerChecksumError,
  assertExpectedVesselFeatureCount,
  resolveVesselLayerUrl,
  verifyVesselLayerBytes,
} from "@/lib/vessel-source";
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
import DomainLayerControl from "./DomainLayerControl";
import ExposureLayerControl from "./ExposureLayerControl";
import VesselLayerControl from "./VesselLayerControl";
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
const vesselLayerUrl = resolveVesselLayerUrl(process.env.NEXT_PUBLIC_VESSEL_LAYER_URL);
const domainLayerUrl = resolveDomainLayerUrl(process.env.NEXT_PUBLIC_DOMAIN_LAYER_URL);
const exposureLayerUrl = resolveExposureLayerUrl(
  process.env.NEXT_PUBLIC_EXPOSURE_LAYER_URL,
);
const exposureManifestUrl = resolveExposureManifestUrl(
  process.env.NEXT_PUBLIC_EXPOSURE_MANIFEST_URL,
);
const verifyConfiguredExposureLayerBytes = (bytes: ArrayBuffer) =>
  verifyExposureLayerBytes(bytes, undefined, undefined, exposureManifestUrl);

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

const VESSEL_FAILURE_MESSAGE =
  "The commercial vessel activity layer could not be loaded. The basemap and " +
  "other project layers remain available.";
const VESSEL_CHECKSUM_MESSAGE =
  "The commercial vessel activity layer was not displayed because its file " +
  "does not match the checksum this build expects.";
const VESSEL_MAP_UNAVAILABLE_MESSAGE =
  "The commercial vessel activity layer is unavailable because the map could " +
  "not be initialized.";
const DOMAIN_FAILURE_MESSAGE =
  "The accepted analytical-domain boundary could not be loaded. The basemap " +
  "and other project layers remain available.";
const DOMAIN_CHECKSUM_MESSAGE =
  "The analytical-domain boundary was not displayed because its file does not " +
  "match the checksum this build expects.";
const DOMAIN_MAP_UNAVAILABLE_MESSAGE =
  "The analytical-domain boundary is unavailable because the map could not be initialized.";
const EXPOSURE_FAILURE_MESSAGE =
  "The relative-exposure layer could not be loaded. The basemap and independent input layers remain available.";
const EXPOSURE_PAIRING_MESSAGE =
  "The relative-exposure layer was not displayed because its display, manifest, and generated results do not match this build.";
const EXPOSURE_MAP_UNAVAILABLE_MESSAGE =
  "The relative-exposure layer is unavailable because the map could not be initialized.";

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

function createWhaleLayer(objectUrl: string): GeoJSONLayer {
  return new GeoJSONLayer({
    id: WHALE_SOURCE.layerId,
    title: WHALE_SOURCE.title,
    url: objectUrl,
    geometryType: "polygon",
    spatialReference: { wkid: 4326 },
    objectIdField: WHALE_SOURCE.objectIdField,
    fields: [
      { name: "object_id", alias: "Display id", type: "oid" },
      { name: "cell_id", alias: "Grid cell", type: "string" },
      {
        name: "modeled_density_animals_per_km2",
        alias: "Modeled density (animals/km²)",
        type: "double",
      },
      {
        name: "modeled_abundance_allocation_animals",
        alias: "Modeled abundance allocation (animals)",
        type: "double",
      },
      { name: "water_area_km2", alias: "Supporting water area (km²)", type: "double" },
      {
        name: "source_coverage_fraction",
        alias: "Source-model support",
        type: "double",
      },
      { name: "coverage_status", alias: "Source support status", type: "string" },
    ],
    copyright: WHALE_SOURCE.attribution,
    renderer: createWhaleRenderer(),
    popupTemplate: createWhalePopupTemplate(),
  });
}

function createVesselRenderer(): ClassBreaksRenderer {
  return new ClassBreaksRenderer({
    field: VESSEL_SOURCE.valueField,
    classBreakInfos: VESSEL_SOURCE.classes.map((entry) => ({
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

function createVesselPopupTemplate(): PopupTemplate {
  const fields = [
    ["vessel_km_per_water_km2_all_commercial", "Activity density", 2],
    ["vessel_km_all_commercial", "All commercial movement", 1],
    ["vessel_km_passenger", "Passenger movement", 1],
    ["vessel_km_cargo", "Cargo movement", 1],
    ["vessel_km_tanker", "Tanker movement", 1],
    ["water_area_km2", "Complete source-cell support water", 2],
    ["analytical_domain_fraction", "Fraction inside analytical domain", 4],
  ] as const;
  return new PopupTemplate({
    title: `${VESSEL_SOURCE.title} — cell {cell_id}`,
    content: [
      {
        type: "fields",
        fieldInfos: fields.map(([name, label, places]) => ({
          fieldName: name,
          label,
          format: { places, digitSeparator: true },
        })),
      },
      {
        type: "text",
        text:
          "Activity density is vessel-km per km² modeled-whale-support water. " +
          "A zero is not verified vessel absence; partial-cell values describe " +
          "the complete source cell and are not rescaled.",
      },
    ],
    outFields: ["cell_id", ...fields.map(([name]) => name)],
  });
}

function createVesselLayer(objectUrl: string): GeoJSONLayer {
  return new GeoJSONLayer({
    id: VESSEL_SOURCE.layerId,
    title: VESSEL_SOURCE.title,
    url: objectUrl,
    geometryType: "polygon",
    spatialReference: { wkid: 4326 },
    objectIdField: VESSEL_SOURCE.objectIdField,
    fields: [
      { name: "object_id", alias: "Display id", type: "oid" },
      { name: "cell_id", alias: "Grid cell", type: "string" },
      {
        name: "vessel_km_per_water_km2_all_commercial",
        alias: "Activity density",
        type: "double",
      },
      {
        name: "vessel_km_all_commercial",
        alias: "All commercial vessel-km",
        type: "double",
      },
      { name: "vessel_km_passenger", alias: "Passenger vessel-km", type: "double" },
      { name: "vessel_km_cargo", alias: "Cargo vessel-km", type: "double" },
      { name: "vessel_km_tanker", alias: "Tanker vessel-km", type: "double" },
      {
        name: "water_area_km2",
        alias: "Source-cell support water (km²)",
        type: "double",
      },
      {
        name: "analytical_domain_area_km2",
        alias: "Area inside domain (km²)",
        type: "double",
      },
      {
        name: "analytical_domain_fraction",
        alias: "Fraction inside domain",
        type: "double",
      },
      { name: "analytical_domain_overlap", alias: "Domain overlap", type: "string" },
    ],
    copyright: VESSEL_SOURCE.attribution,
    renderer: createVesselRenderer(),
    popupTemplate: createVesselPopupTemplate(),
  });
}

function createDomainLayer(objectUrl: string): GeoJSONLayer {
  return new GeoJSONLayer({
    id: DOMAIN_SOURCE.layerId,
    title: DOMAIN_SOURCE.title,
    url: objectUrl,
    geometryType: "polygon",
    spatialReference: { wkid: 4326 },
    objectIdField: DOMAIN_SOURCE.objectIdField,
    fields: [
      { name: "object_id", alias: "Display id", type: "oid" },
      { name: "domain_id", alias: "Domain id", type: "string" },
      { name: "qualification", alias: "Qualification", type: "string" },
      {
        name: "distance_nautical_miles",
        alias: "Receiver distance (nmi)",
        type: "integer",
      },
      { name: "distance_m", alias: "Receiver distance (m)", type: "integer" },
      { name: "measured_from", alias: "Measured from", type: "string" },
      {
        name: "included_water_area_km2",
        alias: "Included support water (km²)",
        type: "double",
      },
      { name: "fully_inside_cell_count", alias: "Full cells", type: "integer" },
      { name: "partly_inside_cell_count", alias: "Partial cells", type: "integer" },
      { name: "wholly_outside_cell_count", alias: "Excluded cells", type: "integer" },
    ],
    copyright: DOMAIN_SOURCE.attribution,
    popupEnabled: false,
    renderer: new SimpleRenderer({
      symbol: new SimpleFillSymbol({
        color: [45, 205, 184, 0.035],
        outline: {
          color: [...DOMAIN_SOURCE.outlineColor],
          width: 2,
          style: "short-dash",
        },
      }),
    }),
  });
}

function createExposureRenderer(method: ExposureMethod): ClassBreaksRenderer {
  const config = exposureMethodConfig(method);
  return new ClassBreaksRenderer({
    field: config.valueField,
    classBreakInfos: config.classes.map((entry) => ({
      minValue: entry.min,
      maxValue: entry.max,
      label: entry.label,
      symbol: new SimpleFillSymbol({
        color: [...entry.color],
        outline: { width: 0 },
      }),
    })),
  });
}

function createExposurePopupTemplate(method: ExposureMethod): PopupTemplate {
  const config = exposureMethodConfig(method);
  return new PopupTemplate({
    title: `${EXPOSURE_SOURCE.title} — cell {${EXPOSURE_SOURCE.featureIdField}}`,
    content: [
      {
        type: "fields",
        fieldInfos: [
          {
            fieldName: config.valueField,
            label: `${config.shortLabel} release-relative index`,
            format: { places: 6, digitSeparator: false },
          },
          {
            fieldName: config.intensityField,
            label: `${config.shortLabel} intensity (${config.intensityUnit})`,
            format: { places: 6, digitSeparator: true },
          },
          {
            fieldName: "qualified_area_km2",
            label: "Receiver-qualified water (km²)",
            format: { places: 3, digitSeparator: true },
          },
          {
            fieldName: "water_area_km2",
            label: "Full source-cell water (km²)",
            format: { places: 3, digitSeparator: true },
          },
        ],
      },
      {
        type: "text",
        text:
          "The map colors use display classes on a release-relative index. " +
          "The p90 field is a separate analytical classification. Blank water " +
          "outside the layer has no analytical coverage, not zero exposure.",
      },
    ],
    outFields: [
      EXPOSURE_SOURCE.featureIdField,
      config.valueField,
      config.intensityField,
      "qualified_area_km2",
      "water_area_km2",
    ],
  });
}

function applyExposureMethod(layer: GeoJSONLayer, method: ExposureMethod): void {
  layer.renderer = createExposureRenderer(method);
  layer.popupTemplate = createExposurePopupTemplate(method);
}

function createExposureLayer(objectUrl: string): GeoJSONLayer {
  const layer = new GeoJSONLayer({
    id: EXPOSURE_SOURCE.layerId,
    title: EXPOSURE_SOURCE.title,
    url: objectUrl,
    geometryType: "polygon",
    spatialReference: { wkid: 4326 },
    objectIdField: EXPOSURE_SOURCE.objectIdField,
    fields: [
      { name: "object_id", alias: "Display id", type: "oid" },
      { name: "cell_id", alias: "Grid cell", type: "string" },
      { name: "water_area_km2", alias: "Full water area (km²)", type: "double" },
      {
        name: "qualified_area_km2",
        alias: "Qualified water area (km²)",
        type: "double",
      },
      { name: "product_intensity", alias: "Product intensity", type: "double" },
      { name: "product_index", alias: "Product index", type: "double" },
      {
        name: "log_traffic_intensity",
        alias: "Log-traffic intensity",
        type: "double",
      },
      { name: "log_traffic_index", alias: "Log-traffic index", type: "double" },
    ],
    copyright: EXPOSURE_SOURCE.attribution,
  });
  applyExposureMethod(layer, "product");
  return layer;
}

function reorderProjectLayers(map: Map): void {
  let index = 0;
  for (const layerId of [
    WHALE_SOURCE.layerId,
    VESSEL_SOURCE.layerId,
    EXPOSURE_SOURCE.layerId,
    DOMAIN_SOURCE.layerId,
    VSR_SOURCE.layerId,
  ]) {
    const layer = map.findLayerById(layerId);
    if (layer) map.reorder(layer, index++);
  }
}

const isWhaleChecksumError = (error: unknown) =>
  error instanceof WhaleLayerChecksumError;
const verifyWhaleLayerBytes = async (bytes: ArrayBuffer) =>
  verifyWhaleLayerChecksum(await sha256Hex(bytes));
const isVesselChecksumError = (error: unknown) =>
  error instanceof VesselLayerChecksumError;
const isDomainChecksumError = (error: unknown) =>
  error instanceof DomainLayerChecksumError;
const isExposurePairingError = (error: unknown) =>
  error instanceof ExposureLayerPairingError;

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
  const [whaleState, dispatchWhale] = useReducer(mapLayerReducer, {
    ...INITIAL_MAP_LAYER_STATE,
    visible: false,
  });
  const [vesselState, dispatchVessel] = useReducer(mapLayerReducer, {
    ...INITIAL_MAP_LAYER_STATE,
    visible: false,
  });
  const [domainState, dispatchDomain] = useReducer(
    mapLayerReducer,
    INITIAL_MAP_LAYER_STATE,
  );
  const [exposureState, dispatchExposure] = useReducer(
    mapLayerReducer,
    INITIAL_MAP_LAYER_STATE,
  );
  const [exposureMethod, setExposureMethod] = useState<ExposureMethod>("product");
  // `null` until a load attempt finishes: true when the bytes were hashed and
  // matched, false when this browser exposes no SubtleCrypto to hash them.
  const [whaleChecksumVerified, setWhaleChecksumVerified] = useState<boolean | null>(
    null,
  );
  const [vesselChecksumVerified, setVesselChecksumVerified] = useState<boolean | null>(
    null,
  );
  const [domainChecksumVerified, setDomainChecksumVerified] = useState<boolean | null>(
    null,
  );
  const [exposureChecksumVerified, setExposureChecksumVerified] = useState<
    boolean | null
  >(null);
  const mapRef = useRef<ArcgisMap | null>(null);
  const vsrLayerRef = useRef<FeatureLayer | null>(null);
  const vsrVisibleRef = useRef(vsrState.visible);
  const whaleLayerRef = useRef<GeoJSONLayer | null>(null);
  const whaleVisibleRef = useRef(whaleState.visible);
  const vesselLayerRef = useRef<GeoJSONLayer | null>(null);
  const vesselVisibleRef = useRef(vesselState.visible);
  const domainLayerRef = useRef<GeoJSONLayer | null>(null);
  const domainVisibleRef = useRef(domainState.visible);
  const exposureLayerRef = useRef<GeoJSONLayer | null>(null);
  const exposureVisibleRef = useRef(exposureState.visible);
  const getMap = useCallback(() => mapRef.current?.map, []);

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
    dispatchVessel({
      type: "map-unavailable",
      warning: VESSEL_MAP_UNAVAILABLE_MESSAGE,
    });
    dispatchDomain({
      type: "map-unavailable",
      warning: DOMAIN_MAP_UNAVAILABLE_MESSAGE,
    });
    dispatchExposure({
      type: "map-unavailable",
      warning: EXPOSURE_MAP_UNAVAILABLE_MESSAGE,
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
      dispatchVessel({
        type: "map-unavailable",
        warning: VESSEL_MAP_UNAVAILABLE_MESSAGE,
      });
      dispatchDomain({
        type: "map-unavailable",
        warning: DOMAIN_MAP_UNAVAILABLE_MESSAGE,
      });
      dispatchExposure({
        type: "map-unavailable",
        warning: EXPOSURE_MAP_UNAVAILABLE_MESSAGE,
      });
    }, INITIALIZATION_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [onSdkAttributionChange, status]);

  // Each project-owned GeoJSON layer has an independent fetch, checksum,
  // timeout, error state, and owned-resource cleanup. A broken activity file
  // cannot remove the whale surface, domain boundary, VSR, or basemap.
  useVerifiedGeoJsonLayer({
    mapIsReady,
    getMap,
    source: WHALE_SOURCE,
    url: whaleLayerUrl,
    visibleRef: whaleVisibleRef,
    layerRef: whaleLayerRef,
    dispatch: dispatchWhale,
    setChecksumVerified: setWhaleChecksumVerified,
    createLayer: createWhaleLayer,
    verifyBytes: verifyWhaleLayerBytes,
    assertFeatureCount: assertExpectedWhaleFeatureCount,
    checksumError: isWhaleChecksumError,
    failureMessage: WHALE_FAILURE_MESSAGE,
    checksumMessage: WHALE_CHECKSUM_MESSAGE,
    mapUnavailableMessage: WHALE_MAP_UNAVAILABLE_MESSAGE,
    loadTimeoutMs: WHALE_LOAD_TIMEOUT_MS,
    afterAdd: reorderProjectLayers,
  });

  useVerifiedGeoJsonLayer({
    mapIsReady,
    getMap,
    source: EXPOSURE_SOURCE,
    url: exposureLayerUrl,
    visibleRef: exposureVisibleRef,
    layerRef: exposureLayerRef,
    dispatch: dispatchExposure,
    setChecksumVerified: setExposureChecksumVerified,
    createLayer: createExposureLayer,
    verifyBytes: verifyConfiguredExposureLayerBytes,
    assertFeatureCount: assertExpectedExposureFeatureCount,
    checksumError: isExposurePairingError,
    failureMessage: EXPOSURE_FAILURE_MESSAGE,
    checksumMessage: EXPOSURE_PAIRING_MESSAGE,
    mapUnavailableMessage: EXPOSURE_MAP_UNAVAILABLE_MESSAGE,
    afterAdd: reorderProjectLayers,
  });

  useVerifiedGeoJsonLayer({
    mapIsReady,
    getMap,
    source: VESSEL_SOURCE,
    url: vesselLayerUrl,
    visibleRef: vesselVisibleRef,
    layerRef: vesselLayerRef,
    dispatch: dispatchVessel,
    setChecksumVerified: setVesselChecksumVerified,
    createLayer: createVesselLayer,
    verifyBytes: verifyVesselLayerBytes,
    assertFeatureCount: assertExpectedVesselFeatureCount,
    checksumError: isVesselChecksumError,
    failureMessage: VESSEL_FAILURE_MESSAGE,
    checksumMessage: VESSEL_CHECKSUM_MESSAGE,
    mapUnavailableMessage: VESSEL_MAP_UNAVAILABLE_MESSAGE,
    afterAdd: reorderProjectLayers,
  });

  useVerifiedGeoJsonLayer({
    mapIsReady,
    getMap,
    source: DOMAIN_SOURCE,
    url: domainLayerUrl,
    visibleRef: domainVisibleRef,
    layerRef: domainLayerRef,
    dispatch: dispatchDomain,
    setChecksumVerified: setDomainChecksumVerified,
    createLayer: createDomainLayer,
    verifyBytes: verifyDomainLayerBytes,
    assertFeatureCount: assertExpectedDomainFeatureCount,
    checksumError: isDomainChecksumError,
    failureMessage: DOMAIN_FAILURE_MESSAGE,
    checksumMessage: DOMAIN_CHECKSUM_MESSAGE,
    mapUnavailableMessage: DOMAIN_MAP_UNAVAILABLE_MESSAGE,
    afterAdd: reorderProjectLayers,
  });

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
          reorderProjectLayers(map);
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

  const handleVesselVisibilityChange = useCallback((visible: boolean) => {
    vesselVisibleRef.current = visible;
    if (vesselLayerRef.current) vesselLayerRef.current.visible = visible;
    dispatchVessel({ type: "visibility-changed", visible });
  }, []);

  const handleDomainVisibilityChange = useCallback((visible: boolean) => {
    domainVisibleRef.current = visible;
    if (domainLayerRef.current) domainLayerRef.current.visible = visible;
    dispatchDomain({ type: "visibility-changed", visible });
  }, []);

  const handleExposureVisibilityChange = useCallback((visible: boolean) => {
    exposureVisibleRef.current = visible;
    if (exposureLayerRef.current) exposureLayerRef.current.visible = visible;
    dispatchExposure({ type: "visibility-changed", visible });
  }, []);

  const handleExposureMethodChange = useCallback((method: ExposureMethod) => {
    setExposureMethod(method);
    if (exposureLayerRef.current) applyExposureMethod(exposureLayerRef.current, method);
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
        <p className={styles.layerHint}>
          Relative exposure is shown by default. Whale and vessel fills start off so the
          result stays readable; turn them on to inspect the inputs. Boundary outlines
          remain above every filled layer.
        </p>
        <ExposureLayerControl
          state={exposureState}
          method={exposureMethod}
          checksumVerified={exposureChecksumVerified}
          onVisibilityChange={handleExposureVisibilityChange}
          onMethodChange={handleExposureMethodChange}
        />
        <WhaleLayerControl
          state={whaleState}
          checksumVerified={whaleChecksumVerified}
          onVisibilityChange={handleWhaleVisibilityChange}
        />
        <VesselLayerControl
          state={vesselState}
          checksumVerified={vesselChecksumVerified}
          onVisibilityChange={handleVesselVisibilityChange}
        />
        <DomainLayerControl
          state={domainState}
          checksumVerified={domainChecksumVerified}
          onVisibilityChange={handleDomainVisibilityChange}
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
