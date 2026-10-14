/**
 * Node.js version gate helpers (iteration 20 / Epic 20.3A).
 *
 * The frontend lockfile requires Node >= 20.19.0 (unplugin-auto-import /
 * unplugin-vue-components engines). CI, start_app.sh and scripts/setup_ubuntu.sh
 * call `scripts/check-node-version.mjs`, which uses these helpers, so a wrong
 * interpreter fails with a clear message before dependencies are installed or
 * a build is attempted.
 *
 * `engines.node` in package.json must use the single-comparator form
 * `>=X.Y.Z`. Any other syntax fails closed (returns ok: false) so the gate can
 * never silently pass on an unsupported range.
 */

const MIN_RANGE = /^>=(\d+)\.(\d+)\.(\d+)$/
const VERSION = /^(\d+)\.(\d+)\.(\d+)/

/** Parse a `>=X.Y.Z` range into a version object, or null if unsupported. */
export function parseMinimumNode(range) {
  if (typeof range !== 'string') return null
  const match = range.trim().match(MIN_RANGE)
  if (!match) return null
  return { major: Number(match[1]), minor: Number(match[2]), patch: Number(match[3]) }
}

/** Parse a concrete version (leading `v` and any suffix tolerated), or null. */
export function parseVersion(version) {
  if (typeof version !== 'string') return null
  const match = version.trim().replace(/^v/, '').match(VERSION)
  if (!match) return null
  return { major: Number(match[1]), minor: Number(match[2]), patch: Number(match[3]) }
}

/** Compare two parsed versions: -1 when a < b, 0 when equal, 1 when a > b. */
export function compareVersions(a, b) {
  for (const key of ['major', 'minor', 'patch']) {
    if (a[key] !== b[key]) return a[key] < b[key] ? -1 : 1
  }
  return 0
}

/**
 * Check `current` (e.g. process.versions.node) against an `engines.node` range.
 * Returns { ok, required?, current?, reason? }.
 */
export function checkNodeVersion(current, range) {
  const required = parseMinimumNode(range)
  if (!required) {
    return { ok: false, reason: `unsupported engines.node range: ${JSON.stringify(range)}` }
  }
  const parsed = parseVersion(current)
  if (!parsed) {
    return { ok: false, reason: `cannot parse Node version: ${JSON.stringify(current)}` }
  }
  return { ok: compareVersions(parsed, required) >= 0, required, current: parsed }
}
