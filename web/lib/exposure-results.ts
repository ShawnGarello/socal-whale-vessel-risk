/**
 * Narrow application boundary for the generated M6 results contract.
 *
 * The browser never derives these statistics. This module only validates the
 * one schema M7 supports and selects its generated presentation strings.
 */

export const EXPOSURE_RESULTS_CONTRACT = "relative_exposure_application_results_v1";
export const EXPOSURE_RESULTS_SCHEMA_VERSION = 1;
export const EXPOSURE_RESULTS_SHA256 =
  "ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60";
export const EXPOSURE_RESULTS_ID = "exposure-results-8a0bf6c27e00fb40a13d6870";

type NullableNumber = number | null;
type NullableString = string | null;

export interface ExposureThreshold {
  readonly available: boolean;
  readonly percentile: number;
  readonly threshold: NullableNumber;
  readonly threshold_units: string;
  readonly selected_water_area_km2: NullableNumber;
  readonly inside_share_of_selected_water: NullableNumber;
  readonly outside_share_of_selected_water: NullableNumber;
  readonly unavailable_reason: NullableString;
  readonly presentation: {
    readonly inside_share_percent_1dp: NullableString;
    readonly outside_share_percent_1dp: NullableString;
    readonly selected_water_area_1dp: NullableString;
    readonly threshold_4dp: NullableString;
  };
}

export interface ExposureScenario {
  readonly role: "primary" | "sensitivity";
  readonly method: "product" | "log_traffic";
  readonly grid_resolution_m: 5000 | 10000;
  readonly qualified_cell_count: number;
  readonly excluded_cell_count: number;
  readonly qualified_water_area_km2: number;
  readonly intensity_units: string;
  readonly integrated_exposure: {
    readonly total_qualified: number;
    readonly inside_vsr: number;
    readonly outside_vsr: number;
    readonly inside_share: NullableNumber;
    readonly outside_share: NullableNumber;
    readonly share_denominator: string;
    readonly presentation: {
      readonly inside_share_percent_1dp: NullableString;
      readonly outside_share_percent_1dp: NullableString;
    };
  };
  readonly high_exposure: {
    readonly definition: string;
    readonly area_share_denominator: string;
    readonly all_valid: readonly ExposureThreshold[];
    readonly positive_only_sensitivity: readonly ExposureThreshold[];
  };
}

export interface ExposureResults {
  readonly contract: typeof EXPOSURE_RESULTS_CONTRACT;
  readonly schema_version: typeof EXPOSURE_RESULTS_SCHEMA_VERSION;
  readonly results_id: typeof EXPOSURE_RESULTS_ID;
  readonly generated_at_utc: string;
  readonly scenarios: {
    readonly "5km_product": ExposureScenario;
    readonly "5km_log_traffic": ExposureScenario;
    readonly "10km_product": ExposureScenario;
    readonly "10km_log_traffic": ExposureScenario;
  };
  readonly comparisons: {
    readonly formula_sensitivity_at_5km: {
      readonly inside_share_change: number;
      readonly presentation_change_percentage_points_4dp: string;
      readonly spearman_cell_ranks: number;
      readonly maximum_absolute_rank_change: number;
    };
    readonly grid_resolution_sensitivity: {
      readonly product: GridSensitivity;
      readonly log_traffic: GridSensitivity;
    };
  };
  readonly methods: {
    readonly normalization: string;
    readonly primary: {
      readonly assumption: string;
      readonly formula: string;
      readonly integration_area_basis: string;
      readonly intensity_area_basis: string;
    };
    readonly sensitivity: {
      readonly purpose: string;
      readonly scientific_status: string;
    };
    readonly speed_separation: string;
  };
  readonly nulls_and_exclusions: {
    readonly all_zero: string;
    readonly outside_domain: string;
    readonly zero_movement: string;
    readonly observational_completeness: string;
  };
  readonly scope: {
    readonly analytical_domain: {
      readonly id: string;
      readonly distance_nautical_miles: number;
      readonly distance_m: number;
      readonly empirical_2024_coverage: boolean;
      readonly measured_from: string;
      readonly outside_cell_treatment: string;
      readonly qualification: string;
    };
    readonly vsr_boundary_year: number;
    readonly whale_vintage: string;
  };
  readonly source_references: {
    readonly traffic: { readonly period: string; readonly publisher: string };
    readonly whales: { readonly publisher: string; readonly product: string };
    readonly vsr: { readonly publisher: string; readonly feature: string };
  };
  readonly limitations: readonly string[];
}

