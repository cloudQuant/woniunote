/**
 * @module composables/useArticleComments
 * @description 文章评论区逻辑
 * 管理评论列表加载、发表评论、楼中楼回复与点赞/反对。状态与方法通过
 * 返回值交给视图层，再以 props/events 分发给评论区子组件渲染。
 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { commentApi } from '@/api'
import { notifyError } from '@/utils/errorToast'

/**
 * 文章评论区逻辑 composable
 * @param {Object} options
 * @param {import('vue').Ref<Object|null>} options.article - 文章数据 ref
 *   （提交评论/回复时从中读取 articleid）
 * @returns {Object} 评论区状态（含评论总数）与操作方法
 */
export function useArticleComments({ article }) {
  const route = useRoute()
  const router = useRouter()
  const userStore = useUserStore()

  const comments = ref([])
  const newComment = ref('')
  const submittingComment = ref(false)
  // A refreshed aggregate count cannot prove whether this user’s vote committed.
  // Keep unknown outcomes visible until the page is reloaded or the user resolves it.
  const pendingVoteVerifications = ref({})

  // 回复（楼中楼）状态
  const replyingTo = ref(null)
  const replyContent = ref('')
  const submittingReply = ref(false)

  /**
   * 评论总数（含楼中楼回复）
   */
  const totalComments = computed(() => {
    return comments.value.reduce((sum, c) => sum + 1 + (c.replies ? c.replies.length : 0), 0)
  })

  /**
   * 获取评论列表
   */
  async function fetchComments() {
    try {
      const res = await commentApi.getByArticle(route.params.id, { page: 1, page_size: 50 })
      comments.value = res.data
      return true
    } catch (error) {
      console.error('获取评论失败:', error)
      notifyError(error, '获取评论失败')
      return false
    }
  }

  function isUnknownVoteOutcome(error) {
    return error?.errorCode === 'WRITE_OUTCOME_UNKNOWN' ||
      error?.response?.data?.error_code === 'WRITE_OUTCOME_UNKNOWN' ||
      error?.response?.data?.data?.error_code === 'WRITE_OUTCOME_UNKNOWN' ||
      !error?.response
  }

  async function refreshAfterUnknownVote(comment, voteType) {
    const commentId = String(comment.commentid)
    pendingVoteVerifications.value = {
      ...pendingVoteVerifications.value,
      [commentId]: { voteType, countRefreshState: 'refreshing' }
    }
    ElMessage.warning('投票结果暂未确认，系统未自动重试；正在刷新评论计数。')

    const refreshed = await fetchComments()
    pendingVoteVerifications.value = {
      ...pendingVoteVerifications.value,
      [commentId]: { voteType, countRefreshState: refreshed ? 'refreshed' : 'failed' }
    }
  }

  /**
   * 提交评论
   */
  async function submitComment() {
    if (!newComment.value.trim()) return

    submittingComment.value = true
    try {
      await commentApi.create({
        articleid: article.value.articleid,
        content: newComment.value.trim()
      })
      newComment.value = ''
      await fetchComments()
      ElMessage.success('评论发表成功')
    } catch (error) {
      console.error('发表评论失败:', error)
      notifyError(error, '发表评论失败')
    } finally {
      submittingComment.value = false
    }
  }

  /**
   * 开始回复某条评论（楼中楼）
   * @param {Object} comment - 被回复的评论
   */
  function startReply(comment) {
    if (!userStore.isLoggedIn) {
      router.push({ name: 'Login' })
      return
    }
    replyingTo.value = comment.commentid
    replyContent.value = ''
  }

  /**
   * 取消回复
   */
  function cancelReply() {
    replyingTo.value = null
    replyContent.value = ''
  }

  /**
   * 提交回复
   * @param {Object} comment - 被回复的顶层评论
   */
  async function submitReply(comment) {
    if (!replyContent.value.trim()) return

    submittingReply.value = true
    try {
      await commentApi.create({
        articleid: article.value.articleid,
        content: replyContent.value.trim(),
        replyid: comment.commentid
      })
      cancelReply()
      await fetchComments()
      ElMessage.success('回复成功')
    } catch (error) {
      console.error('回复失败:', error)
      notifyError(error, '回复失败')
    } finally {
      submittingReply.value = false
    }
  }

  /**
   * 点赞评论。计数以服务端重新读取为准，不在客户端乐观自增。
   * @param {Object} comment - 评论对象
   */
  async function agreeComment(comment) {
    if (!userStore.isLoggedIn) {
      router.push({ name: 'Login' })
      return
    }

    try {
      await commentApi.agree(comment.commentid)
      await fetchComments()
    } catch (error) {
      console.error('点赞失败:', error)
      if (isUnknownVoteOutcome(error)) {
        await refreshAfterUnknownVote(comment, 'agree')
      } else {
        notifyError(error, '点赞失败')
      }
    }
  }

  /**
   * 反对评论。计数以服务端重新读取为准，不在客户端乐观自增。
   * @param {Object} comment - 评论对象
   */
  async function opposeComment(comment) {
    if (!userStore.isLoggedIn) {
      router.push({ name: 'Login' })
      return
    }

    try {
      await commentApi.oppose(comment.commentid)
      await fetchComments()
    } catch (error) {
      console.error('踩失败:', error)
      if (isUnknownVoteOutcome(error)) {
        await refreshAfterUnknownVote(comment, 'oppose')
      } else {
        notifyError(error, '踩失败')
      }
    }
  }

  return {
    // 状态
    comments,
    newComment,
    submittingComment,
    pendingVoteVerifications,
    replyingTo,
    replyContent,
    submittingReply,
    // 计算属性
    totalComments,
    // 方法
    fetchComments,
    submitComment,
    startReply,
    cancelReply,
    submitReply,
    agreeComment,
    opposeComment
  }
}
