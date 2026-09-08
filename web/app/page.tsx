import MapShell from "@/components/MapShell";
import ExposureResultsPanel from "@/components/ExposureResultsPanel";
import { loadExposureResults } from "@/lib/load-exposure-results";
import styles from "./page.module.css";

export default function Home() {
  const exposureResults = loadExposureResults();
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          Southern California whale–vessel spatial overlap
        </h1>
        <p className={styles.subtitle}>
          Explore where modeled blue-whale habitat and commercial vessel activity
          overlap in receiver-qualified Southern California water, and compare that
          relative exposure with the publisher-hosted 2026 Vessel Speed Reduction
          boundary.
        </p>
      </header>
      <main className={styles.main}>
        <section className={styles.mapRegion} aria-labelledby="map-heading">
          <div className={styles.mapIntro}>
            <div>
              <h2 id="map-heading">Explore the surface</h2>
              <p>
                Switch formulas or inspect the whale and vessel inputs. Empty water
                outside the accepted domain means no analytical coverage—not zero
                exposure.
              </p>
            </div>
            <p className={styles.mapStatus}>Relative exposure shown by default</p>
          </div>
          <div className={styles.mapViewport}>
            <MapShell />
          </div>
        </section>
        <div className={styles.resultsRegion}>
          <ExposureResultsPanel load={exposureResults} />
        </div>
      </main>
    </div>
  );
}
