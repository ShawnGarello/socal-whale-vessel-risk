# M7 release-integration handoff

## Status

Release-tooling implementation and local verification are complete on
`feat/m7-release-integration`. This is ready for independent audit, not
deployment approval or acceptance of any scientific conclusion. The live site
still serves the earlier M4 package.

The branch started from `origin/main` commit
`90729cefb5e6f65fa030840fac06d047902691d0`, which already contains the merged
dependency-maintenance work. `package.json` and `package-lock.json` were not
changed. Implementation commits before this handoff are:

- `6ac5761da9035dbce9f92c1c7d51ae5ea8bf96b9` — complete M7 release inputs,
  bindings, validation, receipts and focused tests;
- `71247070663a954fe7e424f05ce2194ee7f1614d` — explicitly keyless,
  browser-runnable rehearsal configuration and receipt identity.

## Implemented boundary

The existing `web/scripts/stage-release.mjs` and
`web/scripts/release-inputs.json` mechanism is retained. It now:

- inventories the four exact public GeoJSON/manifest pairs and binds every
  isolated build to content-addressed same-origin URLs;
- copies only the tracked `results/exposure-results.v1.json` into the isolated
  repository-shaped source tree; it is build-only and no public `results/`
  endpoint is permitted;
- checks display and manifest hashes, results hash and ID, application constants,
  manifest/results pairing, exact staged output, media/cache configuration,
  release identity, count/size limits and receipt read-back;
- fails on missing or changed inputs, incompatible pairing, stale URL/checksum
  bindings, missing output, unexpected public files and the pre-existing input
  layer/receipt violations; and
- preserves the whale, vessel, domain, attribution and publisher-hosted
  `FID = 126` VSR paths. No VSR geometry is copied.

The public identities are:

| Input    | Display SHA-256                                                    | Manifest SHA-256                                                   |
| -------- | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| Whale    | `831a5412e9f414d5e4c7011d1b1687a89b8089826f8925f31e737b974662e154` | `404c53356be7d743cbc5e4bc1b5741e4938c84e206caf1d53468954e368c8108` |
| Vessel   | `3a7f2deeaa1899ac8fc5ecec7e7f522dd058adce667333ba33f8d32d930d3288` | `6d18aaf3e74038db0165884c0daaf99b5acf400dd42f5cccccb42da848ff995d` |
| Domain   | `7020ca8dfa27953a24a9db4ad2b0a25fb321c4edbecd383a01c62efb4b3bc7bf` | `d340dc2703f3a891a62d4735dc442a7545a6330e9e3322b95f742f502b3b0de6` |
| Exposure | `1ccb605cad9640f42ca5eb2cb1ac3543b3a1341a3375f6e78166dd0fd16e92cb` | `0a1b0dea947b3f96dec9cc6ca5037ffe7af4ce949c4e197d8126818e71c569c0` |

The build-only results SHA-256 is
`ebba5b06ee804d80b34f5714ecb1d100c0b05d3579307e88384886dcbd339e60`;
its ID is `exposure-results-8a0bf6c27e00fb40a13d6870`.

## Local candidate and commands

Exact retained inputs were copied byte-for-byte into this session's ignored
directory; no AIS or exposure analysis was rerun:

```text
C:\Users\teche\socal-whale-vessel-risk-m7-release-integration\data\interim\m7-release-integration\retained-inputs-20260908
```

From `web/`:

```powershell
npm ci
npm test -- scripts/stage-release.test.mjs lib/exposure-source.test.ts
node scripts/stage-release.mjs --rehearsal m7-release-integration-rehearsal-20260909-01 C:/Users/teche/socal-whale-vessel-risk-m7-release-integration/data/interim/m7-release-integration/retained-inputs-20260908
node scripts/stage-release.mjs --verify m7-release-integration-rehearsal-20260909-01 ad9f530ea63e64fe661b7ae6fb431e14c200f57ace42327eeecfcf5949955942
```

Candidate directory:

```text
C:\Users\teche\socal-whale-vessel-risk-m7-release-integration\data\interim\m4-releases\m7-release-integration-rehearsal-20260909-01
```

