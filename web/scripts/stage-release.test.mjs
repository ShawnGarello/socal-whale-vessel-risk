import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  checkedBytes,
  assertCompiledBindings,
  assertDeploymentConfig,
  assertPublicOutputInventory,
  digest,
  inventory,
  releaseName,
  validateReleaseArtifacts,
  validateReleaseInventory,
  verifyReceipt,
} from "./stage-release.mjs";

function syntheticRelease() {
  const publicFiles = new Map();
  const sources = new Map();
  const resultsId = "exposure-results-1234567890abcdef12345678";
  const resultsBytes = Buffer.from(
    JSON.stringify({
      contract: "relative_exposure_application_results_v1",
      results_id: resultsId,
    }),
  );
  const resultsSha256 = digest(resultsBytes);
  const buildInput = {
    path: "results/exposure-results.v1.json",
    sha256: resultsSha256,
    contract: "relative_exposure_application_results_v1",
    resultsId,
    sourceModule: "exposure-results",
    sha256Export: "EXPOSURE_RESULTS_SHA256",
    resultsIdExport: "EXPOSURE_RESULTS_ID",
  };
  sources.set(
    "exposure-results",
    `export const EXPOSURE_RESULTS_SHA256 = "${resultsSha256}";\n` +
      `export const EXPOSURE_RESULTS_ID = "${resultsId}";`,
  );

  const publicInputs = [
    ["blue-whale-density.geojson", "whale", "NEXT_PUBLIC_WHALE_LAYER_URL"],
    ["commercial-vessel-activity.geojson", "vessel", "NEXT_PUBLIC_VESSEL_LAYER_URL"],
    ["accepted-analytical-domain.geojson", "domain", "NEXT_PUBLIC_DOMAIN_LAYER_URL"],
    ["relative-exposure.geojson", "exposure", "NEXT_PUBLIC_EXPOSURE_LAYER_URL"],
  ].map(([name, sourceModule, environment]) => {
    const data = Buffer.from(`synthetic ${name}`);
    const sha256 = digest(data);
    const metadata = {
      output: {
        name,
        bytes: data.length,
        sha256,
        media_type: "application/geo+json",
      },
      ...(sourceModule === "exposure"
        ? {
            results: {
              contract: buildInput.contract,
              results_id: resultsId,
              sha256: resultsSha256,
            },
          }
        : {}),
    };
    const manifest = Buffer.from(JSON.stringify(metadata));
    const manifestSha256 = digest(manifest);
    publicFiles.set(name, data);
    publicFiles.set(`${name}.manifest.json`, manifest);
    if (sourceModule === "exposure") {
      sources.set(
        sourceModule,
        `displaySha256: "${sha256}", manifestSha256: "${manifestSha256}", ` +
          "resultsId: EXPOSURE_RESULTS_ID, resultsSha256: EXPOSURE_RESULTS_SHA256",
      );
      return {
        name,
        sha256,
        manifestSha256,
        sourceModule,
        sourceSha256Field: "displaySha256",
        sourceManifestSha256Field: "manifestSha256",
        environment,
        manifestEnvironment: "NEXT_PUBLIC_EXPOSURE_MANIFEST_URL",
        resultsBinding: {
          buildInput: buildInput.path,
          sourceResultsIdReference: "EXPOSURE_RESULTS_ID",
          sourceResultsSha256Reference: "EXPOSURE_RESULTS_SHA256",
        },
      };
    }
    sources.set(sourceModule, `exportSha256: "${sha256}"`);
    return { name, sha256, manifestSha256, sourceModule, environment };
  });
  const definition = { schemaVersion: 2, publicInputs, buildInputs: [buildInput] };
  const readers = {
    readPublicFile: (path) => publicFiles.get(path),
    readRepositoryFile: (path) => (path === buildInput.path ? resultsBytes : undefined),
    readSourceModule: (module) => sources.get(module),
  };
  return { definition, publicFiles, resultsBytes, sources, readers };
}

