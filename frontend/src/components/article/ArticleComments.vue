<template>
  <section class="comment-section">
    <h3 class="section-title">评论 ({{ totalComments }})</h3>

    <!-- 发表评论 -->
    <div class="comment-form" v-if="isLoggedIn">
      <el-input
        :model-value="newComment"
        @update:model-value="(value) => emit('update:newComment', value)"
        type="textarea"
        :rows="3"
        placeholder="写下你的评论..."
      />
      <el-button
        type="primary"
        @click="emit('submit-comment')"
        :loading="submittingComment"
        :disabled="!newComment.trim()"
      >
        发表评论
      </el-button>
    </div>
    <div v-else class="login-prompt">
      <router-link to="/login">登录</router-link> 后发表评论
    </div>

    <!-- 评论列表（支持楼中楼回复） -->
    <div class="comment-list">
      <div
        v-for="comment in comments"
        :key="comment.commentid"
        class="comment-item"
      >
        <div class="comment-avatar">
          <el-avatar :size="40" :src="comment.avatar">
            {{ (comment.nickname || 'U').charAt(0) }}
          </el-avatar>
        </div>
        <div class="comment-body">
          <div class="comment-header">
            <span class="comment-author">{{ comment.nickname || '匿名' }}</span>
            <span class="comment-time">{{ formatDate(comment.createtime) }}</span>
          </div>
          <div class="comment-content">{{ comment.content }}</div>
          <div class="comment-actions">
            <span @click="emit('agree', comment)">
              <el-icon><CaretTop /></el-icon> {{ comment.agreecount }}
            </span>
            <span @click="emit('oppose', comment)">
              <el-icon><CaretBottom /></el-icon> {{ comment.opposecount }}
            </span>
            <span v-if="isLoggedIn" @click="emit('start-reply', comment)">
              <el-icon><ChatLineSquare /></el-icon> 回复
            </span>
          </div>
          <div
            v-if="voteVerificationText(comment.commentid)"
            class="vote-verification"
            role="status"
            aria-live="polite"
          >
            {{ voteVerificationText(comment.commentid) }}
          </div>

          <!-- 回复输入框 -->
          <div v-if="replyingTo === comment.commentid" class="reply-form">
            <el-input
              :model-value="replyContent"
              @update:model-value="(value) => emit('update:replyContent', value)"
              type="textarea"
              :rows="2"
              placeholder="回复..."
            />
            <div class="reply-form-actions">
              <el-button size="small" @click="emit('cancel-reply')">取消</el-button>
              <el-button
                size="small"
                type="primary"
                :loading="submittingReply"
                :disabled="!replyContent.trim()"
                @click="emit('submit-reply', comment)"
              >
                回复
              </el-button>
            </div>
          </div>

          <!-- 楼中楼回复列表 -->
          <div v-if="comment.replies && comment.replies.length" class="reply-list">
            <div
              v-for="reply in comment.replies"
              :key="reply.commentid"
              class="reply-item"
            >
              <el-avatar :size="28" :src="reply.avatar">
                {{ (reply.nickname || 'U').charAt(0) }}
              </el-avatar>
              <div class="reply-body">
                <div class="comment-header">
                  <span class="comment-author">{{ reply.nickname || '匿名' }}</span>
                  <span class="comment-time">{{ formatDate(reply.createtime) }}</span>
                </div>
                <div class="comment-content">{{ reply.content }}</div>
                <div class="comment-actions">
                  <span @click="emit('agree', reply)">
                    <el-icon><CaretTop /></el-icon> {{ reply.agreecount }}
                  </span>
                  <span @click="emit('oppose', reply)">
                    <el-icon><CaretBottom /></el-icon> {{ reply.opposecount }}
                  </span>
                </div>
                <div
                  v-if="voteVerificationText(reply.commentid)"
                  class="vote-verification"
                  role="status"
                  aria-live="polite"
                >
                  {{ voteVerificationText(reply.commentid) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <EmptyState v-if="comments.length === 0" description="暂无评论" compact />
    </div>
  </section>
</template>

<script setup>
/**
 * @component ArticleComments
 * @description 文章评论区组件
 * 展示评论列表（含楼中楼回复）、发表评论与回复表单。所有状态由父级通过
 * props 注入，动作通过事件回传，具体逻辑见 composables/useArticleComments。
 */
import { CaretTop, CaretBottom, ChatLineSquare } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps({
  /**
   * 评论列表（含楼中楼 replies）
   */
  comments: {
    type: Array,
    default: () => []
  },
  /**
   * 评论总数（含回复）
   */
  totalComments: {
    type: Number,
    default: 0
  },
  /**
   * 是否已登录（控制发表/回复入口）
   */
  isLoggedIn: {
    type: Boolean,
    default: false
  },
  /**
   * 新评论内容（v-model:newComment）
   */
  newComment: {
    type: String,
    default: ''
  },
  /**
   * 评论提交中
   */
  submittingComment: {
    type: Boolean,
    default: false
  },
  /**
   * 正在回复的评论 ID（null 表示未展开回复框）
   */
  replyingTo: {
    type: [Number, String],
    default: null
  },
  /**
   * 回复内容（v-model:replyContent）
   */
  replyContent: {
    type: String,
    default: ''
  },
  /**
   * 回复提交中
   */
  submittingReply: {
    type: Boolean,
    default: false
  },
  /**
   * 投票提交结果未知时的待核实状态，按 commentid 索引。
   */
  pendingVoteVerifications: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits([
  'update:newComment',
  'update:replyContent',
  'submit-comment',
  'start-reply',
  'cancel-reply',
  'submit-reply',
  'agree',
  'oppose'
])

function voteVerificationText(commentId) {
  const state = props.pendingVoteVerifications[String(commentId)]
  if (!state) return ''
  if (state.countRefreshState === 'failed') {
    return '投票结果待核实（评论计数刷新失败）'
  }
  if (state.countRefreshState === 'refreshing') {
    return '投票结果待核实（正在刷新评论计数）'
  }
  return '投票结果待核实（计数已刷新，无法确认本人投票）'
}

/**
 * 格式化日期
 * @param {string} dateStr - ISO 日期字符串
 */
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}
</script>

<style scoped>
/* 评论区 */
.comment-section {
  margin-top: 40px;
  padding-top: 30px;
  border-top: 1px solid var(--wn-color-border);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px;
  color: var(--wn-color-text);
}

.comment-form {
  margin-bottom: 30px;
}

.comment-form .el-button {
  margin-top: 10px;
}

.login-prompt {
  padding: 15px;
  background: var(--wn-color-surface-soft);
  border-radius: var(--wn-radius-sm);
  text-align: center;
  margin-bottom: 30px;
}

.comment-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comment-item {
  display: flex;
  gap: 15px;
}

.comment-body {
  flex: 1;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.comment-author {
  font-weight: 500;
  color: var(--wn-color-text);
}

.comment-time {
  font-size: 12px;
  color: var(--wn-color-text-muted);
}

.comment-content {
  color: var(--wn-color-text-secondary);
  line-height: 1.6;
}

.comment-actions {
  margin-top: 10px;
  display: flex;
  gap: 20px;
}

.comment-actions span {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: var(--wn-color-text-muted);
  font-size: 13px;
  transition: color 0.3s;
}

.comment-actions span:hover {
  color: var(--wn-color-primary);
}

.vote-verification {
  margin-top: 6px;
  color: var(--wn-color-warning, #b7791f);
  font-size: 12px;
}

/* 楼中楼回复 */
.reply-form {
  margin-top: 12px;
}

.reply-form-actions {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.reply-list {
  margin-top: 12px;
  padding-left: 12px;
  border-left: 2px solid var(--wn-color-border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reply-item {
  display: flex;
  gap: 10px;
}

.reply-body {
  flex: 1;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .comment-item {
    gap: 10px;
  }
  .reply-list {
    padding-left: 8px;
  }
  .comment-actions {
    flex-wrap: wrap;
  }
}
</style>
