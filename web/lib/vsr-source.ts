/**
 * Publisher-owned source details for the 2026 California VSR zone.
 *
 * The browser references this service directly. No feature geometry is stored,
 * transformed, or republished by this application.
 */
export interface VsrSourceConfig {
  readonly layerId: string;
  readonly title: string;
  readonly serviceUrl: string;
  readonly itemId: string;
  readonly itemUrl: string;
  readonly definitionExpression: "FID = 126";
  readonly expectedFeatureCount: 1;
  readonly attribution: string;
  readonly disclaimer: string;
}

export const VSR_SOURCE: VsrSourceConfig = {
  layerId: "publisher-bwbs-vsr-2026",
  title: "2026 California VSR zone",
  serviceUrl:
    "https://services5.arcgis.com/4biRnCjZju47bNvA/arcgis/rest/services/WhaleAtlas_2026/FeatureServer/0",
  itemId: "b400c7f418b04dc5a9d7ce5015adae32",
  itemUrl: "https://www.arcgis.com/home/item.html?id=b400c7f418b04dc5a9d7ce5015adae32",
  definitionExpression: "FID = 126",
  expectedFeatureCount: 1,
  attribution: "Created by Danielle Alvarez, with CMSF and BWBS.",
  disclaimer:
    "This layer should not be used for navigation purposes. Mariners should " +
    "operate at their own discretion. These measures may not be comprehensive, " +
    "and lack of inclusion does not indicate the absence of a VSR Zone, Area " +
    "to Be Avoided (ATBA), or Traffic Separation Scheme (TSS).",
};

/** Rejects a changed or empty filtered source before it can be called ready. */
export function assertExpectedVsrFeatureCount(featureCount: number): void {
  if (featureCount !== VSR_SOURCE.expectedFeatureCount) {
    throw new Error(
      `Expected ${VSR_SOURCE.expectedFeatureCount} filtered VSR feature; received ${featureCount}.`,
    );
  }
}
