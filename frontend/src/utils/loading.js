/**
 * @module utils/loading
 * @description 全局请求 loading 管理。
 *
 * 通过引用计数管理一个全局进度指示（顶部进度条）。多个并发请求只显示一次，
 * 全部结束后关闭。某些请求（如静默刷新 token、轮询）可通过 config 跳过。
 */

let pendingCount = 0
let activeBar = null

/**
 * 启动一个简单的顶部进度条（基于 DOM，无第三方依赖）。
 */
function ensureBar() {
  if (activeBar) return activeBar
  const bar = document.createElement('div')
  bar.id = 'global-loading-bar'
  bar.style.cssText = [
    'position:fixed',
    'top:0',
    'left:0',
    'height:3px',
    'width:0%',
    'background:linear-gradient(90deg,#409eff,#67c23a)',
    'box-shadow:0 0 8px rgba(64,158,255,.6)',
    'z-index:99999',
    'transition:width .2s ease,opacity .3s ease',
    'opacity:1'
  ].join(';')
  document.body.appendChild(bar)
  activeBar = bar
  return bar
}

function setProgress(pct) {
  const bar = ensureBar()
  bar.style.opacity = '1'
  bar.style.width = pct + '%'
}

function finish() {
  if (!activeBar) return
  activeBar.style.width = '100%'
  const bar = activeBar
  activeBar = null
  setTimeout(() => {
    bar.style.opacity = '0'
    setTimeout(() => bar.remove(), 300)
  }, 200)
}

/**
 * 标记一个请求开始。
 */
export function startLoading() {
  pendingCount++
  if (pendingCount === 1) {
    setProgress(30)
  } else {
    // 多请求时缓慢推进，制造进度感
    setProgress(Math.min(30 + pendingCount * 10, 80))
  }
}

/**
 * 标记一个请求结束。计数归零时关闭进度条。
 */
export function stopLoading() {
  if (pendingCount > 0) pendingCount--
  if (pendingCount === 0) {
    finish()
  }
}

/**
 * 重置（用于异常兜底）。
 */
export function resetLoading() {
  pendingCount = 0
  finish()
}
