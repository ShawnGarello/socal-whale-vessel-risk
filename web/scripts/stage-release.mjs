import { createHash } from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import {
  mkdirSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  lstatSync,
} from "node:fs";
import { dirname, join, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

export const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");

export function checkedBytes(path, expected) {
  const bytes = readFileSync(path);
  if (digest(bytes) !== expected) throw new Error("Pinned artifact checksum mismatch");
  return bytes;
}

export function releaseName(value) {
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(value ?? "")) {
    throw new Error("Release name must be 1-64 lowercase letters, digits or hyphens");
  }
  return value;
}

export function releaseBasemap(rehearsal) {
  return rehearsal ? "topo-vector" : "arcgis/oceans";
}

const REQUIRED_PUBLIC_INPUTS = [
  "accepted-analytical-domain.geojson",
  "blue-whale-density.geojson",
  "commercial-vessel-activity.geojson",
  "relative-exposure.geojson",
];
const REQUIRED_BUILD_INPUTS = ["results/exposure-results.v1.json"];
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const IDENTIFIER_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;
const SOURCE_MODULE_PATTERN = /^[a-z][a-z0-9-]*$/;
const PUBLIC_ENVIRONMENT_PATTERN = /^NEXT_PUBLIC_[A-Z0-9_]+$/;

function object(value, label) {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    throw new Error(`${label} must be an object`);
  return value;
}

function exactMembers(actual, expected, label) {
  const sorted = [...actual].sort();
  if (JSON.stringify(sorted) !== JSON.stringify(expected))
    throw new Error(`${label} is incomplete or contains an unexpected entry`);
}

