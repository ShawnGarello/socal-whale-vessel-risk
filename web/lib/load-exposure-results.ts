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

export const EXPOSURE_RESULTS_PUBLIC_ERROR_MESSAGE =
  "The generated relative-exposure results could not be read or verified for this build.";

type ReadResultsFile = (path: string) => Buffer;
type ReportResultsDiagnostic = (message: string, error: unknown) => void;

/** Read and verify the committed results during the static build. */
export function loadExposureResults(
  readResultsFile: ReadResultsFile = (path) => readFileSync(path),
  reportDiagnostic: ReportResultsDiagnostic = (message, error) =>
    console.error(message, error),
): ExposureResultsLoad {
  try {
    const bytes = readResultsFile(
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
    reportDiagnostic("Exposure results failed static-build verification.", error);
    return {
      ok: false,
      message: EXPOSURE_RESULTS_PUBLIC_ERROR_MESSAGE,
    };
  }
}
