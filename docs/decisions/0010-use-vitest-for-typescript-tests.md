# 0010 — Use Vitest for TypeScript tests

**Status:** Accepted
**Date:** 2026-08-25

## Context

[architecture.md](../architecture.md) lists "test framework and toolchain for
both Python and TypeScript" as a deferred decision, to be resolved "when the
first code is written" — on the grounds that choosing a framework before there
is anything to test is premature. The application-foundation milestone produced
the first TypeScript code, so the TypeScript half of that deferral is now due.

The same document sets the scope: application code gets type checking and
linting, plus tests for non-trivial presentational logic. UI tests are not a
Version 1 priority, and the SDK, ArcGIS Online, and upstream datasets are
explicitly not unit-tested. So what needs a framework is a small amount of pure
logic — currently how environment values resolve into map configuration, and how
the map's reported load failures become text for the interface — with the
expectation of number formatting and value classification later.

Constraints that mattered: the project is ESM and TypeScript throughout; the
runtime is Node 22; and nothing should require a build step or a transform
configuration that later drifts out of step with the application's own.

## Decision

Vitest is the test framework for TypeScript. `npm test` runs the suite once;
`npm run test:watch` watches. Configuration is `web/vitest.config.mts`, which
resolves the `@/` import alias to match `tsconfig.json`.

Tests live beside the code they cover as `*.test.ts`, and the runner is scoped
to `lib/` — the layer where the logic worth testing lives.

This record covers TypeScript only. The Python test framework stays deferred
until the analysis package exists.

## Consequences

- TypeScript and ESM run without a transform step to configure or keep in sync,
  because Vitest uses Vite's transform pipeline.
- The choice does not constrain the Python decision, which is made separately
  against whatever the analysis package needs.
- Should UI-level tests ever become worthwhile, Vitest supports them through
  jsdom or a browser mode, so the framework does not have to be revisited to add
  them. Version 1 does not plan to.
- Vitest is a development dependency in `web/` and does not reach the deployed
  build.
- Scoping the runner to `lib/` means a test placed elsewhere is silently not
  run. Widening the `include` pattern is part of adding tests outside that
  directory.

## Alternatives considered

**Node's built-in test runner (`node:test`).** No dependency at all, which is
genuinely attractive. Rejected because running TypeScript through it still needs
loader or build configuration of its own, duplicating what the application
already has and creating a second place for module resolution to disagree.

**Jest.** The most widely known option, but its ESM and TypeScript support needs
more configuration than Vitest for this project's shape, and none of its
ecosystem advantages apply to a handful of pure functions.

**No test framework, relying on type checking and linting alone.** Considered
seriously, given how little logic there is. Rejected because the cases worth
covering are exactly the ones types do not catch: a blank environment variable
that still looks set, a pasted key that kept its line break, a failure with no
message that would otherwise disappear, and a transposed coordinate pair that
type-checks perfectly and puts the map somewhere else entirely.
