/**
 * Display configuration for the project-derived modeled blue-whale layer.
 *
 * The browser reads one deterministic GeoJSON export of the validated whale
 * grid. Nothing here computes, rescales, or reclassifies an analytical value:
 * the class breaks below are a stated display choice, and every number the map
 * shows comes from the export unchanged.
 *
 * The identities recorded here bind this build to one exact artifact. If the
 * export changes, this file changes with it in the same release.
 */

/** Class break on modeled density, in animals per square kilometre. */
export interface WhaleDensityClass {
  /** Inclusive lower bound. */
  readonly min: number;
  /** Exclusive upper bound; `null` means the open top class. */
  readonly max: number | null;
  /** Legend text, already carrying its unit context. */
  readonly label: string;
  /** Fill colour as `[r, g, b, a]`. */
  readonly color: readonly [number, number, number, number];
}

export interface WhaleFieldDescription {
  readonly name: string;
  readonly label: string;
  readonly unit: string;
  readonly decimals: number;
}

export interface WhaleSourceConfig {
  readonly layerId: string;
  readonly title: string;
  readonly objectIdField: string;
  readonly featureIdField: string;
  readonly valueField: string;
  readonly valueUnit: string;
  readonly expectedFeatureCount: number;
  readonly exportSha256: string;
  readonly analysisSourceSha256: string;
  readonly classes: readonly WhaleDensityClass[];
  readonly popupFields: readonly WhaleFieldDescription[];
  readonly attribution: string;
  readonly citations: readonly string[];
  readonly method: string;
  readonly statements: readonly string[];
  readonly classificationRationale: string;
}

/**
 * Default same-origin location the exporter stages into.
 *
 * A release that publishes a checksum-addressed filename overrides this with
 * `NEXT_PUBLIC_WHALE_LAYER_URL` at build time, so an immutable artifact URL can
 * never be confused with a mutable one.
 */
export const DEFAULT_WHALE_LAYER_URL = "/layers/blue-whale-density.geojson";

/**
 * Class breaks on modeled density, in animals/km².
 *
 * **This is a display choice, not an analytical result.** The breaks are equal
 * 0.001 animals/km² intervals with an open lowest and highest class, chosen
 * over quantiles so the legend reads in the model's own units and so two maps
 * of different subsets stay comparable. Against the exported surface (range
 * 0.000834 to 0.007648 animals/km²) the five classes hold 24.4%, 30.7%, 16.9%,
 * 11.7% and 16.2% of the 4,516 cells, so no class is empty and none dominates.
 *
 * The ramp is a single-hue purple sequence, kept clear of the blue basemap and
 * of the orange VSR outline that must stay legible above the fill.
 */
export const WHALE_DENSITY_CLASSES: readonly WhaleDensityClass[] = [
  {
    min: 0,
    max: 0.002,
    label: "under 0.002",
    color: [231, 212, 238, 0.75],
  },
  {
    min: 0.002,
    max: 0.003,
    label: "0.002 to 0.003",
    color: [195, 154, 214, 0.75],
  },
  {
    min: 0.003,
    max: 0.004,
    label: "0.003 to 0.004",
    color: [156, 102, 187, 0.78],
  },
  {
    min: 0.004,
    max: 0.005,
    label: "0.004 to 0.005",
    color: [116, 57, 155, 0.8],
  },
  {
    min: 0.005,
    max: null,
    label: "0.005 and above",
    color: [75, 29, 110, 0.82],
  },
];

