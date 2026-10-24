#!/usr/bin/env node
/**
 * scripts/check-silent-catch.mjs
 *
 * Epic 18.1 guard: every `catch` block under src/** must either surface a user
 * facing message (ElMessage / notifyError) or be listed in the exemption table
 * below. A silent catch is how the "no feedback on failure" bug class creeps
 * back in.
 *
 * Classification (four buckets):
 *   - 带提示 (toast)              body contains ElMessage / notifyError
 *   - 仅日志 (log-only)           body only logs (console.* / logger helpers)
 *   - 刻意忽略 (intentionally ignored)  no toast, no log (empty / comment / fallback)
 *   - 表单校验链 (validation chain)     `.validate(...).catch(...)` promise chains
 *
 * Rule: a catch block that is neither exempt nor in the toast bucket is a
 * violation. Violations > 0 → print details and exit 1. Otherwise print the
 * four-bucket statistics and exit 0.
 *
 * Exemptions are matched by (file path relative to src/) + a substring of the
 * catch body — never by line number, which drifts on every edit.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const FRONTEND_ROOT = fileURLToPath(new URL('..', import.meta.url))
const SRC_ROOT = join(FRONTEND_ROOT, 'src')

/**
 * Built-in exemption list. Each entry: { file, match, reason, note? }.
 * `file` is relative to src/ with forward slashes; `match` must appear in the
 * catch body for the exemption to apply.
 */