interface GridSensitivity {
  readonly presentation_inside_change_percentage_points_4dp: string;
  readonly presentation_integrated_total_percent_change_6dp: string;
  readonly high_area_inside_share_changes: readonly {
    readonly percentile: number;
    readonly presentation_change_percentage_points_4dp: string;
  }[];
}

export class ExposureResultsContractError extends Error {
  constructor(message: string) {
    super(`Exposure results are incompatible: ${message}`);
    this.name = "ExposureResultsContractError";
  }
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ExposureResultsContractError(`${path} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function string(value: unknown, path: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new ExposureResultsContractError(`${path} must be a non-empty string.`);
  }
  return value;
}

function nullableString(value: unknown, path: string): NullableString {
  return value === null ? null : string(value, path);
}

function number(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ExposureResultsContractError(`${path} must be a finite number.`);
  }
  return value;
}

function nullableNumber(value: unknown, path: string): NullableNumber {
  return value === null ? null : number(value, path);
}

function boolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") {
    throw new ExposureResultsContractError(`${path} must be a boolean.`);
  }
  return value;
}

function array(value: unknown, path: string): readonly unknown[] {
  if (!Array.isArray(value)) {
    throw new ExposureResultsContractError(`${path} must be an array.`);
  }
  return value;
}

function validateThreshold(value: unknown, path: string): void {
  const threshold = record(value, path);
  boolean(threshold.available, `${path}.available`);
  number(threshold.percentile, `${path}.percentile`);
  nullableNumber(threshold.threshold, `${path}.threshold`);
  string(threshold.threshold_units, `${path}.threshold_units`);
  nullableNumber(threshold.selected_water_area_km2, `${path}.selected_water_area_km2`);
  nullableNumber(
    threshold.inside_share_of_selected_water,
    `${path}.inside_share_of_selected_water`,
  );
  nullableNumber(
    threshold.outside_share_of_selected_water,
    `${path}.outside_share_of_selected_water`,
  );
  nullableString(threshold.unavailable_reason, `${path}.unavailable_reason`);
  const presentation = record(threshold.presentation, `${path}.presentation`);
  nullableString(
    presentation.inside_share_percent_1dp,
    `${path}.presentation.inside_share_percent_1dp`,
  );
  nullableString(
    presentation.outside_share_percent_1dp,
    `${path}.presentation.outside_share_percent_1dp`,
  );
  nullableString(
    presentation.selected_water_area_1dp,
    `${path}.presentation.selected_water_area_1dp`,
  );
  nullableString(presentation.threshold_4dp, `${path}.presentation.threshold_4dp`);
}

function validateThresholdFamily(value: unknown, path: string): void {
  const thresholds = array(value, path);
  if (thresholds.length !== 3) {
    throw new ExposureResultsContractError(`${path} must contain p80, p90, and p95.`);
  }
  thresholds.forEach((threshold, index) =>
    validateThreshold(threshold, `${path}[${index}]`),
  );
  const percentiles = thresholds.map((threshold) => record(threshold, path).percentile);
  if (percentiles[0] !== 0.8 || percentiles[1] !== 0.9 || percentiles[2] !== 0.95) {
    throw new ExposureResultsContractError(`${path} must be ordered p80, p90, p95.`);
  }
}

function validateScenario(
  value: unknown,
  path: string,
  method: ExposureScenario["method"],
  role: ExposureScenario["role"],
  resolution: ExposureScenario["grid_resolution_m"],
): void {
  const scenario = record(value, path);
  if (scenario.method !== method || scenario.role !== role) {
    throw new ExposureResultsContractError(`${path} has the wrong method or role.`);
  }
  if (scenario.grid_resolution_m !== resolution) {
    throw new ExposureResultsContractError(`${path} has the wrong grid resolution.`);
  }
  number(scenario.qualified_cell_count, `${path}.qualified_cell_count`);
  number(scenario.excluded_cell_count, `${path}.excluded_cell_count`);
  number(scenario.qualified_water_area_km2, `${path}.qualified_water_area_km2`);
  string(scenario.intensity_units, `${path}.intensity_units`);

  const integrated = record(
    scenario.integrated_exposure,
    `${path}.integrated_exposure`,
  );
  number(integrated.total_qualified, `${path}.integrated_exposure.total_qualified`);
  number(integrated.inside_vsr, `${path}.integrated_exposure.inside_vsr`);
  number(integrated.outside_vsr, `${path}.integrated_exposure.outside_vsr`);
  nullableNumber(integrated.inside_share, `${path}.integrated_exposure.inside_share`);
  nullableNumber(integrated.outside_share, `${path}.integrated_exposure.outside_share`);
  string(integrated.share_denominator, `${path}.integrated_exposure.share_denominator`);
  const presentation = record(
    integrated.presentation,
    `${path}.integrated_exposure.presentation`,
  );
  nullableString(
    presentation.inside_share_percent_1dp,
    `${path}.integrated_exposure.presentation.inside_share_percent_1dp`,
  );
  nullableString(
    presentation.outside_share_percent_1dp,
    `${path}.integrated_exposure.presentation.outside_share_percent_1dp`,
  );

  const high = record(scenario.high_exposure, `${path}.high_exposure`);
  string(high.definition, `${path}.high_exposure.definition`);
  string(high.area_share_denominator, `${path}.high_exposure.area_share_denominator`);
  validateThresholdFamily(high.all_valid, `${path}.high_exposure.all_valid`);
  validateThresholdFamily(
    high.positive_only_sensitivity,
    `${path}.high_exposure.positive_only_sensitivity`,
  );
}

function validateGridSensitivity(value: unknown, path: string): void {
  const comparison = record(value, path);
  string(
    comparison.presentation_inside_change_percentage_points_4dp,
    `${path}.presentation_inside_change_percentage_points_4dp`,
  );
  string(
    comparison.presentation_integrated_total_percent_change_6dp,
    `${path}.presentation_integrated_total_percent_change_6dp`,
  );
  const highChanges = array(
    comparison.high_area_inside_share_changes,
    `${path}.high_area_inside_share_changes`,
  );
  if (highChanges.length !== 3) {
    throw new ExposureResultsContractError(
      `${path}.high_area_inside_share_changes must contain p80, p90, and p95.`,
    );
  }
  highChanges.forEach((entry, index) => {
    const item = record(entry, `${path}.high_area_inside_share_changes[${index}]`);
    number(
      item.percentile,
      `${path}.high_area_inside_share_changes[${index}].percentile`,
    );
    string(
      item.presentation_change_percentage_points_4dp,
      `${path}.high_area_inside_share_changes[${index}].presentation_change_percentage_points_4dp`,
    );
  });
  const percentiles = highChanges.map(
    (entry) => record(entry, `${path}.high_area_inside_share_changes`).percentile,
  );
  if (percentiles[0] !== 0.8 || percentiles[1] !== 0.9 || percentiles[2] !== 0.95) {
    throw new ExposureResultsContractError(
      `${path}.high_area_inside_share_changes must be ordered p80, p90, p95.`,
    );
  }
}

/** Validate and narrow the single generated schema supported by this build. */
export function parseExposureResults(value: unknown): ExposureResults {
  const results = record(value, "results");
  if (results.contract !== EXPOSURE_RESULTS_CONTRACT) {
    throw new ExposureResultsContractError(
      `expected contract ${EXPOSURE_RESULTS_CONTRACT}.`,
    );
  }
  if (results.schema_version !== EXPOSURE_RESULTS_SCHEMA_VERSION) {
    throw new ExposureResultsContractError(
      `expected schema version ${EXPOSURE_RESULTS_SCHEMA_VERSION}.`,
    );
  }
  if (results.results_id !== EXPOSURE_RESULTS_ID) {
    throw new ExposureResultsContractError(
      `the results identity does not match this build.`,
    );
  }
  string(results.generated_at_utc, "results.generated_at_utc");

  const scenarios = record(results.scenarios, "results.scenarios");
  validateScenario(
    scenarios["5km_product"],
    "scenarios.5km_product",
    "product",
    "primary",
    5000,
  );
  validateScenario(
    scenarios["5km_log_traffic"],
    "scenarios.5km_log_traffic",
    "log_traffic",
    "sensitivity",
    5000,
  );
  validateScenario(
    scenarios["10km_product"],
    "scenarios.10km_product",
    "product",
    "primary",
    10000,
  );
  validateScenario(
    scenarios["10km_log_traffic"],
    "scenarios.10km_log_traffic",
    "log_traffic",
    "sensitivity",
    10000,
  );

  const comparisons = record(results.comparisons, "results.comparisons");
  const formula = record(
    comparisons.formula_sensitivity_at_5km,
    "results.comparisons.formula_sensitivity_at_5km",
  );
  number(formula.inside_share_change, "formula_sensitivity_at_5km.inside_share_change");
  string(
    formula.presentation_change_percentage_points_4dp,
    "formula_sensitivity_at_5km.presentation_change_percentage_points_4dp",
  );
  number(formula.spearman_cell_ranks, "formula_sensitivity_at_5km.spearman_cell_ranks");
  number(
    formula.maximum_absolute_rank_change,
    "formula_sensitivity_at_5km.maximum_absolute_rank_change",
  );
  const grid = record(
    comparisons.grid_resolution_sensitivity,
    "results.comparisons.grid_resolution_sensitivity",
  );
  validateGridSensitivity(grid.product, "grid_resolution_sensitivity.product");
  validateGridSensitivity(grid.log_traffic, "grid_resolution_sensitivity.log_traffic");

  const methods = record(results.methods, "results.methods");
  string(methods.normalization, "results.methods.normalization");
  const primary = record(methods.primary, "results.methods.primary");
  for (const field of [
    "assumption",
    "formula",
    "integration_area_basis",
    "intensity_area_basis",
  ]) {
    string(primary[field], `results.methods.primary.${field}`);
  }
  const sensitivity = record(methods.sensitivity, "results.methods.sensitivity");
  string(sensitivity.purpose, "results.methods.sensitivity.purpose");
  string(
    sensitivity.scientific_status,
    "results.methods.sensitivity.scientific_status",
  );
  string(methods.speed_separation, "results.methods.speed_separation");

  const nulls = record(results.nulls_and_exclusions, "results.nulls_and_exclusions");
  for (const field of [
    "all_zero",
    "outside_domain",
    "zero_movement",
    "observational_completeness",
  ]) {
    string(nulls[field], `results.nulls_and_exclusions.${field}`);
  }

  const scope = record(results.scope, "results.scope");
  const domain = record(scope.analytical_domain, "results.scope.analytical_domain");
  for (const field of [
    "id",
    "measured_from",
    "outside_cell_treatment",
    "qualification",
  ]) {
    string(domain[field], `results.scope.analytical_domain.${field}`);
  }
  number(
    domain.distance_nautical_miles,
    "results.scope.analytical_domain.distance_nautical_miles",
  );
  number(domain.distance_m, "results.scope.analytical_domain.distance_m");
  boolean(
    domain.empirical_2024_coverage,
    "results.scope.analytical_domain.empirical_2024_coverage",
  );
  number(scope.vsr_boundary_year, "results.scope.vsr_boundary_year");
  string(scope.whale_vintage, "results.scope.whale_vintage");

  const references = record(results.source_references, "results.source_references");
  for (const [name, fields] of [
    ["traffic", ["period", "publisher"]],
    ["whales", ["publisher", "product"]],
    ["vsr", ["publisher", "feature"]],
  ] as const) {
    const reference = record(references[name], `results.source_references.${name}`);
    for (const field of fields)
      string(reference[field], `results.source_references.${name}.${field}`);
  }

  const limitations = array(results.limitations, "results.limitations");
  if (limitations.length === 0) {
    throw new ExposureResultsContractError("results.limitations must not be empty.");
  }
  limitations.forEach((entry, index) => string(entry, `results.limitations[${index}]`));
  return value as ExposureResults;
}

export function parseExposureResultsText(text: string): ExposureResults {
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new ExposureResultsContractError("the bundled JSON is malformed.");
  }
  return parseExposureResults(value);
}

const unavailable = "Not available for this artifact";

function display(value: NullableString): string {
  return value ?? unavailable;
}

function p90(scenario: ExposureScenario): ExposureThreshold {
  const threshold = scenario.high_exposure.all_valid.find(
    (candidate) => candidate.percentile === 0.9,
  );
  if (!threshold) {
    throw new ExposureResultsContractError("the all-valid p90 result is missing.");
  }
  return threshold;
}

export interface ExposureResultsViewModel {
  readonly primary: ScenarioView;
  readonly sensitivity: ScenarioView;
  readonly formulaInsideChangePercentagePoints: string;
  readonly thresholdRows: readonly ThresholdView[];
  readonly positiveOnlyRows: readonly ThresholdView[];
  readonly gridSensitivityRows: readonly GridSensitivityView[];
  readonly limitationPoints: readonly string[];
  readonly resultsId: string;
}

interface ScenarioView {
  readonly insideShareFraction: NullableNumber;
  readonly outsideShareFraction: NullableNumber;
  readonly insideShare: string;
  readonly outsideShare: string;
  readonly p90InsideAreaShareFraction: NullableNumber;
  readonly p90OutsideAreaShareFraction: NullableNumber;
  readonly p90InsideAreaShare: string;
  readonly p90OutsideAreaShare: string;
  readonly p90SelectedArea: string;
  readonly p90Threshold: string;
  readonly p90Available: boolean;
}

interface ThresholdView {
  readonly percentile: "p80" | "p90" | "p95";
  readonly productInside: string;
  readonly logInside: string;
  readonly productThreshold: string;
  readonly logThreshold: string;
}

interface GridSensitivityView {
  readonly measure: string;
  readonly unit: "percentage points" | "percent";
  readonly productChange: string;
  readonly logTrafficChange: string;
}

function scenarioView(scenario: ExposureScenario): ScenarioView {
  const high = p90(scenario);
  return {
    insideShareFraction: scenario.integrated_exposure.inside_share,
    outsideShareFraction: scenario.integrated_exposure.outside_share,
    insideShare: display(
      scenario.integrated_exposure.presentation.inside_share_percent_1dp,
    ),
    outsideShare: display(
      scenario.integrated_exposure.presentation.outside_share_percent_1dp,
    ),
    p90InsideAreaShareFraction: high.inside_share_of_selected_water,
    p90OutsideAreaShareFraction: high.outside_share_of_selected_water,
    p90InsideAreaShare: display(high.presentation.inside_share_percent_1dp),
    p90OutsideAreaShare: display(high.presentation.outside_share_percent_1dp),
    p90SelectedArea: display(high.presentation.selected_water_area_1dp),
    p90Threshold: display(high.presentation.threshold_4dp),
    p90Available: high.available,
  };
}

function thresholdRows(
  product: readonly ExposureThreshold[],
  log: readonly ExposureThreshold[],
): readonly ThresholdView[] {
  return product.map((entry, index) => ({
    percentile: `p${entry.percentile * 100}` as "p80" | "p90" | "p95",
    productInside: display(entry.presentation.inside_share_percent_1dp),
    logInside: display(log[index]?.presentation.inside_share_percent_1dp ?? null),
    productThreshold: display(entry.presentation.threshold_4dp),
    logThreshold: display(log[index]?.presentation.threshold_4dp ?? null),
  }));
}

function gridSensitivityRows(
  product: GridSensitivity,
  logTraffic: GridSensitivity,
): readonly GridSensitivityView[] {
  return [
    {
      measure: "Integrated inside share",
      unit: "percentage points",
      productChange: product.presentation_inside_change_percentage_points_4dp,
      logTrafficChange: logTraffic.presentation_inside_change_percentage_points_4dp,
    },
    {
      measure: "Integrated total",
      unit: "percent",
      productChange: product.presentation_integrated_total_percent_change_6dp,
      logTrafficChange: logTraffic.presentation_integrated_total_percent_change_6dp,
    },
    ...product.high_area_inside_share_changes.map((entry, index) => ({
      measure: `p${entry.percentile * 100} high-area inside share`,
      unit: "percentage points" as const,
      productChange: entry.presentation_change_percentage_points_4dp,
      logTrafficChange:
        logTraffic.high_area_inside_share_changes[index]
          ?.presentation_change_percentage_points_4dp ?? unavailable,
    })),
  ];
}

/** Select display-ready values without recalculating or reformatting numbers. */
export function buildExposureResultsViewModel(
  results: ExposureResults,
): ExposureResultsViewModel {
  const product = results.scenarios["5km_product"];
  const log = results.scenarios["5km_log_traffic"];
  return {
    primary: scenarioView(product),
    sensitivity: scenarioView(log),
    formulaInsideChangePercentagePoints:
      results.comparisons.formula_sensitivity_at_5km
        .presentation_change_percentage_points_4dp,
    thresholdRows: thresholdRows(
      product.high_exposure.all_valid,
      log.high_exposure.all_valid,
    ),
    positiveOnlyRows: thresholdRows(
      product.high_exposure.positive_only_sensitivity,
      log.high_exposure.positive_only_sensitivity,
    ),
    gridSensitivityRows: gridSensitivityRows(
      results.comparisons.grid_resolution_sensitivity.product,
      results.comparisons.grid_resolution_sensitivity.log_traffic,
    ),
    limitationPoints: [
      "Modeled whale habitat, not observed individual whales.",
      `${results.source_references.traffic.period} vessel activity is compared with the ${results.scope.vsr_boundary_year} VSR boundary; the inputs are not contemporaneous encounters.`,
      `The analytical domain is receiver-qualified (${results.scope.analytical_domain.distance_nautical_miles} nautical miles from relevant NAIS stations), not empirically complete AIS coverage.`,
      "Water outside the accepted domain has no analytical coverage; it is not zero exposure or low traffic.",
      `Boundary statistics assume ${results.methods.primary.assumption}.`,
      "The integrated share depends materially on the chosen exposure formula; the log-traffic sensitivity changes the spatial emphasis and the inside/outside result.",
      "Speed remains separate from relative exposure and is available with the vessel description.",
      ...results.limitations,
    ],
    resultsId: results.results_id,
  };
}
