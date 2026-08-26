"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import esriConfig from "@arcgis/core/config.js";
import "@arcgis/map-components/components/arcgis-map";
import "@arcgis/map-components/components/arcgis-zoom";
import type { ArcgisMap } from "@arcgis/map-components/components/arcgis-map";
import {
  INITIAL_VIEWPOINT,
  describeLoadErrors,
  resolveArcgisConfig,
} from "@/lib/arcgis-config";
import styles from "./ArcgisMapFrame.module.css";

/*
 * This module is loaded only in the browser (see MapShell.tsx). The side-effect
 * imports above register the ArcGIS custom elements against
 * `window.customElements`, which does not exist while Next.js prerenders the
 * page during `next build`, so they must never be evaluated on the server.
 */

const config = resolveArcgisConfig({
  // Referenced literally: Next.js inlines `NEXT_PUBLIC_*` at build time and
  // cannot follow an indirect lookup such as `process.env[name]`.
  apiKey: process.env.NEXT_PUBLIC_ARCGIS_API_KEY,
  basemapId: process.env.NEXT_PUBLIC_ARCGIS_BASEMAP,
});

// The SDK requires the key to be set before the first request to a secured
// service. Module scope runs when this chunk is imported, which is before the
// map element below is ever rendered.
if (config.apiKey !== null) {
  esriConfig.apiKey = config.apiKey;
}

// This is an anonymous public application: nobody signs in, and it reads only
// publicly shared content. Left at its default, the SDK answers a rejected
// request by opening its own username/password dialog and waiting, so a missing
// or unauthorized API key appears to the visitor as an indefinite "loading"
// state with a sign-in prompt over it. Turning identity off makes the request
// fail immediately instead, which the states below can report. Verified
// against SDK 5.1: without this, an unauthenticated basemap request returns 401
// and the view never becomes ready.
esriConfig.request.useIdentity = false;

/**
 * How long to wait for the view before calling initialization failed.
 *
 * The SDK does not time out on its own, and not every failure raises an event —
 * so without this a stalled initialization would show "Loading map…" forever.
 * Generous enough for a cold cache on a slow connection; short enough that a
 * visitor is told something is wrong rather than left watching a spinner.
 */
const INITIALIZATION_TIMEOUT_MS = 20_000;

const TIMEOUT_MESSAGE =
  "The map view did not finish initializing within 20 seconds. The ArcGIS Maps " +
  "SDK or the basemap service may be unreachable, or the configured API key may " +
  "not be authorized for the requested basemap.";

type Status = "initializing" | "ready" | "error";

export default function ArcgisMapFrame() {
  const [status, setStatus] = useState<Status>("initializing");
  const [failures, setFailures] = useState<readonly string[]>([]);
  const mapRef = useRef<ArcgisMap | null>(null);

  const handleReadyChange = useCallback(() => {
    const element = mapRef.current;
    if (!element?.ready) return;
    // A view can be ready while a resource inside it failed — a rejected
    // basemap request is the common case. Report that instead of showing an
    // empty map that looks like it worked.
    setFailures(describeLoadErrors(element.loadErrorSources ?? []));
    setStatus("ready");
  }, []);

  const handleReadyError = useCallback(() => {
    const element = mapRef.current;
    const described = describeLoadErrors(element?.loadErrorSources ?? []);
    setFailures(
      described.length > 0
        ? described
        : ["The map view reported an initialization error with no further detail."],
    );
    setStatus("error");
  }, []);

  useEffect(() => {
    if (status !== "initializing") return;
    const timer = window.setTimeout(() => {
      const element = mapRef.current;
      const described = describeLoadErrors(element?.loadErrorSources ?? []);
      setFailures(described.length > 0 ? described : [TIMEOUT_MESSAGE]);
      setStatus("error");
    }, INITIALIZATION_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [status]);

  const problems = [...config.warnings, ...failures];

  return (
    <div className={styles.frame}>
      {/*
       * Unmounting this component removes the element from the document, and
       * the map component destroys its view and associated resources on
       * disconnect (`autoDestroyDisabled` defaults to false). React also
       * detaches the two event listeners below, so no handler can fire against
       * an unmounted component. Do not set `autoDestroyDisabled` without also
       * calling `destroy()` here.
       */}
      <arcgis-map
        ref={mapRef}
        className={styles.map}
        basemap={config.basemapId}
        center={`${INITIAL_VIEWPOINT.center[0]}, ${INITIAL_VIEWPOINT.center[1]}`}
        zoom={INITIAL_VIEWPOINT.zoom}
        onarcgisViewReadyChange={handleReadyChange}
        onarcgisViewReadyError={handleReadyError}
      >
        <arcgis-zoom slot="top-left" />
      </arcgis-map>

      {status === "initializing" && (
        <div className={styles.overlay} role="status" aria-live="polite">
          <p className={styles.overlayTitle}>Loading map…</p>
          <p className={styles.overlayBody}>
            Initializing the ArcGIS map view over the Southern California Bight.
          </p>
        </div>
      )}

      {status === "error" && (
        <div className={styles.overlay} role="alert">
          <p className={styles.overlayTitle}>The map could not be initialized.</p>
          <ul className={styles.reasons}>
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </div>
      )}

      {/*
       * Configuration problems are known before the map finishes trying, so
       * show them straight away rather than making the visitor wait out the
       * initialization timeout to learn the key is missing.
       */}
      {status !== "error" && problems.length > 0 && (
        <div className={styles.notice} role="alert">
          <p className={styles.noticeTitle}>
            {status === "ready"
              ? "The map loaded with problems."
              : "Configuration problem detected."}
          </p>
          <ul className={styles.reasons}>
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
