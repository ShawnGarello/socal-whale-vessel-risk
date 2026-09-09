import { sha256Hex, type DigestLike } from "./whale-source";
import {
  EXPOSURE_RESULTS_CONTRACT,
  EXPOSURE_RESULTS_ID,
  EXPOSURE_RESULTS_SHA256,
} from "./exposure-results";

export type ExposureMethod = "product" | "log_traffic";

export const DEFAULT_EXPOSURE_LAYER_URL = "/layers/relative-exposure.geojson";
export const DEFAULT_EXPOSURE_MANIFEST_URL =
  "/layers/relative-exposure.geojson.manifest.json";

export function resolveExposureLayerUrl(configured: string | undefined): string {
  const trimmed = configured?.trim();
  return trimmed ? trimmed : DEFAULT_EXPOSURE_LAYER_URL;
}

export function resolveExposureManifestUrl(configured: string | undefined): string {
  const trimmed = configured?.trim();
  return trimmed ? trimmed : DEFAULT_EXPOSURE_MANIFEST_URL;
}

export interface ExposureDisplayClass {
  readonly min: number;
  readonly max: number;
  readonly label: string;
  readonly color: readonly [number, number, number, number];
}

interface ExposureMethodConfig {
  readonly id: ExposureMethod;
  readonly label: string;
  readonly shortLabel: string;
  readonly valueField: "product_index" | "log_traffic_index";
  readonly intensityField: "product_intensity" | "log_traffic_intensity";
  readonly highField: "product_high_p90" | "log_traffic_high_p90";
  readonly intensityUnit: string;
  readonly classes: readonly ExposureDisplayClass[];
  readonly classificationRationale: string;
}

const COLORS = [
  [43, 51, 59, 0.38],
  [255, 229, 232, 0.76],
  [252, 190, 199, 0.78],
  [239, 126, 148, 0.8],
  [198, 57, 100, 0.83],
  [111, 19, 64, 0.88],
] as const;

const PRODUCT_CLASSES: readonly ExposureDisplayClass[] = [
  { min: 0, max: 0, label: "0", color: COLORS[0] },
  { min: Number.MIN_VALUE, max: 0.0001, label: ">0 to 0.0001", color: COLORS[1] },
  { min: 0.0001, max: 0.001, label: "0.0001 to 0.001", color: COLORS[2] },
  { min: 0.001, max: 0.01, label: "0.001 to 0.01", color: COLORS[3] },
  { min: 0.01, max: 0.1, label: "0.01 to 0.1", color: COLORS[4] },
  { min: 0.1, max: 1, label: "0.1 to 1", color: COLORS[5] },
];

const LOG_CLASSES: readonly ExposureDisplayClass[] = [
  { min: 0, max: 0, label: "0", color: COLORS[0] },
  { min: Number.MIN_VALUE, max: 0.05, label: ">0 to 0.05", color: COLORS[1] },
  { min: 0.05, max: 0.1, label: "0.05 to 0.1", color: COLORS[2] },
  { min: 0.1, max: 0.2, label: "0.1 to 0.2", color: COLORS[3] },
  { min: 0.2, max: 0.4, label: "0.2 to 0.4", color: COLORS[4] },
  { min: 0.4, max: 1, label: "0.4 to 1", color: COLORS[5] },
];

export const EXPOSURE_SOURCE = {
  layerId: "project-relative-exposure-grid",
  title: "Relative exposure",
  objectIdField: "object_id",
  featureIdField: "cell_id",
  expectedFeatureCount: 2793,
  displaySha256: "1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb",
  manifestSha256: "0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0",
  resultsId: EXPOSURE_RESULTS_ID,
  resultsSha256: EXPOSURE_RESULTS_SHA256,
  methods: {
    product: {
      id: "product",
      label: "Proportional product (primary)",
      shortLabel: "Product",
      valueField: "product_index",
      intensityField: "product_intensity",
      highField: "product_high_p90",
      intensityUnit: "modeled animals × vessel-km / km⁴, period total",
      classes: PRODUCT_CLASSES,
      classificationRationale:
        "Log-spaced breaks reveal the strongly skewed release-relative product index. " +
        "They are display classes, not the analytical high-exposure threshold.",
    },
    log_traffic: {
      id: "log_traffic",
      label: "Log-traffic sensitivity",
      shortLabel: "Log traffic",
      valueField: "log_traffic_index",
      intensityField: "log_traffic_intensity",
      highField: "log_traffic_high_p90",
      intensityUnit: "dimensionless sensitivity intensity",
      classes: LOG_CLASSES,
      classificationRationale:
        "Sequential breaks span the broader log-traffic index distribution. They are " +
        "display classes, not the analytical high-exposure threshold.",
    },
  } satisfies Record<ExposureMethod, ExposureMethodConfig>,
  attribution:
    "Relative exposure: project analysis combining NOAA/SWFSC modeled blue-whale " +
    "density with NOAA OCM / U.S. Coast Guard Nationwide AIS vessel activity.",
  statements: [
    "The index is relative to this release's qualified-domain maximum and cannot be compared across releases without that reference.",
    "Blank water outside the displayed cells has no analytical coverage; it is not zero exposure.",
    "The proportional product and log-traffic sensitivity answer different versions of the overlap question.",
    "This is modeled whale–vessel overlap, not collision probability, predicted strikes, VSR effectiveness, or a policy recommendation.",
  ],
} as const;

