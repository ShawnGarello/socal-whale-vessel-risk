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
          Compare modeled blue-whale density with retained commercial vessel activity
          inside the accepted receiver-qualified analytical domain. The publisher-hosted
          2026 California Vessel Speed Reduction boundary is reference context. These
          are input layers, not an exposure, risk, or strike result.
        </p>
      </header>
      <main className={styles.main}>
        <MapShell />
      </main>
    </div>
  );
}
