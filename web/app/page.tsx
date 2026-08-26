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
          Application foundation. The map below shows a basemap only — no project layers
          have been published yet, and nothing shown here is an analytical result.
        </p>
      </header>
      <main className={styles.main}>
        <MapShell />
      </main>
    </div>
  );
}