function escaped(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function assertStringProperty(source, property, expected) {
  if (!new RegExp(`${escaped(property)}\\s*:\\s*["']${expected}["']`).test(source))
    throw new Error(`Application ${property} binding mismatch`);
}

function assertReferenceProperty(source, property, expectedExport) {
  if (
    !new RegExp(`${escaped(property)}\\s*:\\s*${escaped(expectedExport)}\\b`).test(
      source,
    )
  )
    throw new Error(`Application ${property} reference mismatch`);
}

function assertExportedString(source, exportName, expected) {
  if (!new RegExp(`\\b${escaped(exportName)}\\s*=\\s*["']${expected}["']`).test(source))
    throw new Error(`Application ${exportName} binding mismatch`);
}

function checkedContent(value, expected) {
  if (value === undefined || value === null)
    throw new Error("Pinned release input is missing");
  const bytes = Buffer.from(value);
  if (digest(bytes) !== expected) throw new Error("Pinned artifact checksum mismatch");
  return bytes;
}

function parsedJson(bytes, label) {
  try {
    return JSON.parse(bytes.toString("utf8"));
  } catch {
    throw new Error(`${label} is not valid JSON`);
  }
}

/** Validate that the committed inventory names the complete M7 release surface. */
export function validateReleaseInventory(value) {
  const definition = object(value, "Release input inventory");
  if (definition.schemaVersion !== 2)
    throw new Error("Unsupported release input inventory schema");
  if (!Array.isArray(definition.publicInputs) || !Array.isArray(definition.buildInputs))
    throw new Error("Release input inventory arrays are required");

  exactMembers(
    definition.publicInputs.map((entry) => object(entry, "Public input").name),
    REQUIRED_PUBLIC_INPUTS,
    "Public release input inventory",
  );
  exactMembers(
    definition.buildInputs.map((entry) => object(entry, "Build input").path),
    REQUIRED_BUILD_INPUTS,
    "Release build input inventory",
  );

  const environments = new Set();
  for (const input of definition.publicInputs) {
    if (!SHA256_PATTERN.test(input.sha256 ?? ""))
      throw new Error("Public input SHA-256 is invalid");
    if (!SHA256_PATTERN.test(input.manifestSha256 ?? ""))
      throw new Error("Public manifest SHA-256 is invalid");
    if (!SOURCE_MODULE_PATTERN.test(input.sourceModule ?? ""))
      throw new Error("Public input source module is invalid");
    if (!PUBLIC_ENVIRONMENT_PATTERN.test(input.environment ?? ""))
      throw new Error("Public input environment binding is invalid");
    if (environments.has(input.environment))
      throw new Error("Public input environment binding is duplicated");
    environments.add(input.environment);
    if (input.manifestEnvironment !== undefined) {
      if (!PUBLIC_ENVIRONMENT_PATTERN.test(input.manifestEnvironment))
        throw new Error("Public manifest environment binding is invalid");
      if (environments.has(input.manifestEnvironment))
        throw new Error("Public manifest environment binding is duplicated");
      environments.add(input.manifestEnvironment);
    }
  }

  const exposure = definition.publicInputs.find(
    (input) => input.name === "relative-exposure.geojson",
  );
  if (
    exposure.sourceSha256Field !== "displaySha256" ||
    exposure.sourceManifestSha256Field !== "manifestSha256" ||
    exposure.manifestEnvironment !== "NEXT_PUBLIC_EXPOSURE_MANIFEST_URL"
  )
    throw new Error("Exposure display and manifest bindings are incomplete");
  const resultsBinding = object(exposure.resultsBinding, "Exposure results binding");
  if (
    resultsBinding.buildInput !== REQUIRED_BUILD_INPUTS[0] ||
    resultsBinding.sourceResultsIdReference !== "EXPOSURE_RESULTS_ID" ||
    resultsBinding.sourceResultsSha256Reference !== "EXPOSURE_RESULTS_SHA256"
  )
    throw new Error("Exposure results binding is incomplete");

  const results = definition.buildInputs[0];
  if (
    results.path !== REQUIRED_BUILD_INPUTS[0] ||
    !SHA256_PATTERN.test(results.sha256 ?? "") ||
    typeof results.contract !== "string" ||
    !/^exposure-results-[0-9a-f]{24}$/.test(results.resultsId ?? "") ||
    !SOURCE_MODULE_PATTERN.test(results.sourceModule ?? "") ||
    !IDENTIFIER_PATTERN.test(results.sha256Export ?? "") ||
    !IDENTIFIER_PATTERN.test(results.resultsIdExport ?? "")
  )
    throw new Error("Exposure results build input is invalid");
  return definition;
}

/** Verify pinned files, manifests, application constants and exposure pairing. */
export function validateReleaseArtifacts(
  definitionValue,
  { readPublicFile, readRepositoryFile, readSourceModule },
) {
  const definition = validateReleaseInventory(definitionValue);
  const buildInputs = definition.buildInputs.map((input) => {
    const bytes = checkedContent(readRepositoryFile(input.path), input.sha256);
    const metadata = object(parsedJson(bytes, "Build input"), "Build input");
    if (metadata.contract !== input.contract || metadata.results_id !== input.resultsId)
      throw new Error("Exposure results identity mismatch");
    const source = String(readSourceModule(input.sourceModule));
    assertExportedString(source, input.sha256Export, input.sha256);
    assertExportedString(source, input.resultsIdExport, input.resultsId);
    return { input, bytes };
  });
  const buildByPath = new Map(buildInputs.map((entry) => [entry.input.path, entry]));

  const publicInputs = definition.publicInputs.map((pin) => {
    const data = checkedContent(readPublicFile(pin.name), pin.sha256);
    const manifest = checkedContent(
      readPublicFile(`${pin.name}.manifest.json`),
      pin.manifestSha256,
    );
    const metadata = object(parsedJson(manifest, "Public manifest"), "Public manifest");
    const output = object(metadata.output, "Public manifest output");
    if (
      output.name !== pin.name ||
      output.sha256 !== pin.sha256 ||
      output.bytes !== data.length ||
      output.media_type !== "application/geo+json"
    )
      throw new Error("Manifest binding mismatch");

    const source = String(readSourceModule(pin.sourceModule));
    assertStringProperty(source, pin.sourceSha256Field ?? "exportSha256", pin.sha256);
    if (pin.sourceManifestSha256Field)
      assertStringProperty(source, pin.sourceManifestSha256Field, pin.manifestSha256);

    if (pin.resultsBinding) {
      const build = buildByPath.get(pin.resultsBinding.buildInput);
      if (!build) throw new Error("Exposure results build input is missing");
      const results = object(metadata.results, "Exposure manifest results");
      if (
        results.contract !== build.input.contract ||
        results.results_id !== build.input.resultsId ||
        results.sha256 !== build.input.sha256
      )
        throw new Error("Exposure manifest/results pairing mismatch");
      assertReferenceProperty(
        source,
        "resultsId",
        pin.resultsBinding.sourceResultsIdReference,
      );
      assertReferenceProperty(
        source,
        "resultsSha256",
        pin.resultsBinding.sourceResultsSha256Reference,
      );
    }
    return { pin, data, manifest, metadata };
  });
  return { publicInputs, buildInputs };
}

export function assertPublicOutputInventory(files, allowedLayers, buildInputPaths) {
  const actualLayers = files
    .filter((file) => file.path.startsWith("layers/"))
    .map((file) => file.path)
    .sort();
  if (JSON.stringify(actualLayers) !== JSON.stringify([...allowedLayers].sort()))
    throw new Error("Staged public layer inventory mismatch");
  for (const path of buildInputPaths)
    if (files.some((file) => file.path === path))
      throw new Error("Build-only input was exposed as a public file");
}

export function assertCompiledBindings(compiledText, bindings) {
  for (const { label, value } of bindings)
    if (!compiledText.includes(value))
      throw new Error(`Compiled application binding missing: ${label}`);
}

export function assertDeploymentConfig(configValue, publicInputs) {
  const config = object(configValue, "Deployment configuration");
  if (config.version !== 3 || !Array.isArray(config.routes))
    throw new Error("Deployment configuration schema mismatch");
  const immutable = config.routes.find((route) => route.src === "/layers/(.*)");
  const release = config.routes.find((route) => route.src === "/release.json");
  if (
    immutable?.headers?.["Cache-Control"] !== "public, max-age=31536000, immutable" ||
    immutable.continue !== true
  )
    throw new Error("Public input immutable-cache configuration mismatch");
  if (release?.headers?.["Cache-Control"] !== "no-store" || release.continue !== true)
    throw new Error("Release identity cache configuration mismatch");

  const expectedOverrides = Object.fromEntries(
    publicInputs.flatMap((input) => [
      [input.data.path, { contentType: input.data.mediaType }],
      [input.manifest.path, { contentType: input.manifest.mediaType }],
    ]),
  );
  if (JSON.stringify(config.overrides) !== JSON.stringify(expectedOverrides))
    throw new Error("Public input media-type configuration mismatch");
}

function writeNew(path, bytes) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, bytes, { flag: "wx" });
}

