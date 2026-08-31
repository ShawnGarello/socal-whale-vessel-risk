"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import EsriAttribution from "./EsriAttribution";
import styles from "./MapShell.module.css";

/**
 * Client-only boundary for the ArcGIS map.
 *
 * The ArcGIS map components are custom elements. Importing them evaluates code
 * that registers against `window.customElements`, which does not exist while
 * Next.js prerenders this page during `next build`. `ssr: false` keeps the
 * whole SDK out of the prerender and out of the initial HTML, so the map is
 * fetched and initialized only once the page is running in a browser.
 *
 * `ssr: false` is permitted only inside a Client Component, which is why this
 * boundary exists rather than the page importing the map directly.
 */
const ArcgisMapFrame = dynamic(() => import("./ArcgisMapFrame"), {
  ssr: false,
  loading: () => (
    <div className={styles.placeholder} role="status" aria-live="polite">
      Loading the ArcGIS Maps SDK…
    </div>
  ),
});

export default function MapShell() {
  const [sdkAttributionAvailable, setSdkAttributionAvailable] = useState(false);
  const handleSdkAttributionChange = useCallback((available: boolean) => {
    setSdkAttributionAvailable(available);
  }, []);

  return (
    <div className={styles.frame}>
      <ArcgisMapFrame onSdkAttributionChange={handleSdkAttributionChange} />
      {!sdkAttributionAvailable && <EsriAttribution />}
    </div>
  );
}
