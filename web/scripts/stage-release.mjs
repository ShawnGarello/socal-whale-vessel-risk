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
  return {
    applicationCommit: receipt.applicationCommit,
    mode: receipt.mode,
    fileCount: actual.length,
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
  const pins = JSON.parse(
    git("show", `${commit}:web/scripts/release-inputs.json`).toString(),
  );
  // Verify the complete allowlist before creating output. Ignore all other inputs.
  const inputs = pins.map((pin) => {
    const data = checkedBytes(join(inputRoot, pin.name), pin.sha256);
    const manifest = checkedBytes(
      join(inputRoot, `${pin.name}.manifest.json`),
      pin.manifestSha256,
    );
    const metadata = JSON.parse(manifest);
    if (metadata.output.sha256 !== pin.sha256 || metadata.output.bytes !== data.length)
      throw new Error("Manifest binding mismatch");
    const source = git(
      "show",
      `${commit}:web/lib/${pin.sourceModule}-source.ts`,
    ).toString();
    if (!new RegExp(`exportSha256:\\s*"${pin.sha256}"`).test(source))
      throw new Error("Application artifact binding mismatch");
    return { pin, data, manifest };
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
  const env = { ...process.env, NEXT_TELEMETRY_DISABLED: "1", CI: "1" };
  for (const variable of Object.keys(env))
    if (variable.startsWith("NEXT_PUBLIC_")) delete env[variable];
  env.NEXT_PUBLIC_ARCGIS_API_KEY = key ?? "";
  env.NEXT_PUBLIC_ARCGIS_BASEMAP = "arcgis/oceans";
  for (const { pin, data, manifest } of inputs) {
    const filename = `${pin.sha256}.geojson`;
    writeNew(join(sourceRoot, "public/layers", filename), data);
    writeNew(
      join(sourceRoot, "public/layers", `${pin.manifestSha256}.manifest.json`),
      manifest,
    );
    env[pin.environment] = `/layers/${filename}`;
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
  for (const file of files) {
    if (file.path.startsWith("layers/") && !allowedLayers.includes(file.path))
      throw new Error("Unexpected public layer");
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
  const release = {
    schemaVersion: 1,
    applicationCommit: commit,
    mode: rehearsal
      ? "keyless-rehearsal-not-for-deployment"
      : "release-candidate-awaiting-approval",
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
      inputs.map(({ pin }) => [
        `layers/${pin.sha256}.geojson`,
        { contentType: "application/geo+json" },
      ]),
    ),
  };
  writeNew(join(output, "config.json"), JSON.stringify(config, null, 2) + "\n");
  const deploymentFiles = inventory(output);
  const bytes = deploymentFiles.reduce((total, file) => total + file.bytes, 0);
  if (bytes > 100_000_000 || deploymentFiles.length > 15_000)
    throw new Error("Hobby upload limit exceeded");
  const receipt = {
    applicationCommit: commit,
    mode: release.mode,
    nodeVersion: process.version,
    bytes,
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
