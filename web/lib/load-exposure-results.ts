import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  EXPOSURE_RESULTS_SHA256,
  ExposureResultsContractError,
  parseExposureResultsText,
  type ExposureResults,
} from "./exposure-results";

export type ExposureResultsLoad =
  | { readonly ok: true; readonly results: ExposureResults; readonly sha256: string }
  | { readonly ok: false; readonly message: string };

/** Read and verify the committed results during the static build. */
export function loadExposureResults(): ExposureResultsLoad {
  try {
    const bytes = readFileSync(
      resolve(process.cwd(), "../results/exposure-results.v1.json"),
    );
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    if (sha256 !== EXPOSURE_RESULTS_SHA256) {
      throw new ExposureResultsContractError(
        `the bundled file checksum is ${sha256}, expected ${EXPOSURE_RESULTS_SHA256}.`,
      );
    }
    return {
      ok: true,
      results: parseExposureResultsText(bytes.toString("utf8")),
      sha256,
    };
  } catch (error) {
    return {
      ok: false,
      message:
        error instanceof Error
          ? error.message
          : "Exposure results could not be read or verified.",
    };
  }
}