- application commit: `71247070663a954fe7e424f05ce2194ee7f1614d`
- mode: `keyless-rehearsal-not-for-deployment`
- build configuration: `topo-vector`, API key `not-configured`
- package: 903 files, 38,658,383 bytes
- receipt SHA-256:
  `ad9f530ea63e64fe661b7ae6fb431e14c200f57ace42327eeecfcf5949955942`
- sanitized verification-log SHA-256:
  `1731f4d6ba3574180903e9de3ef96a78af1b323de3ce30e6a666cbc271e65ec0`
- public layer inventory: exactly eight content-addressed files; no public
  `results/` path

The isolated `npm run verify:clean` passed locked installation, type generation,
formatting, lint, generated type-checking, 101 tests in 11 files and the Next.js
16.3.3 static build. Installation audited 555 packages with zero vulnerabilities.
It emitted the existing ESLint 9.39.5 end-of-support deprecation and the expected
clean-build no-cache advisory.

An earlier rehearsal from the first implementation commit is preserved at
`m7-release-integration-rehearsal-20260908-01`; it is superseded because its
keyless build still selected `arcgis/oceans`. The approved M4 package, receipt,
verification evidence and rollback artifacts were not changed.

## Browser verification

Final evidence is retained under:

```text
C:\Users\teche\socal-whale-vessel-risk-m7-release-integration\data\interim\m7-release-integration\browser-verification-20260909-03
```

`browser-report.json` is 180,038 bytes with SHA-256
`b74e34343866591833d90f17604a5d4f39634a99b2be07c3db61a8ecd44b12bc`.
Headless Chrome 152 checked 390 × 844, 820 × 1180 and 1440 × 900. Each normal
run found one layer in exact order whale / vessel / exposure / domain / VSR and
feature counts 4,516 / 2,793 / 2,793 / 1 / 1. Initial visibility was off / off /
on / on / on. The product renderer had six classes; switching to log traffic,
visibility toggles and restoring boundaries changed no layer counts.

All viewports matched the generated results and pairing strings, showed the M5
processing dates, legends, limitations, VSR credit/disclaimer and a 3 px keyboard
focus outline, and had no horizontal overflow, visitor sign-in, console errors,
log errors or request failures. The layer panel scrolled at every viewport; the
document or results panel supplied the required results scrolling. Screenshots
were visually inspected.

A read-only local test server injected missing exposure bytes, a changed manifest
and malformed exposure JSON without modifying the candidate. Each case removed
only exposure (zero exposure layers), showed its warning, and left the results
panel plus whale, vessel, domain and VSR usable. The four unaffected layers each
remained present exactly once. The malformed case produced the two expected
ArcGIS layer-load console errors; normal runs had none. Earlier
partial/superseded browser attempts are preserved beside the final evidence
rather than overwritten.

This was a keyless local test. It does not prove keyed `arcgis/oceans`, production
referrers, actual deployed headers/compression, mid-range network performance or
public-origin behavior. Although the live publisher VSR layer loaded in the local
contexts with its expected UI credit and feature count, no release-time anonymous
identity, version or immutable-snapshot geometry comparison was performed or
claimed.

## Required next actions

The dependency update is already in the base commit, so no dependency rebase is
pending. After independent audit and authorized PR integration:

1. run both required `analysis` and `web` gates on the final PR head;
2. fetch merged `origin/main` and build a new uniquely named, keyed candidate
   from a clean checkout using the same retained input bytes;
3. review the candidate inventory and receipt, privately verify current account,
   key scope/referrers and free-capacity posture, and obtain explicit upload
   authorization;
4. perform the documented release-time anonymous VSR identity/version and exact
   snapshot geometry comparison; and
5. only after an authorized upload, verify every public byte, header/cache rule,
   keyed browser matrix and mid-range connection behavior at the stable origin.

Independent scientific audit, owner conclusion/map review and acceptance of
public wording remain separate gates. M5, M6 and M7 remain in progress; M8 and
M9 are not started.
