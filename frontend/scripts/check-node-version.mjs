#!/usr/bin/env node
/**
 * Node.js version gate for the WoniuNote frontend.
 *
 * Reads `engines.node` from frontend/package.json (single-comparator form
 * `>=X.Y.Z`) and fails with a non-zero exit code when the running interpreter
 * does not satisfy it. Called by CI, start_app.sh and scripts/setup_ubuntu.sh
 * BEFORE dependencies are installed or a build is started, so a wrong Node
 * version produces a clear error instead of a confusing install/build failure
 * (or a stale artifact being served).
 *
 * Usage:
 *   node scripts/check-node-version.mjs          # exit 1 when unsupported
 *   node scripts/check-node-version.mjs --print  # print requirement only
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'
import { checkNodeVersion } from '../src/utils/nodeVersion.js'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const packageJsonPath = join(scriptDir, '..', 'package.json')

function main() {
  const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf8'))
  const range = pkg.engines?.node

  if (process.argv.includes('--print')) {
    console.log(range ?? '')
    return 0
  }

  const result = checkNodeVersion(process.versions.node, range)
  if (result.ok) {
    console.log(`Node ${process.versions.node} satisfies engines.node "${range}"`)
    return 0
  }

  console.error(`[错误] Node 版本不满足要求: 当前 ${process.versions.node}，需要 "${range}"`)
  if (result.reason) {
    console.error(`       ${result.reason}`)
  }
  console.error('       请升级 Node.js（CI 与部署脚本使用 Node 22 LTS）后重试。')
  return 1
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main())
}