const EXEMPTIONS = [
  {
    file: 'components/editor/UEditor.vue',
    match: '处理PDF上传结果失败',
    reason: 'PDF 上传结果处理失败：编辑器区域已有状态反馈，仅告警日志'
  },
  {
    file: 'components/editor/UEditor.vue',
    match: 'Failed to initialize UEditor',
    reason: '第三方编辑器初始化失败：降级为纯文本区域，不打断页面'
  },
  {
    file: 'components/editor/UEditor.vue',
    match: 'Error destroying editor',
    reason: '编辑器销毁失败：卸载路径无用户可见场景'
  },
  {
    file: 'components/editor/UEditor.vue',
    match: '忽略',
    reason: 'iframe 样式/主题同步失败：刻意忽略（2 处）'
  },
  {
    file: 'components/viewer/PdfViewer.vue',
    match: 'Render page error',
    reason: '组件内 error.value 已有 UI 反馈'
  },
  {
    file: 'components/viewer/PdfViewer.vue',
    match: 'Fetch PDF error',
    reason: '由外层 catch 统一写入 error.value 展示'
  },
  {
    file: 'components/viewer/PdfViewer.vue',
    match: 'Load PDF error',
    reason: '组件内 error.value 已有 UI 反馈'
  },
  {
    file: 'composables/useArticleRendering.js',
    match: 'MathJax渲染失败',
    reason: '公式渲染失败不影响正文阅读，静默降级'
  },
  {
    file: 'composables/useArticleRendering.js',
    match: 'already unmounted',
    reason: '卸载清理幂等操作，无用户可见影响'
  },
  {
    file: 'composables/useMathTraining.js',
    match: 'return iso',
    reason: 'formatTime 时间格式化兜底，非 API 调用'
  },
  {
    file: 'stores/theme.js',
    match: '忽略',
    reason: 'localStorage/matchMedia 不可用降级（3 处）'
  },
  {
    file: 'api/index.js',
    match: 'config._retried || config._sessionSnapshot || config.headers.Authorization',
    reason: 'syncSession 的 failClosed 已 notifyError；认证请求传播错误，匿名公开请求仅清除凭据后继续。api/index.spec.js 覆盖 IDB 失败的匿名请求与认证重放拒绝'
  },
  {
    file: 'api/index.js',
    match: 'error.config ||= config',
    reason: '仅补回 Axios config 后 rethrow；后续 rejection handler 按 config 清 loading 并传播错误。api/index.spec.js 覆盖 stale retry 拒绝时 loading 只结束一次'
  },
  {
    file: 'api/index.js',
    match: '401处理时无法确认登录会话，已阻止刷新和重放',
    reason: 'syncSession 的 failClosed 已 notifyError；此处阻止 refresh/replay 并拒绝请求。api/index.spec.js 覆盖权威存储不可用时拒绝认证重放'
  },
  {
    file: 'router/index.js',
    match: 'The store already fails closed and reports the storage error.',
    reason: 'syncSession 已由 store 清凭据并 notifyError；守卫只把受保护路由视为未登录，公开路由继续。router/index.spec.js 覆盖公开访问与硬刷新守卫，api/index.spec.js 覆盖 IDB 失败的匿名公开请求'
  },
  {
    file: 'stores/user.js',
    match: 'failClosed(error)',
    reason: 'failClosed 清内存凭据并调用 notifyError，两个调用点随后 rethrow；authSessionStorage.spec.js 覆盖 IDB fail-closed，api/index.spec.js 覆盖匿名公开请求和认证重放拒绝'
  },
  {
    file: 'stores/user.js',
    match: 'IndexedDB already committed; legacy mirrors only notify other tabs and',
    reason: '镜像失败发生在 IDB 事务完成后且只写兼容通知；API/路由每次同步仍读取权威记录。authSessionStorage.spec.js 覆盖事务提交，stores/user.spec.js 覆盖跨标签同步'
  },
  {
    file: 'stores/user.js',
    match: 'localClearError = error',
    reason: '本地撤销失败被带入 revoked:false 结果；AppHeader 对未确认撤销显示 warning。AppHeader.spec.js 覆盖该 warning，stores/user.spec.js 覆盖 logout 未确认结果'
  },
  {
    file: 'stores/user.js',
    match: 'return { revoked: false, error }',
    reason: '本地无凭据且会话存储不可用时返回未确认；AppHeader 对 revoked:false 显示 warning。AppHeader.spec.js 覆盖该反馈'
  },
  {
    file: 'stores/user.js',
    match: 'return { revoked: false, error: localClearError || error }',
    reason: 'logout API/本地清理失败均返回未确认；AppHeader 对 revoked:false 显示 warning。stores/user.spec.js 覆盖 API 失败结果，AppHeader.spec.js 覆盖 warning'
  },
  {
    file: 'test/authSessionStorageMock.js',
    match: 'Invalid test legacy mirrors are ignored like the production seeding path.',
    reason: '仅测试适配器解析初始化夹具中的损坏旧镜像；stores/user.spec.js 覆盖兼容种子路径'
  },
  {
    file: 'test/authSessionStorageMock.js',
    match: 'The legacy user mirror is optional test fixture data.',
    reason: '仅测试夹具中 user 镜像的可选 JSON 解析；authSessionStorage.spec.js 覆盖首次 legacy 种子初始化'
  },
  {
    file: 'utils/authSessionStorage.js',
    match: 'A malformed legacy mirror is ignored only while seeding the new authority.',
    reason: '仅在首次事务播种时容忍旧 user JSON 损坏，后续权威记录严格校验；authSessionStorage.spec.js 覆盖只首次读取 legacy 种子'
  },
  {
    file: 'utils/authSessionStorage.js',
    match: 'An invalid legacy canonical record falls back to the older key mirrors.',
    reason: '仅首次播种时让无效旧 canonical 回退兼容键，不用于权威 IDB 读取；authSessionStorage.spec.js 覆盖首次播种及后续不重读'
  },
  {
    file: 'utils/authSessionStorage.js',
    match: 'failTransaction(error)',
    reason: 'catch 调用 failTransaction 中止 IDB 写事务，onabort 拒绝 promise 并由 store failClosed/notifyError 后传播；authSessionStorage.spec.js 覆盖原子 compare-and-update 与 fail-closed'
  },
  {
    file: 'utils/authSessionStorage.js',
    match: 'failure = error\n              transaction.abort()',
    reason: '权威读取解析失败时中止只读事务，onabort 拒绝 promise 并由 store failClosed/notifyError；authSessionStorage.spec.js 覆盖无效记录 fail-closed'
  },
  {
    file: 'views/user/Profile.vue',
    match: 'The store reports the storage failure and clears in-memory credentials.',
    reason: 'mount 的 syncSession 已由 store failClosed/notifyError；页面不继续使用旧资料。user-views.spec.js 覆盖资料页旧账号响应隔离，api/index.spec.js 覆盖 IDB 失败反馈路径'
  },
  {
    file: 'views/WriteArticle.vue',
    match: '编辑器会话初始化失败，store 已提示并清除内存登录状态',
    reason: '编辑器初始化遇到会话存储错误时 store 的 failClosed 已通知用户，页面记录原因并禁止继续加载/提交；WriteArticle.spec.js 覆盖初始化后身份隔离，stores/user.spec.js 覆盖 failClosed 反馈'
  },
  {
    file: 'views/WriteArticle.vue',
    match: "logWarning('无法显示编辑恢复失败提示'",
    reason: '仅在 ElMessage.warning 反馈组件本身抛错后记录兜底日志；WriteArticle.spec.js 覆盖 warning 抛错时仍保留已恢复内容'
  },
  {
    file: 'views/WriteArticle.vue',
    match: '本地编辑恢复稿无法读取，已加载服务器内容；请检查浏览器存储设置',
    reason: '恢复稿读取失败通过 warnEditorRecovery 调用 ElMessage.warning，告知用户服务器内容已加载；WriteArticle.spec.js 覆盖该用户反馈'
  },
  {
    file: 'views/WriteArticle.vue',
    match: "warnEditorRecovery('已恢复未保存内容，但无法清理本地恢复副本', error)",
    reason: '恢复稿清理失败通过 warnEditorRecovery 调用 ElMessage.warning，同时保留已恢复内容；WriteArticle.spec.js 覆盖该用户反馈'
  },
  {
    file: 'utils/authNavigation.js',
    match: 'return null',
    reason: 'router.resolve 解析失败时拒绝 redirect；authNavigation.spec.js 覆盖抛错路径'
  },
  {
    file: 'utils/editorRecovery.js',
    match: 'return null',
    reason: '损坏的本地编辑快照按不可恢复处理；editorRecovery.spec.js 覆盖 malformed JSON'
  },
  {
    file: 'utils/editorRecovery.js',
    match: 'reportPageExitError(registration, error)',
    reason: '页面退出保存失败交给编辑器的 onPageExitError 用户反馈 wrapper；editorRecovery.spec.js 覆盖页面退出错误回调'
  },
  {
    file: 'utils/editorRecovery.js',
    match: "logWarning('无法报告页面离开时的编辑恢复失败'",
    reason: '仅在 onPageExitError 用户反馈 wrapper 自身抛错时记录兜底日志；editorRecovery.spec.js 覆盖反馈回调抛错'
  },
  {
    file: 'utils/logger.js',
    match: 'localStorage 可能已满',
    reason: '日志落盘失败静默降级，不影响业务'
  },
  {
    file: 'utils/logger.js',
    match: 'return []',
    reason: '日志读取失败返回空数组，不影响业务'
  },
  {
    file: 'utils/logger.js',
    match: 'ignore',
    reason: '日志清理失败静默降级，不影响业务'
  },
  {
    file: 'components/article/ArticleCard.vue',
    match: "return ''",
    reason: 'CSS 变量读取兜底，非 API 调用'
  },
  {
    file: 'api/index.js',
    match: 'return null',
    reason: 'refresh token 静默刷新失败，由 401 分支统一处理'
  }
]

