import { ElMessage } from 'element-plus'

/**
 * 统一错误提示：优先用后端/拦截器构造的 error.message，空串时落到场景化 fallback。
 * grouping 防并发提示风暴。
 * @param {Error|{ message?: string }|null|undefined} error - 捕获到的错误对象
 * @param {string} [fallback='请求失败'] - error.message 为空时的场景化兜底文案
 */
export function notifyError(error, fallback = '请求失败') {
  ElMessage({ message: error?.message || fallback, type: 'error', grouping: true })
}
