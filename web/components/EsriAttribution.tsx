import styles from "./EsriAttribution.module.css";

/**
 * Application-level Esri attribution for states in which the SDK cannot yet
 * provide its automatic map and data attribution.
 */
export default function EsriAttribution() {
  return <p className={styles.attribution}>Powered by Esri</p>;
}
