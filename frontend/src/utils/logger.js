/**
 * 前端日志工具
 * - info: 正常操作日志
 * - error: 错误日志
 * - warning: 警告日志
 */

const LOG_LEVELS = {
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR'
}

// 日志存储（最多保留100条）
const MAX_LOGS = 100
const logStorage = []

/**
 * 格式化日志时间
 */
function formatTime() {
  return new Date().toISOString()
}

/**
 * 添加日志到存储
 */
function addToStorage(level, message, data) {
  const logEntry = {
    timestamp: formatTime(),
    level,
    message,
    data
  }
  
  logStorage.push(logEntry)
  
  // 限制存储大小
  if (logStorage.length > MAX_LOGS) {
    logStorage.shift()
  }
  
  // 同时保存到 localStorage
  try {
    localStorage.setItem('woniunote_logs', JSON.stringify(logStorage.slice(-50)))
  } catch (e) {
    // localStorage 可能已满
  }
}

/**
 * 控制台输出样式
 */
const styles = {
  INFO: 'color: #2196F3; font-weight: bold;',
  WARNING: 'color: #FF9800; font-weight: bold;',
  ERROR: 'color: #F44336; font-weight: bold;'
}

/**
 * 记录INFO日志
 */
export function logInfo(message, data = null) {
  const prefix = `[${formatTime()}] [INFO]`
  
  if (data) {
    console.log(`%c${prefix}`, styles.INFO, message, data)
  } else {
    console.log(`%c${prefix}`, styles.INFO, message)
  }
  
  addToStorage(LOG_LEVELS.INFO, message, data)
}

/**
 * 记录WARNING日志
 */
export function logWarning(message, data = null) {
  const prefix = `[${formatTime()}] [WARNING]`
  
  if (data) {
    console.warn(`%c${prefix}`, styles.WARNING, message, data)
  } else {
    console.warn(`%c${prefix}`, styles.WARNING, message)
  }
  
  addToStorage(LOG_LEVELS.WARNING, message, data)
}

/**
 * 记录ERROR日志
 */
export function logError(message, error = null, data = null) {
  const prefix = `[${formatTime()}] [ERROR]`
  
  const errorInfo = error ? {
    name: error.name,
    message: error.message,
    stack: error.stack
  } : null
  
  if (error) {
    console.error(`%c${prefix}`, styles.ERROR, message, error, data)
  } else {
    console.error(`%c${prefix}`, styles.ERROR, message, data)
  }
  
  addToStorage(LOG_LEVELS.ERROR, message, { error: errorInfo, ...data })
}

/**
 * 记录API请求
 */
export function logRequest(method, url, status, duration) {
  const message = `${method} ${url} - ${status} (${duration}ms)`
  
  if (status >= 500) {
    logError(`API请求失败: ${message}`)
  } else if (status >= 400) {
    logWarning(`API请求警告: ${message}`)
  } else {
    logInfo(`API请求: ${message}`)
  }
}

/**
 * 获取所有日志
 */
export function getLogs() {
  return [...logStorage]
}

/**
 * 获取存储的日志
 */
export function getStoredLogs() {
  try {
    const stored = localStorage.getItem('woniunote_logs')
    return stored ? JSON.parse(stored) : []
  } catch (e) {
    return []
  }
}

/**
 * 清空日志
 */
export function clearLogs() {
  logStorage.length = 0
  try {
    localStorage.removeItem('woniunote_logs')
  } catch (e) {
    // ignore
  }
}

/**
 * 导出日志为文本
 */
export function exportLogs() {
  const logs = getLogs()
  return logs.map(log => {
    const dataStr = log.data ? ` | ${JSON.stringify(log.data)}` : ''
    return `${log.timestamp} [${log.level}] ${log.message}${dataStr}`
  }).join('\n')
}

// 默认导出
export default {
  info: logInfo,
  warning: logWarning,
  error: logError,
  request: logRequest,
  getLogs,
  getStoredLogs,
  clearLogs,
  exportLogs
}
