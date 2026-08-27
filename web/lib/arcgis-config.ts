/**
 * Runtime configuration for the ArcGIS map, and the initial map viewpoint.
 *
 * Everything here is presentational. Nothing in this file defines, constrains,
 * or describes the analytical study area, the analysis grid, or any layer.
 */

/**
 * Initial map viewpoint, in WGS 84 decimal degrees.
 *
 * **This display setting is not an analytical boundary.** It positions the
 * initial view roughly over the Southern California Bight so the empty shell
 * opens somewhere relevant. The map and context extent is settled enough to
 * build against, and data discovery accepted EPSG:3310 and a 5 km analysis grid
 * (ADRs 0003 and 0004). The analytical and statistical domain remains open in
 * ADR 0002. These coordinates do not define it and must not be reused as an
 * analytical boundary.
 */
export const INITIAL_VIEWPOINT = {
  /** Longitude, latitude. */
  center: [-119.4, 33.6],
  /** Whole-region zoom level; roughly Point Conception to the Mexican border. */
  zoom: 7,
} as const;

/** Basemap style id used when `NEXT_PUBLIC_ARCGIS_BASEMAP` is not set. */
export const DEFAULT_BASEMAP_ID = "arcgis/oceans";

/** Raw environment values the application reads. */
export interface ArcgisEnv {
  apiKey?: string;
  basemapId?: string;
}

/** Resolved configuration, plus anything the operator should know about it. */
export interface ArcgisConfig {
  /** `null` when unset — the map then loads without an access token. */
  apiKey: string | null;
  basemapId: string;
  /** Configuration problems worth showing in the interface. */
  warnings: string[];
}

/** Treats blank and whitespace-only environment values as unset. */
function clean(value: string | undefined): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

/**
 * Resolves environment values into the configuration the map component uses.
 *
 * Pure, so the resolution rules can be tested without a browser or a build.
 * Callers must reference `process.env.NEXT_PUBLIC_*` literally at the call site
 * — Next.js inlines those at build time and cannot follow an indirect lookup.
 */
export function resolveArcgisConfig(env: ArcgisEnv): ArcgisConfig {
  const warnings: string[] = [];

  const apiKey = clean(env.apiKey);
  if (apiKey === null) {
    warnings.push(
      "NEXT_PUBLIC_ARCGIS_API_KEY is not set. Basemap requests are sent without " +
        "an access token and the ArcGIS basemap styles service will reject them.",
    );
  } else if (/\s/.test(apiKey)) {
    warnings.push(
      "NEXT_PUBLIC_ARCGIS_API_KEY contains whitespace. Check for a stray line " +
        "break or surrounding quotes in the environment value.",
    );
  }

  const basemapId = clean(env.basemapId) ?? DEFAULT_BASEMAP_ID;

  return { apiKey, basemapId, warnings };
}

/** Shape of the component's `loadErrorSources` entries that this app reads. */
export interface LoadErrorLike {
  loadError?: { message?: string } | null;
  title?: string | null;
  type?: string | null;
}

/**
 * Turns the map component's `loadErrorSources` into short lines for the
 * interface. Sources with no usable message are reported rather than dropped,
 * so a silent failure never looks like a success.
 */
export function describeLoadErrors(sources: readonly LoadErrorLike[]): string[] {
  return sources.map((source) => {
    const label = clean(source.title ?? undefined) ?? clean(source.type ?? undefined);
    const message = clean(source.loadError?.message ?? undefined);
    if (label && message) return `${label}: ${message}`;
    if (message) return message;
    if (label) return `${label}: failed to load, with no reported reason.`;
    return "A map resource failed to load, with no reported reason.";
  });
}
