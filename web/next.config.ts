import type { NextConfig } from "next";

/**
 * The application is a static, client-rendered presentation layer. It has no
 * backend, no database, and no server-side analytical processing — every
 * analytical result is computed offline and published as a hosted layer or a
 * small committed file. See docs/architecture.md.
 *
 * `output: "export"` therefore matches the architecture rather than merely
 * being convenient: it makes a Node server impossible to depend on by
 * accident, and produces a plain HTML/CSS/JS bundle in `out/` that any static
 * host can serve over HTTPS.
 */
const nextConfig: NextConfig = {
  output: "export",

  // Emit `out/<route>/index.html` so hosts that do not rewrite extensionless
  // URLs still resolve every route.
  trailingSlash: true,

  // `next dev` otherwise writes its own AGENTS.md and CLAUDE.md into this
  // directory. The repository already has agent guidance at its root, and a
  // second, generated set of instructions here would compete with it.
  agentRules: false,

  // `next/image` optimization requires a server. Nothing in the application
  // relies on it today; this makes the constraint explicit rather than
  // letting a future `<Image>` silently break the export.
  images: { unoptimized: true },
};

export default nextConfig;