describe("release publication safeguards", () => {
  it("rejects an extra upload file even when all original files still match", () => {
    const stage = mkdtempSync(join(tmpdir(), "m4-receipt-test-"));
    const output = join(stage, "deploy/.vercel/output");
    mkdirSync(output, { recursive: true });
    writeFileSync(join(output, "config.json"), '{"version":3}');
    const receipt = JSON.stringify({
      applicationCommit: "test",
      mode: "test",
      files: inventory(output),
    });
    writeFileSync(join(stage, "receipt.json"), receipt);
    expect(verifyReceipt(stage, digest(receipt)).fileCount).toBe(1);
    writeFileSync(join(output, "private.json"), "{}");
    expect(() => verifyReceipt(stage, digest(receipt))).toThrow("differs from receipt");
  });
  it("verifies schema-2 release identity, public inputs, and build-only inputs", () => {
    const stage = mkdtempSync(join(tmpdir(), "m7-receipt-test-"));
    const output = join(stage, "deploy/.vercel/output");
    const staticRoot = join(output, "static");
    mkdirSync(join(staticRoot, "layers"), { recursive: true });
    writeFileSync(join(staticRoot, "layers/display.geojson"), "display");
    writeFileSync(join(staticRoot, "layers/manifest.manifest.json"), "{}");
    const publicInputs = [
      {
        name: "synthetic.geojson",
        data: {
          path: "layers/display.geojson",
          bytes: 7,
          sha256: digest("display"),
          mediaType: "application/geo+json",
        },
        manifest: {
          path: "layers/manifest.manifest.json",
          bytes: 2,
          sha256: digest("{}"),
          mediaType: "application/json",
        },
      },
    ];
    const buildInputs = [
      {
        path: "results/exposure-results.v1.json",
        bytes: 2,
        sha256: digest("{}"),
        contract: "test",
        resultsId: "test",
        delivery: "build-only-not-public",
      },
    ];
    const release = {
      schemaVersion: 2,
      applicationCommit: "test",
      mode: "test",
      publicInputs,
      buildInputs,
      files: inventory(staticRoot),
    };
    writeFileSync(
      join(staticRoot, "release.json"),
      `${JSON.stringify(release, null, 2)}\n`,
    );
    const config = {
      version: 3,
      routes: [
        {
          src: "/layers/(.*)",
          headers: { "Cache-Control": "public, max-age=31536000, immutable" },
          continue: true,
        },
        {
          src: "/release.json",
          headers: { "Cache-Control": "no-store" },
          continue: true,
        },
      ],
      overrides: {
        "layers/display.geojson": { contentType: "application/geo+json" },
        "layers/manifest.manifest.json": { contentType: "application/json" },
      },
    };
    writeFileSync(join(output, "config.json"), `${JSON.stringify(config)}\n`);
    const files = inventory(output);
    const receiptValue = {
      schemaVersion: 2,
      applicationCommit: "test",
      mode: "test",
      bytes: files.reduce((total, file) => total + file.bytes, 0),
      publicInputs,
      buildInputs,
      files,
    };
    let receipt = `${JSON.stringify(receiptValue, null, 2)}\n`;
    writeFileSync(join(stage, "receipt.json"), receipt);
    expect(verifyReceipt(stage, digest(receipt))).toMatchObject({
      applicationCommit: "test",
      fileCount: files.length,
    });

    receiptValue.publicInputs[0].data.mediaType = "text/plain";
    receipt = `${JSON.stringify(receiptValue, null, 2)}\n`;
    writeFileSync(join(stage, "receipt.json"), receipt);
    expect(() => verifyReceipt(stage, digest(receipt))).toThrow(/identity differs/);
  });
  it("refuses changed artifact bytes, including a same-size substitution", () => {
    const root = mkdtempSync(join(tmpdir(), "m4-release-test-"));
    const file = join(root, "artifact.json");
    writeFileSync(file, '{"a":1}');
    const expected = digest('{"a":1}');
    expect(checkedBytes(file, expected).toString()).toBe('{"a":1}');
    writeFileSync(file, '{"a":2}');
    expect(() => checkedBytes(file, expected)).toThrow("checksum mismatch");
    expect(() => checkedBytes(join(root, "missing"), expected)).toThrow();
  });
  it("rejects paths and shell-shaped release names", () => {
    for (const value of ["../old", "C:\\release", "/", "a/b", "a;whoami", "", "a b"]) {
      expect(() => releaseName(value)).toThrow();
    }
    expect(releaseName("m4-rehearsal-01")).toBe("m4-rehearsal-01");
  });
  it("inventories nested bytes deterministically without absolute paths", () => {
    const root = mkdtempSync(join(tmpdir(), "m4-inventory-test-"));
    mkdirSync(join(root, "layers"));
    writeFileSync(join(root, "layers", "a.json"), "{}");
    writeFileSync(join(root, "index.html"), "hello");
    expect(inventory(root)).toEqual([
      { path: "index.html", bytes: 5, sha256: digest("hello") },
      { path: "layers/a.json", bytes: 2, sha256: digest("{}") },
    ]);
  });

  it("requires the complete M7 public and build-only input inventory", () => {
    const committed = JSON.parse(
      readFileSync(new URL("./release-inputs.json", import.meta.url), "utf8"),
    );
    expect(validateReleaseInventory(committed)).toBe(committed);

    const missingExposure = structuredClone(committed);
    missingExposure.publicInputs = missingExposure.publicInputs.filter(
      (input) => input.name !== "relative-exposure.geojson",
    );
    expect(() => validateReleaseInventory(missingExposure)).toThrow(/incomplete/);

    const missingResults = structuredClone(committed);
    missingResults.buildInputs = [];
    expect(() => validateReleaseInventory(missingResults)).toThrow(/incomplete/);
  });

  it("rejects changed display, manifest, and results bytes", () => {
    const fixture = syntheticRelease();
    expect(validateReleaseArtifacts(fixture.definition, fixture.readers)).toMatchObject(
      {
        publicInputs: { length: 4 },
        buildInputs: { length: 1 },
      },
    );

    for (const changed of [
      {
        ...fixture.readers,
        readPublicFile: (path) =>
          path === "relative-exposure.geojson"
            ? Buffer.from("changed display bytes")
            : fixture.readers.readPublicFile(path),
      },
      {
        ...fixture.readers,
        readPublicFile: (path) =>
          path === "relative-exposure.geojson.manifest.json"
            ? Buffer.from("changed manifest bytes")
            : fixture.readers.readPublicFile(path),
      },
      {
        ...fixture.readers,
        readRepositoryFile: () => Buffer.from("changed results bytes"),
      },
    ]) {
      expect(() => validateReleaseArtifacts(fixture.definition, changed)).toThrow(
        /checksum mismatch/,
      );
    }
  });

  it("rejects missing exposure and results files", () => {
    const fixture = syntheticRelease();
    expect(() =>
      validateReleaseArtifacts(fixture.definition, {
        ...fixture.readers,
        readPublicFile: (path) =>
          path === "relative-exposure.geojson"
            ? undefined
            : fixture.readers.readPublicFile(path),
      }),
    ).toThrow(/input is missing/);
    expect(() =>
      validateReleaseArtifacts(fixture.definition, {
        ...fixture.readers,
        readRepositoryFile: () => undefined,
      }),
    ).toThrow(/input is missing/);
  });

  it("rejects checksum-pinned but incompatible exposure/results pairing", () => {
    const fixture = syntheticRelease();
    const definition = structuredClone(fixture.definition);
    const files = new Map(fixture.publicFiles);
    const exposure = definition.publicInputs.find(
      (input) => input.name === "relative-exposure.geojson",
    );
    const manifestPath = "relative-exposure.geojson.manifest.json";
    const metadata = JSON.parse(files.get(manifestPath).toString("utf8"));
    metadata.results.results_id = "exposure-results-ffffffffffffffffffffffff";
    const changedManifest = Buffer.from(JSON.stringify(metadata));
    exposure.manifestSha256 = digest(changedManifest);
    files.set(manifestPath, changedManifest);
    fixture.sources.set(
      "exposure",
      fixture.sources
        .get("exposure")
        .replace(
          /manifestSha256: "[0-9a-f]{64}"/,
          `manifestSha256: "${exposure.manifestSha256}"`,
        ),
    );
    expect(() =>
      validateReleaseArtifacts(definition, {
        ...fixture.readers,
        readPublicFile: (path) => files.get(path),
      }),
    ).toThrow(/pairing mismatch/);
  });

  it("rejects incorrect source constants and compiled URL bindings", () => {
    const fixture = syntheticRelease();
    expect(() =>
      validateReleaseArtifacts(fixture.definition, {
        ...fixture.readers,
        readSourceModule: (module) =>
          module === "exposure"
            ? fixture.sources
                .get(module)
                .replace(/displaySha256: "[0-9a-f]{64}"/, 'displaySha256: "bad"')
            : fixture.readers.readSourceModule(module),
      }),
    ).toThrow(/displaySha256 binding mismatch/);
    expect(() =>
      assertCompiledBindings("only the display URL", [
        { label: "exposure manifest URL", value: "/layers/manifest.manifest.json" },
      ]),
    ).toThrow(/manifest URL/);
  });

  it("requires every staged public pair and refuses extras or build-only files", () => {
    const expected = ["layers/display.geojson", "layers/manifest.manifest.json"];
    const files = expected.map((path) => ({ path }));
    expect(() =>
      assertPublicOutputInventory(files, expected, [
        "results/exposure-results.v1.json",
      ]),
    ).not.toThrow();
    expect(() =>
      assertPublicOutputInventory(files.slice(0, 1), expected, [
        "results/exposure-results.v1.json",
      ]),
    ).toThrow(/inventory mismatch/);
    expect(() =>
      assertPublicOutputInventory(
        [...files, { path: "layers/unexpected.json" }],
        expected,
        ["results/exposure-results.v1.json"],
      ),
    ).toThrow(/inventory mismatch/);
    expect(() =>
      assertPublicOutputInventory(
        [...files, { path: "results/exposure-results.v1.json" }],
        expected,
        ["results/exposure-results.v1.json"],
      ),
    ).toThrow(/Build-only/);
  });

  it("binds public media types and the immutable/no-store cache policy", () => {
    const publicInputs = [
      {
        data: {
          path: "layers/display.geojson",
          mediaType: "application/geo+json",
        },
        manifest: {
          path: "layers/manifest.manifest.json",
          mediaType: "application/json",
        },
      },
    ];
    const config = {
      version: 3,
      routes: [
        {
          src: "/layers/(.*)",
          headers: { "Cache-Control": "public, max-age=31536000, immutable" },
          continue: true,
        },
        {
          src: "/release.json",
          headers: { "Cache-Control": "no-store" },
          continue: true,
        },
      ],
      overrides: {
        "layers/display.geojson": { contentType: "application/geo+json" },
        "layers/manifest.manifest.json": { contentType: "application/json" },
      },
    };
    expect(() => assertDeploymentConfig(config, publicInputs)).not.toThrow();
    expect(() =>
      assertDeploymentConfig(
        {
          ...config,
          routes: config.routes.map((route) =>
            route.src === "/layers/(.*)"
              ? { ...route, headers: { "Cache-Control": "no-store" } }
              : route,
          ),
        },
        publicInputs,
      ),
    ).toThrow(/immutable-cache/);
    expect(() =>
      assertDeploymentConfig(
        {
          ...config,
          overrides: {
            ...config.overrides,
            "layers/manifest.manifest.json": { contentType: "text/plain" },
          },
        },
        publicInputs,
      ),
    ).toThrow(/media-type/);
  });
});
