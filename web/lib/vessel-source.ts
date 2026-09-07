import { sha256Hex } from "./whale-source";

export interface VesselActivityClass {
  readonly min: number;
  readonly max: number | null;
  readonly label: string;
  readonly color: readonly [number, number, number, number];
}

export const DEFAULT_VESSEL_LAYER_URL = "/layers/commercial-vessel-activity.geojson";

export const VESSEL_ACTIVITY_CLASSES: readonly VesselActivityClass[] = [
  { min: 0, max: 0, label: "zero retained movement", color: [214, 220, 216, 0.7] },
  { min: 0, max: 1, label: "over 0 to 1", color: [218, 240, 214, 0.76] },
  { min: 1, max: 5, label: "over 1 to 5", color: [166, 217, 160, 0.78] },
  { min: 5, max: 20, label: "over 5 to 20", color: [90, 174, 108, 0.8] },
  { min: 20, max: 100, label: "over 20 to 100", color: [35, 139, 69, 0.82] },
  { min: 100, max: null, label: "over 100", color: [0, 88, 36, 0.86] },
];

export const VESSEL_SOURCE = {
  layerId: "project-commercial-vessel-activity",
  title: "Commercial vessel activity",
  objectIdField: "object_id",
  featureIdField: "cell_id",
  valueField: "vessel_km_per_water_km2_all_commercial",
  valueUnit: "vessel-km / km² modeled-whale-support water",
  expectedFeatureCount: 2793,
  exportSha256: "3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288",
  analysisSourceSha256:
    "5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0",
  qualitySourceSha256:
    "4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7",
  analysisProcessedOn: "2026-09-05",
  analysisProcessedOnLabel: "5 September 2026",
  domainSourceSha256:
    "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77",
  classes: VESSEL_ACTIVITY_CLASSES,
  attribution:
    "Vessel activity derived from NOAA Office for Coastal Management / " +
    "Marine Cadastre U.S. Coast Guard National AIS broadcast points.",
  method:
    "Retained passenger, cargo, and tanker movement from 1 July through " +
    "30 November 2024, allocated to the 5 km analysis grid and limited to " +
    "the accepted receiver-qualified analytical domain.",
  statements: [
    "Activity is vessel-kilometres, not vessel presence, transit count, or speed.",
    "The 300-second gap and 30-knot implied-speed ceiling are project quality choices.",
    "The population is type-only; it is not VSR participation or a 300-gross-ton proxy.",
    "Zero means no retained movement in the processed data, not verified vessel absence.",
    "Partial boundary cells keep the complete source-cell value; values are not rescaled.",
    "AIS observational completeness remains unverified. Not for navigation or enforcement.",
    "This layer states no exposure, collision probability, strike prediction, or policy recommendation.",
  ],
  classRationale:
    "Fixed, interpretable activity intervals. The separate neutral zero class keeps " +
    "zero retained movement distinct from excluded water outside the domain.",
} as const;

export function resolveVesselLayerUrl(configured: string | undefined): string {
  const trimmed = configured?.trim();
  return trimmed ? trimmed : DEFAULT_VESSEL_LAYER_URL;
}

export class VesselLayerChecksumError extends Error {
  constructor(readonly actual: string) {
    super(`Vessel export checksum mismatch: received ${actual}.`);
    this.name = "VesselLayerChecksumError";
  }
}

export function verifyVesselLayerChecksum(actual: string | null): boolean {
  if (actual === null) return false;
  if (actual !== VESSEL_SOURCE.exportSha256) throw new VesselLayerChecksumError(actual);
  return true;
}

export async function verifyVesselLayerBytes(bytes: ArrayBuffer): Promise<boolean> {
  return verifyVesselLayerChecksum(await sha256Hex(bytes));
}

export function assertExpectedVesselFeatureCount(featureCount: number): void {
  if (featureCount !== VESSEL_SOURCE.expectedFeatureCount) {
    throw new Error(
      `Expected ${VESSEL_SOURCE.expectedFeatureCount} vessel cells; received ${featureCount}.`,
    );
  }
}

export function classifyVesselActivity(value: number): VesselActivityClass | null {
  if (!Number.isFinite(value) || value < 0) return null;
  if (value === 0) return VESSEL_ACTIVITY_CLASSES[0];
  return (
    VESSEL_ACTIVITY_CLASSES.slice(1).find(
      (entry) => value > entry.min && (entry.max === null || value <= entry.max),
    ) ?? null
  );
}
