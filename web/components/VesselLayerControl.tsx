import type { MapLayerState } from "@/lib/map-layer-state";
import { VESSEL_SOURCE } from "@/lib/vessel-source";
import styles from "./MapLayerPanel.module.css";

interface VesselLayerControlProps {
  state: MapLayerState;
  checksumVerified: boolean | null;
  onVisibilityChange: (visible: boolean) => void;
}

const STATUS_LABELS = {
  waiting: "Waiting for map",
  loading: "Loading activity grid",
  ready: "Activity grid loaded",
  error: "Activity grid unavailable",
} as const;

function swatchColor(color: readonly [number, number, number, number]): string {
  const [red, green, blue, alpha] = color;
  return `rgb(${red} ${green} ${blue} / ${alpha * 100}%)`;
}

export default function VesselLayerControl({
  state,
  checksumVerified,
  onVisibilityChange,
}: VesselLayerControlProps) {
  return (
    <div className={styles.section}>
      <label className={styles.visibilityRow}>
        <input
          className={styles.checkbox}
          type="checkbox"
          checked={state.visible}
          disabled={state.status !== "ready"}
          onChange={(event) => onVisibilityChange(event.currentTarget.checked)}
        />
        <span>
          <span className={styles.label}>{VESSEL_SOURCE.title}</span>
          <span className={styles.status} aria-live="polite">
            {STATUS_LABELS[state.status]}
            {state.featureCount !== null &&
              ` · ${state.featureCount.toLocaleString("en-US")} domain cells`}
          </span>
        </span>
      </label>

      <div className={styles.legend}>
        <span className={styles.legendUnit}>{VESSEL_SOURCE.valueUnit}</span>
        <ul className={styles.legendScale}>
          {VESSEL_SOURCE.classes.map((entry) => (
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
        <summary>Vessel source and method</summary>
        <div className={styles.detailsBody}>
          <p>{VESSEL_SOURCE.attribution}</p>
          <p>{VESSEL_SOURCE.method}</p>
          <p>
            Analytical processing date:{" "}
            <time dateTime={VESSEL_SOURCE.analysisProcessedOn}>
              {VESSEL_SOURCE.analysisProcessedOnLabel}
            </time>
            . This date applies to the checksum-bound vessel input and quality report
            below.
          </p>
          <p>{VESSEL_SOURCE.classRationale}</p>
          <ul>
            {VESSEL_SOURCE.statements.map((statement) => (
              <li key={statement}>{statement}</li>
            ))}
          </ul>
          <p>
            {checksumVerified === true
              ? "Displayed export SHA-256, verified from the loaded bytes:"
              : checksumVerified === false
                ? "Expected export SHA-256; this browser could not compute a checksum:"
                : "Expected export SHA-256:"}{" "}
            <span className={styles.identity}>{VESSEL_SOURCE.exportSha256}</span>
          </p>
          <p>
            Vessel input:{" "}
            <span className={styles.identity}>
              {VESSEL_SOURCE.analysisSourceSha256}
            </span>
          </p>
          <p>
            Vessel quality report:{" "}
            <span className={styles.identity}>{VESSEL_SOURCE.qualitySourceSha256}</span>
          </p>
          <p>
            Analytical-domain mask:{" "}
            <span className={styles.identity}>{VESSEL_SOURCE.domainSourceSha256}</span>
          </p>
        </div>
      </details>
    </div>
  );
}