export function inventory(root, prefix = "") {
  return readdirSync(join(root, prefix))
    .sort()
    .flatMap((name) => {
      const path = prefix ? `${prefix}/${name}` : name;
      const stat = lstatSync(join(root, path));
      if (stat.isSymbolicLink()) throw new Error("Release symlinks are forbidden");
      if (stat.isDirectory()) return inventory(root, path);
      if (!stat.isFile()) throw new Error("Release must contain only regular files");
      const bytes = readFileSync(join(root, path));
      return [{ path, bytes: bytes.length, sha256: digest(bytes) }];
    });
}

export function verifyReceipt(stage, expectedReceiptSha256) {
  const receipt = JSON.parse(
    checkedBytes(join(stage, "receipt.json"), expectedReceiptSha256),
  );
  const actual = inventory(join(stage, "deploy/.vercel/output"));
  if (JSON.stringify(actual) !== JSON.stringify(receipt.files))
    throw new Error("Staged deployment differs from receipt");
  const bytes = actual.reduce((total, file) => total + file.bytes, 0);
  if (receipt.bytes !== undefined && receipt.bytes !== bytes)
    throw new Error("Staged deployment byte count differs from receipt");

  // Preserve verification for retained schema-1 M4 receipts. New M7 receipts
  // carry schema 2 and receive the additional release-identity checks below.
  if (receipt.schemaVersion === 2) {
    const buildConfiguration = object(
      receipt.buildConfiguration,
      "Receipt build configuration",
    );
    const expectedBuildConfiguration =
      receipt.mode === "keyless-rehearsal-not-for-deployment"
        ? { basemap: "topo-vector", arcgisApiKey: "not-configured" }
        : {
            basemap: "arcgis/oceans",
            arcgisApiKey: "configured-not-recorded",
          };
    if (
      JSON.stringify(buildConfiguration) !== JSON.stringify(expectedBuildConfiguration)
    )
      throw new Error("Receipt build configuration mismatch");
    const staticRoot = join(stage, "deploy/.vercel/output/static");
    const release = parsedJson(
      readFileSync(join(staticRoot, "release.json")),
      "Release identity",
    );
    const publicFiles = inventory(staticRoot).filter(
      (file) => file.path !== "release.json",
    );
    if (
      release.schemaVersion !== 2 ||
      release.applicationCommit !== receipt.applicationCommit ||
      release.mode !== receipt.mode ||
      JSON.stringify(release.buildConfiguration) !==
        JSON.stringify(receipt.buildConfiguration) ||
      JSON.stringify(release.files) !== JSON.stringify(publicFiles) ||
      JSON.stringify(release.publicInputs) !== JSON.stringify(receipt.publicInputs) ||
      JSON.stringify(release.buildInputs) !== JSON.stringify(receipt.buildInputs)
    )
      throw new Error("Public release identity differs from receipt");
    assertDeploymentConfig(
      parsedJson(
        readFileSync(join(stage, "deploy/.vercel/output/config.json")),
        "Deployment configuration",
      ),
      receipt.publicInputs,
    );
    assertPublicOutputInventory(
      publicFiles,
      receipt.publicInputs.flatMap((input) => [input.data.path, input.manifest.path]),
      receipt.buildInputs.map((input) => input.path),
    );
  }
  return {
    applicationCommit: receipt.applicationCommit,
    mode: receipt.mode,
    fileCount: actual.length,
    bytes,
  };
}