export class ExposureLayerPairingError extends Error {
  constructor(message: string) {
    super(`The relative-exposure artifacts do not match: ${message}`);
    this.name = "ExposureLayerPairingError";
  }
}

interface FetchResponseLike {
  readonly ok: boolean;
  readonly status: number;
  arrayBuffer(): Promise<ArrayBuffer>;
}

type FetchLike = (
  url: string,
  options: { readonly cache: "no-store" },
) => Promise<FetchResponseLike>;

function object(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ExposureLayerPairingError(`${path} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function exact(value: unknown, expected: unknown, path: string): void {
  if (value !== expected) {
    throw new ExposureLayerPairingError(`${path} is incompatible with this build.`);
  }
}

/** Validate only the M6 display-manifest shape and exact pairing M7 consumes. */
export function validateExposureManifest(value: unknown): void {
  const manifest = object(value, "manifest");
  exact(
    manifest.contract,
    "relative_exposure_display_manifest_v1",
    "manifest.contract",
  );
  exact(manifest.processing_version, "1.0.0", "manifest.processing_version");
  exact(
    manifest.dataset_contract,
    "relative_exposure_display_v1",
    "manifest.dataset_contract",
  );

  const output = object(manifest.output, "manifest.output");
  exact(output.name, "relative-exposure.geojson", "manifest.output.name");
  exact(output.media_type, "application/geo+json", "manifest.output.media_type");
  exact(
    output.feature_count,
    EXPOSURE_SOURCE.expectedFeatureCount,
    "manifest.output.feature_count",
  );
  exact(
    output.unique_cell_count,
    EXPOSURE_SOURCE.expectedFeatureCount,
    "manifest.output.unique_cell_count",
  );
  exact(output.sha256, EXPOSURE_SOURCE.displaySha256, "manifest.output.sha256");

  const geometry = object(manifest.geometry, "manifest.geometry");
  exact(geometry.display_crs, "EPSG:4326", "manifest.geometry.display_crs");
  exact(
    geometry.meaning,
    "exact receiver-domain-qualified 5 km water geometry",
    "manifest.geometry.meaning",
  );
  exact(geometry.vsr_geometry, "not_included", "manifest.geometry.vsr_geometry");

  const results = object(manifest.results, "manifest.results");
  exact(results.contract, EXPOSURE_RESULTS_CONTRACT, "manifest.results.contract");
  exact(results.results_id, EXPOSURE_SOURCE.resultsId, "manifest.results.results_id");
  exact(results.sha256, EXPOSURE_SOURCE.resultsSha256, "manifest.results.sha256");

  const classification = object(manifest.classification, "manifest.classification");
  for (const [method, field] of [
    ["product", "product_high_p90"],
    ["log_traffic", "log_traffic_high_p90"],
  ] as const) {
    const entry = object(classification[method], `manifest.classification.${method}`);
    exact(entry.available, true, `manifest.classification.${method}.available`);
    exact(entry.percentile, 0.9, `manifest.classification.${method}.percentile`);
    exact(entry.reference, "all_valid", `manifest.classification.${method}.reference`);
    exact(entry.field, field, `manifest.classification.${method}.field`);
    if (typeof entry.threshold !== "number" || !Number.isFinite(entry.threshold)) {
      throw new ExposureLayerPairingError(
        `manifest.classification.${method}.threshold must be finite.`,
      );
    }
  }
}

/**
 * Verify the manifest identity, its results binding, and the exact display
 * bytes before the existing GeoJSON lifecycle creates an ArcGIS layer.
 */
export async function verifyExposureLayerBytes(
  displayBytes: ArrayBuffer,
  fetchManifest: FetchLike = (url, options) => fetch(url, options),
  subtle?: DigestLike | null,
  manifestUrl = DEFAULT_EXPOSURE_MANIFEST_URL,
): Promise<boolean> {
  const response = await fetchManifest(manifestUrl, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new ExposureLayerPairingError(
      `the manifest request returned HTTP ${response.status}.`,
    );
  }
  const manifestBytes = await response.arrayBuffer();
  const [manifestSha256, displaySha256] = await Promise.all([
    sha256Hex(manifestBytes, subtle),
    sha256Hex(displayBytes, subtle),
  ]);
  if (manifestSha256 !== null && manifestSha256 !== EXPOSURE_SOURCE.manifestSha256) {
    throw new ExposureLayerPairingError(
      `manifest checksum ${manifestSha256} does not match ${EXPOSURE_SOURCE.manifestSha256}.`,
    );
  }

  let manifest: unknown;
  try {
    manifest = JSON.parse(new TextDecoder().decode(manifestBytes));
  } catch {
    throw new ExposureLayerPairingError("the display manifest is malformed JSON.");
  }
  validateExposureManifest(manifest);

  if (displaySha256 !== null && displaySha256 !== EXPOSURE_SOURCE.displaySha256) {
    throw new ExposureLayerPairingError(
      `display checksum ${displaySha256} does not match ${EXPOSURE_SOURCE.displaySha256}.`,
    );
  }
  return manifestSha256 !== null && displaySha256 !== null;
}

export function assertExpectedExposureFeatureCount(featureCount: number): void {
  if (featureCount !== EXPOSURE_SOURCE.expectedFeatureCount) {
    throw new Error(
      `Expected ${EXPOSURE_SOURCE.expectedFeatureCount} qualified exposure cells; received ${featureCount}.`,
    );
  }
}

export function exposureMethodConfig(method: ExposureMethod): ExposureMethodConfig {
  return EXPOSURE_SOURCE.methods[method];
}
