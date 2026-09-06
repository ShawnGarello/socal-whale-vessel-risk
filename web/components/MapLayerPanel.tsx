import type { ReactNode } from "react";
import styles from "./MapLayerPanel.module.css";

/**
 * Container for the map's operational layer controls.
 *
 * Layer controls stack inside one panel so they share a scroll boundary and
 * cannot drift over the ArcGIS zoom controls or the SDK attribution as more
 * layers arrive.
 */
export default function MapLayerPanel({ children }: { children: ReactNode }) {
  return (
    <section className={styles.panel} aria-label="Map layers">
      {children}
    </section>
  );
}
