import type { MapLayerState } from "@/lib/map-layer-state";
import {
  EXPOSURE_SOURCE,
  exposureMethodConfig,
  type ExposureMethod,
} from "@/lib/exposure-source";
import panelStyles from "./MapLayerPanel.module.css";
import styles from "./ExposureLayerControl.module.css";

interface ExposureLayerControlProps {
  readonly state: MapLayerState;
  readonly method: ExposureMethod;
  readonly checksumVerified: boolean | null;
  readonly onVisibilityChange: (visible: boolean) => void;
  readonly onMethodChange: (method: ExposureMethod) => void;
}

const STATUS_LABELS = {
  waiting: "Waiting for map",
  loading: "Loading exposure grid",
  ready: "Exposure grid loaded",
  error: "Exposure grid unavailable",
} as const;

function swatchColor(color: readonly [number, number, number, number]): string {
  const [red, green, blue, alpha] = color;
  return `rgb(${red} ${green} ${blue} / ${alpha * 100}%)`;
}

export default function ExposureLayerControl({
  state,
  method,
  checksumVerified,
  onVisibilityChange,
  onMethodChange,
}: ExposureLayerControlProps) {
  const config = exposureMethodConfig(method);
  const disabled = state.status !== "ready";
  return (
    <div className={panelStyles.section}>
      <label className={panelStyles.visibilityRow}>
        <input
          className={panelStyles.checkbox}
          type="checkbox"
          checked={state.visible}
          disabled={disabled}
          onChange={(event) => onVisibilityChange(event.currentTarget.checked)}
        />
        <span>
          <span className={panelStyles.label}>{EXPOSURE_SOURCE.title}</span>
          <span className={panelStyles.status} aria-live="polite">
            {STATUS_LABELS[state.status]}
            {state.featureCount !== null &&
              ` · ${state.featureCount.toLocaleString("en-US")} qualified cells`}
          </span>
        </span>
      </label>

      <fieldset className={styles.methodPicker} disabled={disabled}>
        <legend>Map measure</legend>
        {(Object.keys(EXPOSURE_SOURCE.methods) as ExposureMethod[]).map((id) => (
          <label key={id}>
            <input
              type="radio"
              name="exposure-method"
              value={id}
              checked={method === id}
              onChange={() => onMethodChange(id)}
            />
            <span>{EXPOSURE_SOURCE.methods[id].label}</span>
          </label>
        ))}
      </fieldset>

      {state.warning && (
        <p className={panelStyles.warning} role="alert">
          {state.warning}
        </p>
      )}

      <div className={panelStyles.legend}>
        <span className={panelStyles.legendUnit}>
          {config.shortLabel} release-relative index (0–1)
        </span>
        <ul className={panelStyles.legendScale}>
          {config.classes.map((entry) => (
            <li className={panelStyles.legendClass} key={entry.label}>
              <span
                className={panelStyles.legendSwatch}
                style={{ background: swatchColor(entry.color) }}
                aria-hidden="true"
              />
              <span>{entry.label}</span>
            </li>
          ))}
        </ul>
        <p className={panelStyles.legendNote}>
          Display scale only. The analytical high-exposure result uses the all-valid p90
          threshold shown in the results panel.
        </p>
      </div>

      <details className={panelStyles.details}>
        <summary>Exposure source and method</summary>
        <div className={panelStyles.detailsBody}>
          <p>{EXPOSURE_SOURCE.attribution}</p>
          <p>{config.classificationRationale}</p>
          <ul>
            {EXPOSURE_SOURCE.statements.map((statement) => (
              <li key={statement}>{statement}</li>
            ))}
          </ul>
          <p>
            {checksumVerified === true
              ? "Display and manifest checksums verified; their results identity matches this build."
              : checksumVerified === false
                ? "This browser could not compute checksums, so the display identity and pairing are unverified."
                : "Waiting to verify the display, manifest, and results pairing."}
          </p>
          <p>
            Display SHA-256:{" "}
            <span className={panelStyles.identity}>
              {EXPOSURE_SOURCE.displaySha256}
            </span>
          </p>
          <p>
            Manifest SHA-256:{" "}
            <span className={panelStyles.identity}>
              {EXPOSURE_SOURCE.manifestSha256}
            </span>
          </p>
          <p>
            Results ID:{" "}
            <span className={panelStyles.identity}>{EXPOSURE_SOURCE.resultsId}</span>
          </p>
        </div>
      </details>
    </div>
  );
}
