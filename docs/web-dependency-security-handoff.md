# Web dependency security handoff

Current as of 2026-09-08. This handoff records the narrowly scoped web
dependency maintenance prompted by two newly reported advisories. It does not
change application behavior, architecture, analytical artifacts, release
staging, deployment, or external accounts.

## Checkout, base, and scope

- Branch: `chore/web-dependency-security`
- Worktree:
  `C:\Users\teche\socal-whale-vessel-risk-dependency-security`
- Base: `e7752b1b014e68d8cdba27f26c989c1bdf2c54d7`, the current
  `origin/main` after fetching on 2026-09-08
- Dependency commit: `c0d3f17eb88452e7846a69ef8810ed73986c4f17`
  (`chore: update audited web dependencies`)
- The handoff is committed separately in the commit containing this revision.
- No push, pull request, merge, deployment, credential operation, Vercel
  operation, or ArcGIS operation was performed.

The primary checkout was clean, and the requested branch and worktree did not
already exist. The dedicated branch was created from `origin/main`; no work was
performed on `main` or in another milestone session's checkout.

## Investigation and change

Node.js 22.16.0 and npm 10.9.2 were used. `npm ci` installed the committed web
tree before investigation. A fresh `npm audit` then reported exactly two high
severity findings:

| Advisory | Dependency path | Before | Patched boundary | After |
|---|---|---:|---:|---:|
| [`GHSA-2883-xcg3-v3hh`](https://github.com/advisories/GHSA-2883-xcg3-v3hh) | `eslint@9.39.5` -> `@eslint/eslintrc@3.3.6` -> `js-yaml` | 4.3.1 | 4.3.2 | 4.3.2 |
| [`GHSA-rgj7-g3m4-5g8c`](https://github.com/advisories/GHSA-rgj7-g3m4-5g8c) | `next@16.3.3` -> optional `sharp` | 0.35.3 | 0.35.4 | 0.35.4 |

Both parents already allowed the patched releases: `@eslint/eslintrc@3.3.6`
declares `js-yaml ^4.3.0`, and Next.js 16.3.3 declares optional
`sharp ^0.35.3`. The lockfile was therefore refreshed only for those packages
with:

```text
npm update js-yaml sharp --package-lock-only
```

`web/package.json` did not change. The lockfile moves `js-yaml` from 4.3.1 to
4.3.2 and `sharp` plus its matching optional platform packages from 0.35.3 to
0.35.4. The platform packages' matching `@img/sharp-libvips-*` dependencies
move from 1.3.2 to 1.3.3, and sharp's WASM metadata moves its compatible
`@emnapi/runtime` range from `^1.11.1` to `^1.11.3`. These are the dependency
records published with sharp 0.35.4, not unrelated resolution churn. Next.js,
React, ArcGIS, ESLint, and all other direct dependency versions remain
unchanged. No override was added and no forced audit fix was used.

## Verification

The required clean gate completed successfully from `web/`:

| Check | Result |
|---|---|
| `npm run verify:clean` | Passed; `npm ci` installed 554 packages and reported zero vulnerabilities, then all remaining web gates passed |
| `next typegen` | Passed |
| `npm run format:check` | Passed |
| `npm run lint` | Passed |
| `tsc --noEmit` | Passed |
| `npm test` | Passed; 91 tests across 11 files |
| `npm run build` | Passed; `/` and `/_not-found` reported as statically prerendered content |
| Static-export check | `web/out/index.html` exists after the clean build |
| Final `npm audit` | Zero vulnerabilities |
| Final `npm ls js-yaml sharp --all` | `js-yaml@4.3.2` and `sharp@0.35.4` at the expected paths |

The dependency and documentation diffs were reviewed, `git diff --check`
passed, and staged changes were checked for credential-like strings and
generated or analytical data. No application source, Next.js configuration,
analytical input/output, formula, artifact pin, deployment file, credential, or
generated data changed.

These are automated installation, audit, formatting, lint, type, unit-test, and
build results. Browser behavior was not rechecked because the change is limited
to compatible transitive lockfile patches and makes no source or configuration
change. Static export was verified through the production build output, not a
served-browser session.

## Remaining concerns and next action

- The final npm audit has no remaining findings as of 2026-09-08. Audit results
  are registry-state observations and should be rerun during independent review.
- npm emits an existing deprecation warning for `eslint@9.39.5`. Resolving that
  would broaden this change beyond the reported advisories, so it remains
  unchanged for separate maintenance.
- Independent review and the clean Linux CI jobs have not run because this
  branch has not been pushed and no pull request was opened.

Next action: independently review commit `c0d3f17eb88452e7846a69ef8810ed73986c4f17`
and the handoff commit, rerun the clean web gate and npm audit, then follow the
author-controlled push and pull-request workflow if accepted.
