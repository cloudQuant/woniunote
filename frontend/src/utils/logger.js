/**
 * @module utils/logger
 * @description 前端日志工具模块
 * 提供日志记录、存储、导出和控制台输出功能。
 * 支持 INFO, WARNING, ERROR 三种日志级别。
 */

/**
 * 日志级别常量
 * @enum {string}
 */
const LOG_LEVELS = {
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR'
}

/**
 * 最大日志存储数量
 * @constant {number}
 */
const MAX_LOGS = 100

/**
 * 内存日志存储数组
 * @type {Array<Object>}
 */
const logStorage = []

/**
 * 格式化当前时间为 ISO 字符串
 * @returns {string} ISO 格式的时间字符串
 */
function formatTime() {
  return new Date().toISOString()
}

/**
 * 添加日志到存储
 * 
 * 将日志添加到内存数组，并同步到 localStorage（保留最近50条）。
 * 
 * @param {string} level - 日志级别
 * @param {string} message - 日志消息
 * @param {any} data - 附加数据
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
 * 控制台输出样式配置
 */
const styles = {
  INFO: 'color: #2196F3; font-weight: bold;',
  WARNING: 'color: #FF9800; font-weight: bold;',
  ERROR: 'color: #F44336; font-weight: bold;'
}

/**
 * 记录 INFO 级别日志
 * 
 * @param {string} message - 日志消息
 * @param {any} [data=null] - 附加数据
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
 * 记录 WARNING 级别日志
 * 
 * @param {string} message - 日志消息
 * @param {any} [data=null] - 附加数据
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
 * 记录 ERROR 级别日志
 * 
 * @param {string} message - 日志消息
 * @param {Error|null} [error=null] - 错误对象
 * @param {any} [data=null] - 附加数据
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
 * 记录 API 请求日志
 * 
 * 根据状态码自动选择日志级别：
 * - >= 500: ERROR
 * - >= 400: WARNING
 * - < 400: INFO
 * 
 * @param {string} method - HTTP 方法
 * @param {string} url - 请求 URL
 * @param {number} status - HTTP 状态码
 * @param {number} duration - 请求耗时（毫秒）
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
 * 获取所有内存中的日志
 * @returns {Array<Object>} 日志数组副本
 */
export function getLogs() {
  return [...logStorage]
}

/**
 * 获取 localStorage 中存储的日志
 * @returns {Array<Object>} 日志数组
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
 * 清空所有日志（内存和 localStorage）
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
 * 导出日志为文本格式
 * @returns {string} 格式化后的日志文本
 */
export function exportLogs() {
  const logs = getLogs()
  return logs.map(log => {
    const dataStr = log.data ? ` | ${JSON.stringify(log.data)}` : ''
    return `${log.timestamp} [${log.level}] ${log.message}${dataStr}`
  }).join('\n')
}

// 默认导出对象
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
