import type { MapLayerState } from "@/lib/map-layer-state";
import { VSR_SOURCE } from "@/lib/vsr-source";
import styles from "./MapLayerPanel.module.css";

interface VsrLayerControlProps {
  state: MapLayerState;
  onVisibilityChange: (visible: boolean) => void;
}

const STATUS_LABELS = {
  waiting: "Waiting for map",
  loading: "Loading boundary",
  ready: "Boundary loaded",
  error: "Boundary unavailable",
} as const;

export default function VsrLayerControl({
  state,
  onVisibilityChange,
}: VsrLayerControlProps) {
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
          <span className={styles.label}>{VSR_SOURCE.title}</span>
          <span className={styles.status} aria-live="polite">
            {STATUS_LABELS[state.status]}
          </span>
        </span>
      </label>

      <div className={styles.legend}>
        <div className={styles.legendLine}>
          <span className={styles.legendStroke} aria-hidden="true" />
          <span>VSR boundary</span>
        </div>
      </div>

      {state.warning && (
        <p className={styles.warning} role="alert">
          {state.warning}
        </p>
      )}

      <details className={styles.details}>
        <summary>Source and use notice</summary>
        <div className={styles.detailsBody}>
          <p>{VSR_SOURCE.attribution}</p>
          <p>{VSR_SOURCE.disclaimer}</p>
          <a href={VSR_SOURCE.itemUrl} target="_blank" rel="noreferrer">
            View publisher item
          </a>
        </div>
      </details>
    </div>
  );
}