function main() {
  const args = process.argv.slice(2);
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
  if (args[0] === "--verify" && args.length === 3) {
    console.log(
      JSON.stringify(
        verifyReceipt(
          join(root, "data/interim/m4-releases", releaseName(args[1])),
          args[2],
        ),
      ),
    );
    return;
  }
  const rehearsal = args[0] === "--rehearsal";
  if (rehearsal) args.shift();
  if (args.length !== 2)
    throw new Error(
      "Usage: node scripts/stage-release.mjs [--rehearsal] <name> <input-layer-directory>",
    );
  const name = releaseName(args[0]);
  const inputRoot = resolve(args[1]);
  const git = (...argv) =>
    execFileSync("git", argv, { cwd: root, maxBuffer: 16 * 1024 * 1024 });
  if (git("status", "--porcelain").toString().trim())
    throw new Error("Commit intended changes before staging");
  const commit = git("rev-parse", "HEAD").toString().trim();
  if (!rehearsal && commit !== git("rev-parse", "origin/main").toString().trim()) {
    throw new Error("Release requires HEAD equal to freshly fetched origin/main");
  }
  const key = rehearsal ? "" : process.env.NEXT_PUBLIC_ARCGIS_API_KEY;
  if (!rehearsal && !key?.trim())
    throw new Error("Supply the browser key privately through the process environment");
  const definition = JSON.parse(
    git("show", `${commit}:web/scripts/release-inputs.json`).toString(),
  );
  // Verify the complete allowlist before creating output. Ignore all other inputs.
  const { publicInputs: inputs, buildInputs } = validateReleaseArtifacts(definition, {
    readPublicFile: (path) => readFileSync(join(inputRoot, path)),
    readRepositoryFile: (path) => git("show", `${commit}:${path}`),
    readSourceModule: (module) =>
      git(
        "show",
        `${commit}:web/lib/${module}${module.endsWith("-results") ? "" : "-source"}.ts`,
      ).toString(),
  });
  const releases = join(root, "data", "interim", "m4-releases");
  mkdirSync(releases, { recursive: true });
  if (lstatSync(releases).isSymbolicLink())
    throw new Error("Release root cannot be a symlink");
  const stage = join(releases, name);
  mkdirSync(stage); // Never overwrite or remove a prior/failed release.
  const sourceRoot = join(stage, "source", "web");
  const tracked = git("ls-tree", "-r", "--name-only", commit, "web")
    .toString()
    .trim()
    .split("\n");
  for (const path of tracked) {
    if (!path.startsWith("web/") || path.includes(".."))
      throw new Error("Unexpected source path");
    if (path.startsWith("web/public/") && path !== "web/public/favicon.svg")
      throw new Error("Review new public assets before release");
    if (path.includes("/.env")) continue;
    writeNew(join(stage, "source", path), git("show", `${commit}:${path}`));
  }
  for (const { input, bytes } of buildInputs)
    writeNew(join(stage, "source", input.path), bytes);
  const env = { ...process.env, NEXT_TELEMETRY_DISABLED: "1", CI: "1" };
  for (const variable of Object.keys(env))
    if (variable.startsWith("NEXT_PUBLIC_")) delete env[variable];
  env.NEXT_PUBLIC_ARCGIS_API_KEY = key ?? "";
  env.NEXT_PUBLIC_ARCGIS_BASEMAP = releaseBasemap(rehearsal);
  for (const { pin, data, manifest } of inputs) {
    const filename = `${pin.sha256}.geojson`;
    writeNew(join(sourceRoot, "public/layers", filename), data);
    writeNew(
      join(sourceRoot, "public/layers", `${pin.manifestSha256}.manifest.json`),
      manifest,
    );
    env[pin.environment] = `/layers/${filename}`;
    if (pin.manifestEnvironment)
      env[pin.manifestEnvironment] = `/layers/${pin.manifestSha256}.manifest.json`;
  }
  // npm's Windows launcher needs cmd.exe; this is a constant command, with no
  // interpolated paths, credentials or user-supplied shell text.
  const run = (command) => {
    const result =
      process.platform === "win32"
        ? spawnSync("cmd.exe", ["/d", "/s", "/c", command], {
            cwd: sourceRoot,
            env,
            encoding: "utf8",
            maxBuffer: 16 * 1024 * 1024,
          })
        : spawnSync("sh", ["-c", command], {
            cwd: sourceRoot,
            env,
            encoding: "utf8",
            maxBuffer: 16 * 1024 * 1024,
          });
    const log = `${result.stdout ?? ""}${result.stderr ?? ""}`;
    const sanitized = key ? log.split(key).join("[REDACTED]") : log;
    writeNew(
      join(stage, "verification.log"),
      sanitized.replaceAll(sourceRoot, "[staged-web]"),
    );
    if (result.status !== 0)
      throw new Error("Web gates failed; sanitized local verification.log retained");
  };
  console.log("Building isolated committed source and running locked web checks...");
  run("npm run verify:clean");
  const out = join(sourceRoot, "out");
  const files = inventory(out);
  const allowedLayers = inputs.flatMap(({ pin }) => [
    `layers/${pin.sha256}.geojson`,
    `layers/${pin.manifestSha256}.manifest.json`,
  ]);
  assertPublicOutputInventory(
    files,
    allowedLayers,
    buildInputs.map(({ input }) => input.path),
  );
  for (const file of files) {
    if (!/\.(html|txt|js|css|svg|ico|woff2?|geojson|json)$/.test(file.path))
      throw new Error("Unexpected export file type");
    if (/\.(map|env|parquet)$|(^|\/)(data|raw|source|node_modules)\//.test(file.path))
      throw new Error("Private output refused");
    const text = readFileSync(join(out, file.path)).toString();
    for (const localPath of [root, inputRoot, stage]) {
      if (
        [
          localPath,
          localPath.replaceAll("\\", "/"),
          localPath.replaceAll("\\", "\\\\"),
        ].some((value) => text.includes(value))
      )
        throw new Error("Local path found in export");
    }
  }
  const compiledText = files
    .filter(
      (file) =>
        !file.path.startsWith("layers/") && /\.(html|txt|js|json)$/.test(file.path),
    )
    .map((file) => readFileSync(join(out, file.path), "utf8"))
    .join("\n");
  assertCompiledBindings(compiledText, [
    ...inputs.flatMap(({ pin }) => [
      {
        label: `${pin.name} URL`,
        value: `/layers/${pin.sha256}.geojson`,
      },
      ...(pin.manifestEnvironment
        ? [
            {
              label: `${pin.name} manifest URL`,
              value: `/layers/${pin.manifestSha256}.manifest.json`,
            },
          ]
        : []),
    ]),
    ...buildInputs.flatMap(({ input }) => [
      { label: `${input.path} checksum`, value: input.sha256 },
      { label: `${input.path} results ID`, value: input.resultsId },
    ]),
  ]);
  for (const { pin } of inputs) {
    checkedBytes(join(out, "layers", `${pin.sha256}.geojson`), pin.sha256);
    checkedBytes(
      join(out, "layers", `${pin.manifestSha256}.manifest.json`),
      pin.manifestSha256,
    );
  }
  const output = join(stage, "deploy/.vercel/output");
  const staticRoot = join(output, "static");
  for (const file of files)
    writeNew(join(staticRoot, file.path), readFileSync(join(out, file.path)));
  const publicInputIdentities = inputs.map(({ pin, data, manifest, metadata }) => ({
    name: pin.name,
    data: {
      path: `layers/${pin.sha256}.geojson`,
      bytes: data.length,
      sha256: pin.sha256,
      mediaType: metadata.output.media_type,
    },
    manifest: {
      path: `layers/${pin.manifestSha256}.manifest.json`,
      bytes: manifest.length,
      sha256: pin.manifestSha256,
      mediaType: "application/json",
    },
  }));
  const buildInputIdentities = buildInputs.map(({ input, bytes }) => ({
    path: input.path,
    bytes: bytes.length,
    sha256: input.sha256,
    contract: input.contract,
    resultsId: input.resultsId,
    delivery: "build-only-not-public",
  }));
  const buildConfiguration = {
    basemap: releaseBasemap(rehearsal),
    arcgisApiKey: key?.trim() ? "configured-not-recorded" : "not-configured",
  };
  const release = {
    schemaVersion: 2,
    applicationCommit: commit,
    mode: rehearsal
      ? "keyless-rehearsal-not-for-deployment"
      : "release-candidate-awaiting-approval",
    buildConfiguration,
    publicInputs: publicInputIdentities,
    buildInputs: buildInputIdentities,
    files,
  };
  writeNew(join(staticRoot, "release.json"), JSON.stringify(release, null, 2) + "\n");
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
      { src: "/", dest: "/index.html" },
      { handle: "filesystem" },
      { src: "/.*", dest: "/404.html", status: 404 },
    ],
    overrides: Object.fromEntries(
      inputs.flatMap(({ pin }) => [
        [`layers/${pin.sha256}.geojson`, { contentType: "application/geo+json" }],
        [
          `layers/${pin.manifestSha256}.manifest.json`,
          { contentType: "application/json" },
        ],
      ]),
    ),
  };
  assertDeploymentConfig(config, publicInputIdentities);
  writeNew(join(output, "config.json"), JSON.stringify(config, null, 2) + "\n");
  const deploymentFiles = inventory(output);
  const bytes = deploymentFiles.reduce((total, file) => total + file.bytes, 0);
  if (bytes > 100_000_000 || deploymentFiles.length > 15_000)
    throw new Error("Hobby upload limit exceeded");
  const receipt = {
    schemaVersion: 2,
    applicationCommit: commit,
    mode: release.mode,
    nodeVersion: process.version,
    bytes,
    buildConfiguration,
    publicInputs: publicInputIdentities,
    buildInputs: buildInputIdentities,
    files: deploymentFiles,
  };
  const receiptBytes = JSON.stringify(receipt, null, 2) + "\n";
  writeNew(join(stage, "receipt.json"), receiptBytes);
  console.log(
    JSON.stringify({
      applicationCommit: commit,
      mode: release.mode,
      bytes,
      fileCount: deploymentFiles.length,
      receiptSha256: digest(receiptBytes),
      directory: relative(root, stage),
    }),
  );
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    main();
  } catch (error) {
    // Never echo arbitrary filesystem, subprocess or environment errors.
    console.error(
      error instanceof Error && !error.code
        ? error.message
        : "Release staging failed; inputs and existing releases preserved",
    );
    process.exitCode = 1;
  }
}
