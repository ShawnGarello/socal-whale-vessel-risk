import MapShell from "@/components/MapShell";
import styles from "./page.module.css";

export default function Home() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          Southern California whale–vessel spatial overlap
        </h1>
        <p className={styles.subtitle}>
          The map shows this project&rsquo;s modeled blue-whale density grid, derived
          from the NOAA/SWFSC 2020b summer&ndash;fall model, together with the
          publisher-hosted 2026 California Vessel Speed Reduction boundary. The
          whale&ndash;vessel exposure analysis is not finished: nothing shown here is an
          exposure, risk, or strike result.
        </p>
      </header>
      <main className={styles.main}>
        <MapShell />
      </main>
    </div>
  );
}
