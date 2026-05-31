<template>
  <div class="empty-state" :style="{ padding: compact ? '24px 16px' : '48px 16px' }">
    <el-empty :description="description" :image-size="compact ? 80 : 120">
      <template v-if="$slots.default" #default>
        <slot />
      </template>
    </el-empty>
  </div>
</template>

<script setup>
/**
 * 通用空状态组件。
 * 用于列表/页面无数据时的统一展示，可选地通过默认插槽放置操作按钮。
 */
defineProps({
  /** 空状态描述文案 */
  description: {
    type: String,
    default: '暂无数据'
  },
  /** 紧凑模式（用于卡片内/侧栏等小区域） */
  compact: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
</style>
