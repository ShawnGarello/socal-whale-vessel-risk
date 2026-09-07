import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import DomainLayerControl from "../components/DomainLayerControl";
import VesselLayerControl from "../components/VesselLayerControl";
import {
  DEFAULT_DOMAIN_LAYER_URL,
  DOMAIN_SOURCE,
  assertExpectedDomainFeatureCount,
  resolveDomainLayerUrl,
  verifyDomainLayerChecksum,
} from "./domain-source";
import type { MapLayerState } from "./map-layer-state";
import {
  DEFAULT_VESSEL_LAYER_URL,
  VESSEL_ACTIVITY_CLASSES,
  VESSEL_SOURCE,
  assertExpectedVesselFeatureCount,
  classifyVesselActivity,
  resolveVesselLayerUrl,
  verifyVesselLayerChecksum,
} from "./vessel-source";

const vesselReady: MapLayerState = {
  status: "ready",
  visible: false,
  featureCount: 2793,
  warning: null,
};
const domainReady: MapLayerState = {
  status: "ready",
  visible: true,
  featureCount: 1,
  warning: null,
};

describe("vessel display source", () => {
  it("binds exact vessel, domain, and export identities", () => {
    expect(VESSEL_SOURCE.exportSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(VESSEL_SOURCE.analysisSourceSha256).toBe(
      "5d3b12982f093e637ebda4a0fbd7ac4a1bb4756c6d1c1c2d3a696d2a0ef688c0",
    );
    expect(VESSEL_SOURCE.qualitySourceSha256).toBe(
      "4d0565af16c15fc9dc176db7b5b14cef99848e7bd48f1a3986dbaca1a5bc9de7",
    );
    expect(VESSEL_SOURCE.analysisProcessedOn).toBe("2026-09-05");
    expect(VESSEL_SOURCE.analysisProcessedOnLabel).toBe("5 September 2026");
    expect(VESSEL_SOURCE.domainSourceSha256).toBe(
      "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77",
    );
    expect(VESSEL_SOURCE.expectedFeatureCount).toBe(2793);
  });

  it("uses a same-origin default and rejects unexpected feature counts", () => {
    expect(DEFAULT_VESSEL_LAYER_URL.startsWith("/layers/")).toBe(true);
    expect(resolveVesselLayerUrl(" ")).toBe(DEFAULT_VESSEL_LAYER_URL);
    expect(resolveVesselLayerUrl("/immutable/vessel.geojson")).toBe(
      "/immutable/vessel.geojson",
    );
    expect(() => assertExpectedVesselFeatureCount(2792)).toThrow(/2792/);
    expect(() => assertExpectedVesselFeatureCount(2793)).not.toThrow();
  });

  it("accepts only the checksum bound to this build", () => {
    expect(verifyVesselLayerChecksum(VESSEL_SOURCE.exportSha256)).toBe(true);
    expect(verifyVesselLayerChecksum(null)).toBe(false);
    expect(() => verifyVesselLayerChecksum("0".repeat(64))).toThrow(
      /Vessel export checksum mismatch/,
    );
  });

  it("keeps zero distinct and covers fixed positive intervals", () => {
    expect(classifyVesselActivity(0)).toBe(VESSEL_ACTIVITY_CLASSES[0]);
    expect(classifyVesselActivity(0.5)).toBe(VESSEL_ACTIVITY_CLASSES[1]);
    expect(classifyVesselActivity(1)).toBe(VESSEL_ACTIVITY_CLASSES[1]);
    expect(classifyVesselActivity(5)).toBe(VESSEL_ACTIVITY_CLASSES[2]);
    expect(classifyVesselActivity(20)).toBe(VESSEL_ACTIVITY_CLASSES[3]);
    expect(classifyVesselActivity(100)).toBe(VESSEL_ACTIVITY_CLASSES[4]);
    expect(classifyVesselActivity(8487.070237441523)).toBe(VESSEL_ACTIVITY_CLASSES[5]);
    expect(classifyVesselActivity(-1)).toBeNull();
    expect(classifyVesselActivity(Number.NaN)).toBeNull();
  });

  it("renders units, caveats, identity, and an initially hidden control", () => {
    const markup = renderToStaticMarkup(
      createElement(VesselLayerControl, {
        state: vesselReady,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );
    expect(markup).toContain("vessel-km / km² modeled-whale-support water");
    expect(markup).toContain("not verified vessel absence");
    expect(markup).toContain("not vessel presence, transit count, or speed");
    expect(markup).toContain("Analytical processing date:");
    expect(markup).toContain('<time dateTime="2026-09-05">5 September 2026</time>');
    expect(markup).toContain("checksum-bound vessel input and quality report below");
    expect(markup).toContain(VESSEL_SOURCE.exportSha256);
    expect(markup).toContain(VESSEL_SOURCE.analysisSourceSha256);
    expect(markup).toContain(VESSEL_SOURCE.qualitySourceSha256);
    expect(markup).not.toContain("checked");
    expect(markup).not.toContain("disabled");
  });
});

describe("accepted analytical-domain source", () => {
  it("binds exact evidence and export identities", () => {
    expect(DOMAIN_SOURCE.exportSha256).toMatch(/^[0-9a-f]{64}$/);
    expect(DOMAIN_SOURCE.evidenceSourceSha256).toBe(
      "4dbb7be45a55d948f820982fcc2e124bf6777b60446692d6e406895a024a9a77",
    );
    expect(DOMAIN_SOURCE.evidenceReportSha256).toBe(
      "eb7963f6ccf625b1547d01ae768dadabfb3f47207d29c24fa5df47e387df5d98",
    );
    expect(DOMAIN_SOURCE.evidenceProcessedOn).toBe("2026-08-29");
    expect(DOMAIN_SOURCE.evidenceProcessedOnLabel).toBe("29 August 2026");
  });

  it("uses a same-origin default and requires the single accepted feature", () => {
    expect(DEFAULT_DOMAIN_LAYER_URL.startsWith("/layers/")).toBe(true);
    expect(resolveDomainLayerUrl(undefined)).toBe(DEFAULT_DOMAIN_LAYER_URL);
    expect(() => assertExpectedDomainFeatureCount(0)).toThrow(/received 0/);
    expect(() => assertExpectedDomainFeatureCount(1)).not.toThrow();
  });

  it("accepts only the checksum bound to this build", () => {
    expect(verifyDomainLayerChecksum(DOMAIN_SOURCE.exportSha256)).toBe(true);
    expect(verifyDomainLayerChecksum(null)).toBe(false);
    expect(() => verifyDomainLayerChecksum("0".repeat(64))).toThrow(
      /Analytical-domain export checksum mismatch/,
    );
  });

  it("renders the receiver qualification and excluded-area warning", () => {
    const markup = renderToStaticMarkup(
      createElement(DomainLayerControl, {
        state: domainReady,
        checksumVerified: true,
        onVisibilityChange: () => undefined,
      }),
    );
    expect(markup).toContain("50 nmi from relevant NAIS stations");
    expect(markup).toContain("Outside = excluded, not low activity");
    expect(markup).toContain("not from the coast");
    expect(markup).toContain("not verified empirical 2024 reception coverage");
    expect(markup).toContain("Domain-evidence processing date:");
    expect(markup).toContain('<time dateTime="2026-08-29">29 August 2026</time>');
    expect(markup).toContain("checksum-bound evidence mask and report below");
    expect(markup).toContain(DOMAIN_SOURCE.exportSha256);
    expect(markup).toContain(DOMAIN_SOURCE.evidenceSourceSha256);
    expect(markup).toContain(DOMAIN_SOURCE.evidenceReportSha256);
    expect(markup).toContain("checked");
  });
});
