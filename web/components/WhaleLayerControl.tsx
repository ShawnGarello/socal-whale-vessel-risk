import type { MapLayerState } from "@/lib/map-layer-state";
import { WHALE_SOURCE } from "@/lib/whale-source";
import styles from "./MapLayerPanel.module.css";

interface WhaleLayerControlProps {
  state: MapLayerState;
  /**
   * Whether the displayed file's bytes were hashed and matched this build's
   * recorded checksum. `null` before a load attempt finishes, `false` when the
   * browser exposes no SubtleCrypto to hash them with.
   */
  checksumVerified: boolean | null;
  onVisibilityChange: (visible: boolean) => void;
}

const STATUS_LABELS = {
  waiting: "Waiting for map",
  loading: "Loading density grid",
  ready: "Density grid loaded",
  error: "Density grid unavailable",
} as const;

function swatchColor(color: readonly [number, number, number, number]): string {
  const [red, green, blue, alpha] = color;
  return `rgb(${red} ${green} ${blue} / ${alpha * 100}%)`;
}

export default function WhaleLayerControl({
  state,
  checksumVerified,
  onVisibilityChange,
}: WhaleLayerControlProps) {
  const interactionDisabled = state.status !== "ready";

  return (
    <div className={styles.section}>
      <label className={styles.visibilityRow}>
        <input
          className={styles.checkbox}
          type="checkbox"
          checked={state.visible}
          disabled={interactionDisabled}
          onChange={(event) => onVisibilityChange(event.currentTarget.checked)}
        />
        <span>
          <span className={styles.label}>{WHALE_SOURCE.title}</span>
          <span className={styles.status} aria-live="polite">
            {STATUS_LABELS[state.status]}
            {state.featureCount !== null &&
              ` · ${state.featureCount.toLocaleString("en-US")} grid cells`}
          </span>
        </span>
      </label>

      <div className={styles.legend}>
        <span className={styles.legendUnit}>
          Modeled density ({WHALE_SOURCE.valueUnit})
        </span>
        <ul className={styles.legendScale}>
          {WHALE_SOURCE.classes.map((entry) => (
            <li className={styles.legendClass} key={entry.label}>
              <span
                className={styles.legendSwatch}
                style={{ background: swatchColor(entry.color) }}
                aria-hidden="true"
              />
              <span>{entry.label}</span>
            </li>
          ))}
        </ul>
      </div>

      {state.warning && (
        <p className={styles.warning} role="alert">
          {state.warning}
        </p>
      )}

      <details className={styles.details}>
        <summary>Whale layer source and method</summary>
        <div className={styles.detailsBody}>
          <p>{WHALE_SOURCE.attribution}</p>
          <p>{WHALE_SOURCE.method}</p>
          <p>{WHALE_SOURCE.classificationRationale}</p>
          <ul>
            {WHALE_SOURCE.statements.map((statement) => (
              <li key={statement}>{statement}</li>
            ))}
          </ul>
          <p>Requested citations:</p>
          <ul>
            {WHALE_SOURCE.citations.map((citation) => (
              <li key={citation}>{citation}</li>
            ))}
          </ul>
          <p>
            {checksumVerified === true
              ? "Displayed export SHA-256, verified against the bytes this browser loaded:"
              : checksumVerified === false
                ? "Expected export SHA-256. This browser could not compute a checksum, so the displayed file's identity is unverified:"
                : "Expected export SHA-256:"}{" "}
            <span className={styles.identity}>{WHALE_SOURCE.exportSha256}</span>
          </p>
          <p>
            Derived from validated analysis output{" "}
            <span className={styles.identity}>{WHALE_SOURCE.analysisSourceSha256}</span>
            .
          </p>
        </div>
      </details>
    </div>
  );
}
