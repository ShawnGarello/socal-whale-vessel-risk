import {
  buildExposureResultsViewModel,
  type ExposureResults,
} from "@/lib/exposure-results";
import type { ExposureResultsLoad } from "@/lib/load-exposure-results";
import styles from "./ExposureResultsPanel.module.css";

interface SplitMeasureProps {
  readonly title: string;
  readonly description: string;
  readonly insideText: string;
  readonly outsideText: string;
  readonly insideFraction: number | null;
  readonly outsideFraction: number | null;
}

function SplitMeasure({
  title,
  description,
  insideText,
  outsideText,
  insideFraction,
  outsideFraction,
}: SplitMeasureProps) {
  const available = insideFraction !== null && outsideFraction !== null;
  return (
    <section className={styles.measure} aria-label={title}>
      <h3>{title}</h3>
      <p>{description}</p>
      {available ? (
        <>
          <div className={styles.splitValues}>
            <span>
              <strong>{insideText}</strong> inside
            </span>
            <span>
              <strong>{outsideText}</strong> outside
            </span>
          </div>
          <div className={styles.splitBar} aria-hidden="true">
            <span
              className={styles.insideSegment}
              style={{ flexGrow: insideFraction }}
            />
            <span
              className={styles.outsideSegment}
              style={{ flexGrow: outsideFraction }}
            />
          </div>
        </>
      ) : (
        <p className={styles.unavailable} role="status">
          This share is not available. A valid zero total is not converted into a
          percentage.
        </p>
      )}
    </section>
  );
}

function SensitivityTable({ results }: { readonly results: ExposureResults }) {
  const view = buildExposureResultsViewModel(results);
  return (
    <details className={styles.details}>
      <summary>Review threshold and grid sensitivities</summary>
      <div className={styles.detailsBody}>
        <p>
          All-valid p90 is the initial presentation. P80 and p95 show how the
          selected-water result changes with the descriptive cutoff; positive-only
          changes the reference population. None is an ecological danger threshold.
        </p>
        <div className={styles.tableScroller} tabIndex={0}>
          <table>
            <caption>All-valid high-exposure water area inside the VSR</caption>
            <thead>
              <tr>
                <th scope="col">Cutoff</th>
                <th scope="col">Product</th>
                <th scope="col">Log traffic</th>
                <th scope="col">Product threshold</th>
                <th scope="col">Log threshold</th>
              </tr>
            </thead>
            <tbody>
              {view.thresholdRows.map((row) => (
                <tr key={row.percentile}>
                  <th scope="row">{row.percentile}</th>
                  <td>{row.productInside}</td>
                  <td>{row.logInside}</td>
                  <td>{row.productThreshold}</td>
                  <td>{row.logThreshold}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={styles.tableScroller} tabIndex={0}>
          <table>
            <caption>Positive-only reference sensitivity, inside-area share</caption>
            <thead>
              <tr>
                <th scope="col">Cutoff</th>
                <th scope="col">Product</th>
                <th scope="col">Log traffic</th>
              </tr>
            </thead>
            <tbody>
              {view.positiveOnlyRows.map((row) => (
                <tr key={row.percentile}>
                  <th scope="row">{row.percentile}</th>
                  <td>{row.productInside}</td>
                  <td>{row.logInside}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className={styles.tableScroller} tabIndex={0}>
          <table>
            <caption>Generated change from the 5 km to 10 km grid</caption>
            <thead>
              <tr>
                <th scope="col">Measure</th>
                <th scope="col">Product</th>
                <th scope="col">Log traffic</th>
              </tr>
            </thead>
            <tbody>
              {view.gridSensitivityRows.map((row) => (
                <tr key={row.measure}>
                  <th scope="row">
                    {row.measure}
                    <span className={styles.tableUnit}>
                      {row.unit === "percentage points" ? " (pp)" : " (%)"}
                    </span>
                  </th>
                  <td>{row.productChange}</td>
                  <td>{row.logTrafficChange}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          These are generated 10 km minus 5 km comparisons; positive values are
          increases and negative values are decreases. Grid stability for an integrated
          share does not establish stability for the high-area statistics.
        </p>
      </div>
    </details>
  );
}

export default function ExposureResultsPanel({
  load,
}: {
  readonly load: ExposureResultsLoad;
}) {
  if (!load.ok) {
    return (
      <aside className={styles.panel} aria-labelledby="results-heading">
        <h2 id="results-heading">Relative exposure results</h2>
        <div className={styles.error} role="alert">
          <strong>Results unavailable</strong>
          <p>{load.message}</p>
          <p>The map and independent input layers can still be used.</p>
        </div>
      </aside>
    );
  }

  const view = buildExposureResultsViewModel(load.results);
  const requiredLimitations = view.limitationPoints.slice(0, 7);
  const additionalLimitations = view.limitationPoints.slice(7);
  return (
    <aside className={styles.panel} aria-labelledby="results-heading">
      <div className={styles.intro}>
        <p className={styles.context}>Exploratory result · 5 km grid</p>
        <h2 id="results-heading">Where the modeled overlap falls</h2>
        <p>
          The primary measure multiplies modeled blue-whale density by commercial vessel
          movement intensity, then integrates it over receiver-qualified water. It
          describes relative spatial overlap—not encounters or collision probability.
        </p>
      </div>

      <SplitMeasure
        title="Share of integrated relative exposure"
        description="The full exposure proxy, divided by its exact fractional position inside and outside the current VSR boundary."
        insideText={view.primary.insideShare}
        outsideText={view.primary.outsideShare}
        insideFraction={view.primary.insideShareFraction}
        outsideFraction={view.primary.outsideShareFraction}
      />

      <SplitMeasure
        title="Share of high-exposure water area"
        description={`Water at or above the all-valid p90 intensity threshold (${view.primary.p90Threshold}); ${view.primary.p90SelectedArea} is selected. This is area share, not exposure share.`}
        insideText={view.primary.p90InsideAreaShare}
        outsideText={view.primary.p90OutsideAreaShare}
        insideFraction={view.primary.p90InsideAreaShareFraction}
        outsideFraction={view.primary.p90OutsideAreaShareFraction}
      />

      <section className={styles.sensitivity} aria-labelledby="sensitivity-heading">
        <h3 id="sensitivity-heading">Formula sensitivity matters</h3>
        <p>
          Compressing high traffic changes the integrated inside share to{" "}
          <strong>{view.sensitivity.insideShare}</strong> (outside{" "}
          <strong>{view.sensitivity.outsideShare}</strong>), a{" "}
          <strong>{view.formulaInsideChangePercentagePoints}</strong> percentage-point
          change from the primary product. This is a different formula, not a confidence
          interval.
        </p>
      </section>

      <SensitivityTable results={load.results} />

      <section className={styles.limitations} aria-labelledby="limitations-heading">
        <h3 id="limitations-heading">Read this result with care</h3>
        <ul>
          {requiredLimitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
        {additionalLimitations.length > 0 && (
          <details className={styles.details}>
            <summary>Additional generated limitations</summary>
            <ul className={styles.additionalList}>
              {additionalLimitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <details className={styles.details}>
        <summary>Artifact identity</summary>
        <div className={styles.identity}>
          <p>
            Results ID: <span>{view.resultsId}</span>
          </p>
          <p>
            Results SHA-256: <span>{load.sha256}</span>
          </p>
          <p>
            These generated values passed independent numerical/scientific-content
            review and were accepted by the author for this exploratory public
            presentation. Review and acceptance do not change the limitations above or
            turn this exploratory overlap proxy into a causal or policy result.
          </p>
        </div>
      </details>
    </aside>
  );
}
