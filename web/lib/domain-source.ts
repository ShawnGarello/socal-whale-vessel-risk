import { sha256Hex } from "./whale-source";

export const DEFAULT_DOMAIN_LAYER_URL = "/layers/accepted-analytical-domain.geojson";

export const DOMAIN_SOURCE = {
  layerId: "project-accepted-analytical-domain",
  title: "Accepted analytical domain",
  objectIdField: "object_id",
  expectedFeatureCount: 1,
  exportSha256: "7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf",
  evidenceSourceSha256:
    "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77",
  evidenceReportSha256:
    "eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98",
  evidenceProcessedOn: "2026-08-29",
  evidenceProcessedOnLabel: "29 August 2026",
  outlineColor: [45, 205, 184, 0.98] as const,
  attribution:
    "Analytical-domain evidence uses NOAA OCM AIS Base Stations and the " +
    "U.S. Coast Guard NAVCEN receiver-distance qualification.",
  method:
    "Exact modeled-whale-support water within 50 nautical miles (92,600 m) " +
    "of relevant NAIS reception stations.",
  statements: [
    "The distance is measured from relevant NAIS stations, not from the coast.",
    "This is system-performance-qualified scope, not verified empirical 2024 reception coverage.",
    "Water outside the boundary is excluded from headline statistics; it is not low traffic.",
    "Map/context extent, modeled-whale-support water, and this accepted domain have distinct roles.",
  ],
} as const;

export function resolveDomainLayerUrl(configured: string | undefined): string {
  const trimmed = configured?.trim();
  return trimmed ? trimmed : DEFAULT_DOMAIN_LAYER_URL;
}

export class DomainLayerChecksumError extends Error {
  constructor(readonly actual: string) {
    super(`Analytical-domain export checksum mismatch: received ${actual}.`);
    this.name = "DomainLayerChecksumError";
  }
}

export function verifyDomainLayerChecksum(actual: string | null): boolean {
  if (actual === null) return false;
  if (actual !== DOMAIN_SOURCE.exportSha256) throw new DomainLayerChecksumError(actual);
  return true;
}

export async function verifyDomainLayerBytes(bytes: ArrayBuffer): Promise<boolean> {
  return verifyDomainLayerChecksum(await sha256Hex(bytes));
}

export function assertExpectedDomainFeatureCount(featureCount: number): void {
  if (featureCount !== DOMAIN_SOURCE.expectedFeatureCount) {
    throw new Error(
      `Expected one analytical-domain feature; received ${featureCount}.`,
    );
  }
}
