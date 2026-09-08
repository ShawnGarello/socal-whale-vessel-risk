import type { MapLayerState } from "@/lib/map-layer-state";
import { DOMAIN_SOURCE } from "@/lib/domain-source";
import styles from "./MapLayerPanel.module.css";

interface DomainLayerControlProps {
  state: MapLayerState;
  checksumVerified: boolean | null;
  onVisibilityChange: (visible: boolean) => void;
}

const STATUS_LABELS = {
  waiting: "Waiting for map",
  loading: "Loading qualified boundary",
  ready: "Qualified boundary loaded",
  error: "Qualified boundary unavailable",
} as const;

export default function DomainLayerControl({
  state,
  checksumVerified,
  onVisibilityChange,
}: DomainLayerControlProps) {
  const [red, green, blue, alpha] = DOMAIN_SOURCE.outlineColor;
  const strokeColor =
    "rgb(" + red + " " + green + " " + blue + " / " + alpha * 100 + "%)";
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
          <span className={styles.label}>{DOMAIN_SOURCE.title}</span>
          <span className={styles.status} aria-live="polite">
            {STATUS_LABELS[state.status]}
          </span>
        </span>
      </label>

      <div className={styles.legend}>
        <div className={styles.legendLine}>
          <span
            className={styles.domainLegendStroke}
            style={{ borderColor: strokeColor }}
            aria-hidden="true"
          />
          <span>50 nmi from relevant NAIS stations</span>
        </div>
        <p className={styles.legendNote}>Outside = excluded, not low activity</p>
      </div>

      {state.warning && (
        <p className={styles.warning} role="alert">
          {state.warning}
        </p>
      )}

      <details className={styles.details}>
        <summary>Domain source and meaning</summary>
        <div className={styles.detailsBody}>
          <p>{DOMAIN_SOURCE.attribution}</p>
          <p>{DOMAIN_SOURCE.method}</p>
          <p>
            Domain-evidence processing date:{" "}
            <time dateTime={DOMAIN_SOURCE.evidenceProcessedOn}>
              {DOMAIN_SOURCE.evidenceProcessedOnLabel}
            </time>
            . This date applies to the checksum-bound evidence mask and report below.
          </p>
          <ul>
            {DOMAIN_SOURCE.statements.map((statement) => (
              <li key={statement}>{statement}</li>
            ))}
          </ul>
          <p>
            {checksumVerified === true
              ? "Displayed export SHA-256, verified from the loaded bytes:"
              : checksumVerified === false
                ? "Expected export SHA-256; this browser could not compute a checksum:"
                : "Expected export SHA-256:"}{" "}
            <span className={styles.identity}>{DOMAIN_SOURCE.exportSha256}</span>
          </p>
          <p>
            Evidence mask:{" "}
            <span className={styles.identity}>
              {DOMAIN_SOURCE.evidenceSourceSha256}
            </span>
          </p>
          <p>
            Evidence report:{" "}
            <span className={styles.identity}>
              {DOMAIN_SOURCE.evidenceReportSha256}
            </span>
          </p>
        </div>
      </details>
    </div>
  );
}
