import { describe, it, expect } from "vitest";
import { mkdtempSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  checkedBytes,
  digest,
  inventory,
  releaseName,
  verifyReceipt,
} from "./stage-release.mjs";

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
});