export const WHALE_SOURCE: WhaleSourceConfig = {
  layerId: "project-blue-whale-density-grid",
  title: "Modeled blue-whale density",
  objectIdField: "object_id",
  featureIdField: "cell_id",
  valueField: "modeled_density_animals_per_km2",
  valueUnit: "animals/km²",

  // Bound to one exact artifact. `blue_whale_display_export_v1` produced this
  // GeoJSON from `blue_whale_grid_transfer_v1` source
  // 421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62.
  expectedFeatureCount: 4516,
  exportSha256: "831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154",
  analysisSourceSha256:
    "421dc7bf837de1b328328d61944bfb7fa0c7e3c77ac0489ab47506a060520c62",

  classes: WHALE_DENSITY_CLASSES,
  popupFields: [
    {
      name: "modeled_density_animals_per_km2",
      label: "Modeled density",
      unit: "animals/km²",
      decimals: 6,
    },
    {
      name: "modeled_abundance_allocation_animals",
      label: "Modeled abundance allocated to this cell",
      unit: "animals",
      decimals: 6,
    },
    {
      name: "water_area_km2",
      label: "Supporting water area",
      unit: "km²",
      decimals: 3,
    },
    {
      name: "source_coverage_fraction",
      label: "Source-model support",
      unit: "of the cell's water area",
      decimals: 4,
    },
  ],

  attribution:
    "Modeled blue-whale density: NOAA Fisheries / NMFS Office of Science and " +
    "Technology (SWFSC), Predictive Models of Cetacean Densities in the " +
    "California Current Ecosystem, 2020b.",
  citations: [
    "Becker EA, Forney KA, Miller DL, Fiedler PC, Barlow J, Moore JE. 2020. " +
      "Habitat-based density estimates for cetaceans in the California Current " +
      "Ecosystem based on 1991-2018 survey data. NOAA Technical Memorandum " +
      "NMFS-SWFSC-638. https://doi.org/10.25923/3znq-yx13",
    "NMFS Office of Science and Technology, 2026: Predictive Models of Cetacean " +
      "Densities in the California Current Ecosystem, 2020b, " +
      "https://www.fisheries.noaa.gov/inport/item/64349",
  ],
  method:
    "Source layer Blue_whale_summer_fall, retrieved 2026-08-25, transferred to " +
    "this project's 5 km EPSG:3310 analysis grid by abundance-conserving " +
    "area weighting, then exported to WGS 84 GeoJSON without simplification.",

  // These restate the project's scientific-communication rules at the point a
  // reader meets the layer, rather than in a document they will not open.
  statements: [
    "These are modeled densities, not observed whales and not sightings.",
    "The source model is a single multi-year summer–fall average, so this " +
      "layer supports no monthly or seasonal claim.",
    "The 5 km cells are a reporting grid. They do not improve the roughly " +
      "0.1-degree resolution of the source model.",
    "The source model's per-cell uncertainty is not propagated into this layer " +
      "and is not shown.",
    "This layer shows modeled habitat only. It states no vessel exposure, no " +
      "collision probability, and no strike risk.",
  ],
  classificationRationale:
    "Five equal 0.001 animals/km² classes with an open lowest and highest " +
    "class. A display choice, stated so the map can be read against the " +
    "model's own units.",
};

/**
 * Resolves the layer URL, treating blank configuration as unset.
 *
 * Callers must reference `process.env.NEXT_PUBLIC_*` literally at the call
 * site — Next.js inlines those at build time and cannot follow an indirect
 * lookup.
 */
export function resolveWhaleLayerUrl(configured: string | undefined): string {
  if (typeof configured !== "string") return DEFAULT_WHALE_LAYER_URL;
  const trimmed = configured.trim();
  return trimmed.length > 0 ? trimmed : DEFAULT_WHALE_LAYER_URL;
}

/**
 * Raised when the file served does not match the checksum this build expects.
 *
 * The layer URL is build-time configurable and a feature count is not an
 * identity: a different file with the same number of features would otherwise
 * be displayed under this build's recorded checksum. Verifying the bytes is
 * what makes the identity shown in the interface true.
 */
export class WhaleLayerChecksumError extends Error {
  constructor(
    readonly expected: string,
    readonly actual: string,
  ) {
    super(
      `The modeled blue-whale density file does not match the checksum this ` +
        `build expects. Expected ${expected}; received ${actual}.`,
    );
    this.name = "WhaleLayerChecksumError";
  }
}

/** Minimal digest surface, so verification can be tested without a browser. */
export interface DigestLike {
  digest(algorithm: string, data: ArrayBuffer): Promise<ArrayBuffer>;
}

/**
 * SHA-256 of the supplied bytes as lowercase hex, or `null` when the browser
 * exposes no `SubtleCrypto`.
 *
 * `crypto.subtle` is only available in a secure context. HTTPS and localhost
 * both qualify, so the deployed application and local development can verify;
 * anything else reports honestly that it could not, rather than pretending.
 */
export async function sha256Hex(
  bytes: ArrayBuffer,
  subtle?: DigestLike | null,
): Promise<string | null> {
  // Resolved in the body rather than as a default argument, so passing `null`
  // means "no digest available" instead of silently falling back to the
  // platform's.
  const digester = subtle === undefined ? globalThis.crypto?.subtle : subtle;
  if (!digester) return null;
  const digest = await digester.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Compares a computed checksum with the one this build records.
 *
 * Returns whether verification actually happened. A mismatch throws, so the
 * layer fails rather than rendering unknown bytes under a known identity.
 */
export function verifyWhaleLayerChecksum(actual: string | null): boolean {
  if (actual === null) return false;
  if (actual !== WHALE_SOURCE.exportSha256) {
    throw new WhaleLayerChecksumError(WHALE_SOURCE.exportSha256, actual);
  }
  return true;
}

/** Rejects a truncated, empty, or otherwise unexpected export before display. */
export function assertExpectedWhaleFeatureCount(featureCount: number): void {
  if (featureCount !== WHALE_SOURCE.expectedFeatureCount) {
    throw new Error(
      `Expected ${WHALE_SOURCE.expectedFeatureCount} whale grid cells; ` +
        `received ${featureCount}.`,
    );
  }
}

/**
 * Returns the class a modeled density falls in, or `null` when it falls
 * outside every class. A value outside the ramp is a defect worth surfacing,
 * not something to clamp silently.
 */
export function classifyDensity(value: number): WhaleDensityClass | null {
  if (!Number.isFinite(value)) return null;
  return (
    WHALE_DENSITY_CLASSES.find(
      (entry) => value >= entry.min && (entry.max === null || value < entry.max),
    ) ?? null
  );
}