const TOAST_PATTERN = /ElMessage|notifyError/
const LOG_PATTERN = /console\.(log|warn|error|info|debug)|logInfo|logWarning|logError|logDebug/
const VALIDATION_CHAIN_PATTERN = /\.validate\([^)]*\)\s*\.catch\(/g

function isWordChar(ch) {
  return ch !== undefined && /[\w$]/.test(ch)
}

function skipSpaces(source, index) {
  let i = index
  while (i < source.length && /\s/.test(source[i])) i++
  return i
}

function skipString(source, start) {
  const quote = source[start]
  let i = start + 1
  while (i < source.length) {
    if (source[i] === '\\') {
      i += 2
      continue
    }
    if (source[i] === quote) return i + 1
    i++
  }
  return i
}

/**
 * Find the index of the delimiter matching the one at `openIndex`.
 * Skips strings and comments so braces inside literals do not confuse us.
 */
function matchDelimiter(source, openIndex) {
  const open = source[openIndex]
  const close = open === '{' ? '}' : ')'
  let depth = 0
  let i = openIndex
  while (i < source.length) {
    const ch = source[i]
    if (ch === '/' && source[i + 1] === '/') {
      const nl = source.indexOf('\n', i)
      i = nl === -1 ? source.length : nl + 1
      continue
    }
    if (ch === '/' && source[i + 1] === '*') {
      const end = source.indexOf('*/', i + 2)
      i = end === -1 ? source.length : end + 2
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') {
      i = skipString(source, i)
      continue
    }
    if (ch === open) depth++
    else if (ch === close) {
      depth--
      if (depth === 0) return i
    }
    i++
  }
  return -1
}

function lineOf(source, index) {
  let line = 1
  for (let i = 0; i < index; i++) {
    if (source[i] === '\n') line++
  }
  return line
}

/**
 * Collect every brace-bodied catch block (`catch {}` / `catch (e) {}`).
 * `.catch(...)` promise chains (no block) are collected separately.
 */
function findCatchBlocks(source) {
  const blocks = []
  let i = 0
  while (i < source.length) {
    const ch = source[i]
    if (ch === '/' && source[i + 1] === '/') {
      const nl = source.indexOf('\n', i)
      i = nl === -1 ? source.length : nl + 1
      continue
    }
    if (ch === '/' && source[i + 1] === '*') {
      const end = source.indexOf('*/', i + 2)
      i = end === -1 ? source.length : end + 2
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') {
      i = skipString(source, i)
      continue
    }
    const isCatch =
      source.startsWith('catch', i) &&
      !isWordChar(source[i - 1]) &&
      source[i - 1] !== '.' &&
      !isWordChar(source[i + 5])
    if (!isCatch) {
      i++
      continue
    }

    let j = skipSpaces(source, i + 5)
    if (source[j] === '(') {
      const close = matchDelimiter(source, j)
      if (close === -1) {
        i = j
        continue
      }
      j = skipSpaces(source, close + 1)
    }
    if (source[j] === '{') {
      const end = matchDelimiter(source, j)
      if (end === -1) {
        i = j
        continue
      }
      blocks.push({
        line: lineOf(source, i),
        body: source.slice(j + 1, end)
      })
      i = end + 1
      continue
    }
    i = j
  }
  return blocks
}

function countValidationChains(source) {
  return (source.match(VALIDATION_CHAIN_PATTERN) || []).length
}

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      out.push(...walk(full))
    } else if (/\.(vue|js)$/.test(entry) && !entry.endsWith('.spec.js')) {
      out.push(full)
    }
  }
  return out
}

