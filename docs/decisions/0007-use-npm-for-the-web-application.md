# 0007 — Use npm as the web application's package manager

**Status:** Accepted
**Date:** 2026-08-25

## Context

The application-foundation milestone needed a package manager before anything
could be installed. The choice is small but sticky: it fixes the lockfile
format, and a second lockfile appearing later produces dependency trees that
disagree in ways nobody notices until a build breaks somewhere else.

What was known at the time:

- The author's machine had Node.js 22.16.0 and npm 10.9.2. Neither pnpm nor Yarn
  was installed.
- Next.js 16.3.3 requires Node.js `>=20.9.0`; the installed runtime satisfies it.
- Nothing in this project is a monorepo, and nothing shares dependencies between
  the application and the (not yet existing) Python analysis package. The
  workspace features that justify pnpm or Yarn have nothing to manage here.
- The ArcGIS Maps SDK is a large dependency tree, so install time and disk use
  are not trivial — pnpm's content-addressed store would genuinely save both.
- A reviewer opening this repository should be able to run it without installing
  a package manager first.

## Decision

npm is the package manager for `web/`. `web/package-lock.json` is committed and
kept in step with `package.json` in the same commit as any dependency change.

Do not add a second lockfile. Introducing a different package manager is a
change to this record, not a preference exercised in passing.

## Consequences

- Anyone with Node.js can clone and run the application. No prerequisite install
  step, and nothing extra to document.
- The deployment platform's default build command works unmodified — every
  static host understands `npm install && npm run build`.
- Installs are slower and use more disk than pnpm would, most visibly with the
  ArcGIS SDK. This is accepted: it costs time on a cold install, and nothing at
  runtime or in the deployed output.
- If a Node-based tool is ever added outside `web/`, this record does not cover
  it, and the workspace question should be reopened deliberately rather than
  answered by whichever manager gets typed first.

## Alternatives considered

**pnpm.** Faster, and markedly more disk-efficient for a dependency tree this
size. Rejected because it is not installed, would become a prerequisite for
every contributor and for the build environment, and its main advantage —
workspaces — has nothing to manage in a single-application repository. Worth
revisiting if the repository grows a second Node package.

**Yarn.** No advantage over npm here, and the same prerequisite problem as pnpm.

**Bun.** Faster still, but a change of runtime as well as package manager, with
less certain support across static hosts. Not a reasonable thing to bet the
deployment path on for a saving that does not matter at this size.