function classify(body) {
  if (TOAST_PATTERN.test(body)) return 'toast'
  if (LOG_PATTERN.test(body)) return 'log-only'
  return 'ignored'
}

function findExemption(relFile, body) {
  return EXEMPTIONS.find((rule) => rule.file === relFile && body.includes(rule.match))
}

const CATEGORY_LABELS = {
  toast: '带提示 (ElMessage/notifyError)',
  'log-only': '仅日志',
  ignored: '刻意忽略',
  'validation-chain': '表单校验链'
}

function main() {
  const verbose = process.argv.includes('--verbose')
  const files = walk(SRC_ROOT).sort()
  const counts = { toast: 0, 'log-only': 0, ignored: 0, 'validation-chain': 0 }
  const violations = []
  let exempted = 0
  let totalBlocks = 0

  for (const full of files) {
    const relFile = relative(SRC_ROOT, full).split('\\').join('/')
    const source = readFileSync(full, 'utf8')
    const blocks = findCatchBlocks(source)
    if (verbose && blocks.length > 0) {
      console.log(`  [verbose] ${relFile}: ${blocks.length} catch blocks @ lines ${blocks.map((b) => b.line).join(', ')}`)
    }

    for (const block of blocks) {
      totalBlocks++
      const category = classify(block.body)
      counts[category]++

      const exemption = findExemption(relFile, block.body)
      if (exemption) {
        exempted++
        continue
      }
      if (category !== 'toast') {
        const firstLine = block.body.trim().split('\n')[0].slice(0, 80)
        violations.push({ relFile, line: block.line, category, firstLine })
      }
    }

    counts['validation-chain'] += countValidationChains(source)
  }

  console.log(`scan-silent-catch: ${files.length} files, ${totalBlocks} catch blocks`)
  for (const key of Object.keys(CATEGORY_LABELS)) {
    console.log(`  ${CATEGORY_LABELS[key]}: ${counts[key]}`)
  }
  console.log(`  豁免 (exempted): ${exempted}`)
  console.log(`  违规 (violations): ${violations.length}`)

  if (violations.length > 0) {
    console.error('\nSilent catch blocks without user feedback and without exemption:')
    for (const v of violations) {
      console.error(`  src/${v.relFile}:${v.line} [${v.category}] ${v.firstLine}`)
    }
    console.error(
      '\nFix: call notifyError(error, "<场景文案>") in the catch, or add a justified entry to EXEMPTIONS.'
    )
    process.exit(1)
  }

  console.log('OK: every catch block surfaces feedback or is explicitly exempted.')
}

main()
