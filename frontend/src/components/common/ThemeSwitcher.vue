<template>
  <el-popover
    v-model:visible="isOpen"
    placement="bottom-end"
    :width="368"
    trigger="click"
    popper-class="theme-switcher-popover"
  >
    <template #reference>
      <button
        type="button"
        class="theme-switcher-trigger"
        :title="`当前主题：${themeStore.currentMeta?.name || ''}`"
        :aria-label="`切换主题，当前为${themeStore.currentMeta?.name || ''}`"
        aria-haspopup="dialog"
        :aria-expanded="String(isOpen)"
      >
        <el-icon class="trigger-icon"><Brush /></el-icon>
        <span class="trigger-label">主题</span>
      </button>
    </template>

    <div class="theme-panel" role="dialog" aria-label="主题选择器">
      <div class="theme-panel-header">
        <div>
          <span class="theme-panel-title">选择主题风格</span>
          <span class="theme-panel-intro">色彩、层级与状态反馈会同步切换</span>
        </div>
        <span class="theme-panel-count">{{ themeStore.themes.length }} 套</span>
      </div>

      <span class="theme-selection-status" aria-live="polite">
        当前：{{ themeStore.currentMeta?.name }}
      </span>

      <section v-for="group in themeGroups" :key="group.key" class="theme-group">
        <div class="theme-group-heading">
          <span class="theme-group-title">{{ group.label }}</span>
          <span class="theme-group-description">{{ group.description }}</span>
        </div>

        <div class="theme-grid" role="group" :aria-label="group.label">
          <button
            v-for="t in group.themes"
            :key="t.key"
            type="button"
            :class="['theme-cell', { active: t.key === themeStore.currentTheme }]"
            :data-theme-key="t.key"
            :title="t.desc"
            :aria-pressed="String(t.key === themeStore.currentTheme)"
            :aria-label="`${t.name}，${t.dark ? '暗色' : '明亮'}主题。${t.desc}${t.key === themeStore.currentTheme ? '，当前已选' : ''}`"
            @click="select(t.key)"
          >
            <span class="theme-preview" :style="previewStyle(t)" aria-hidden="true">
              <span class="preview-nav" />
              <span class="preview-surface">
                <span class="preview-line preview-line-title" />
                <span class="preview-line preview-line-body" />
                <span class="preview-action" />
              </span>
            </span>

            <span class="theme-copy">
              <span class="theme-name">{{ t.name }}</span>
              <span class="theme-description">{{ t.desc }}</span>
              <span class="theme-tag">{{ t.dark ? '暗色' : '明亮' }}</span>
            </span>

            <el-icon v-if="t.key === themeStore.currentTheme" class="theme-check"><Select /></el-icon>
          </button>
        </div>
      </section>
    </div>
  </el-popover>
</template>

<script setup>
/**
 * @component ThemeSwitcher
 * @description 主题切换器。
 * 导航栏放置一个可键盘操作的「主题」按钮，点击后按明亮/暗色主题分组展示。
 * 每个卡片提供真实层级预览、色彩说明和按下状态，点击后即时切换并持久化。
 */
import { computed, ref } from 'vue'
import { Brush, Select } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const isOpen = ref(false)

const themeGroups = computed(() => [
  {
    key: 'light',
    label: '明亮主题',
    description: '适合日间阅读与长文编辑',
    themes: themeStore.themes.filter((theme) => !theme.dark),
  },
  {
    key: 'dark',
    label: '暗色主题',
    description: '适合夜间浏览与专注阅读',
    themes: themeStore.themes.filter((theme) => theme.dark),
  },
])

/**
 * 将主题令牌映射为微型页面预览，不把组件颜色写死在 CSS 中。
 * @param {{swatch: string[], nav?: string}} theme
 */
function previewStyle(theme) {
  return {
    '--theme-preview-canvas': theme.swatch[0],
    '--theme-preview-primary': theme.swatch[1],
    '--theme-preview-text': theme.swatch[2],
    '--theme-preview-surface': theme.swatch[3],
    '--theme-preview-nav': theme.nav || theme.swatch[2],
  }
}

/**
 * 选择并应用主题。
 * @param {string} key - 主题 key
 */
function select(key) {
  themeStore.setTheme(key)
  isOpen.value = false
}
</script>

<style scoped>
.theme-switcher-trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 44px;
  padding: 10px 16px;
  border: 0;
  border-radius: var(--wn-radius-sm);
  background: transparent;
  color: var(--wn-color-nav-text);
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  transition: background-color var(--wn-transition-fast), color var(--wn-transition-fast);
}

.theme-switcher-trigger:hover,
.theme-switcher-trigger[aria-expanded='true'] {
  background: var(--wn-color-nav-hover);
}

.trigger-icon {
  font-size: 16px;
}

.theme-panel {
  padding: 2px;
}

.theme-panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 2px 8px;
}

.theme-panel-title,
.theme-group-title,
.theme-name {
  display: block;
  color: var(--wn-color-text);
  font-weight: 650;
}

.theme-panel-title {
  font-size: 15px;
  line-height: 1.4;
}

.theme-panel-intro,
.theme-group-description,
.theme-description,
.theme-panel-count,
.theme-selection-status,
.theme-tag {
  color: var(--wn-color-text-muted);
}

.theme-panel-intro {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.45;
}

.theme-panel-count {
  flex: none;
  padding-top: 2px;
  font-size: 12px;
}

.theme-selection-status {
  display: block;
  margin: 0 2px 12px;
  padding: 6px 8px;
  border-radius: var(--wn-radius-sm);
  background: var(--wn-color-surface-soft);
  font-size: 12px;
  line-height: 1.35;
}

.theme-group + .theme-group {
  margin-top: 14px;
}

.theme-group-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin: 0 2px 7px;
}

.theme-group-title {
  font-size: 12px;
}

.theme-group-description {
  font-size: 10px;
  white-space: nowrap;
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.theme-cell {
  position: relative;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  min-height: 66px;
  padding: 7px;
  border: 1px solid var(--wn-color-border);
  border-radius: var(--wn-radius-md);
  background: var(--wn-color-surface);
  color: inherit;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition: border-color var(--wn-transition-fast), box-shadow var(--wn-transition-fast),
    transform var(--wn-transition-fast), background-color var(--wn-transition-fast);
}

.theme-cell:hover {
  border-color: var(--wn-color-border-strong);
  box-shadow: var(--wn-shadow-sm);
  transform: translateY(-1px);
}

.theme-cell.active {
  border-color: var(--wn-color-primary);
  box-shadow: 0 0 0 1px var(--wn-color-primary) inset, var(--wn-shadow-sm);
}

.theme-preview {
  position: relative;
  display: block;
  width: 54px;
  height: 42px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--theme-preview-text) 18%, var(--theme-preview-canvas));
  border-radius: calc(var(--wn-radius-sm) - 1px);
  background: var(--theme-preview-canvas);
}

.preview-nav {
  position: absolute;
  inset: 0 auto 0 0;
  width: 12px;
  background: var(--theme-preview-nav);
}

.preview-surface {
  position: absolute;
  inset: 5px 5px 5px 17px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 5px;
  border-radius: 3px;
  background: var(--theme-preview-surface);
}

.preview-line {
  display: block;
  height: 3px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--theme-preview-text) 68%, transparent);
}

.preview-line-title {
  width: 82%;
}

.preview-line-body {
  width: 60%;
  opacity: 0.56;
}

.preview-action {
  width: 13px;
  height: 4px;
  margin-top: auto;
  border-radius: 999px;
  background: var(--theme-preview-primary);
}

.theme-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
}

.theme-name {
  max-width: 100%;
  overflow: hidden;
  font-size: 12px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-description {
  display: -webkit-box;
  overflow: hidden;
  max-width: 100%;
  font-size: 10px;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.theme-tag {
  margin-top: 1px;
  font-size: 10px;
  line-height: 1.2;
}

.theme-check {
  position: absolute;
  top: 5px;
  right: 5px;
  display: grid;
  width: 16px;
  height: 16px;
  place-items: center;
  border-radius: 50%;
  background: var(--wn-color-primary);
  color: var(--wn-color-on-primary);
  font-size: 10px;
}

@media (prefers-reduced-motion: reduce) {
  .theme-switcher-trigger,
  .theme-cell {
    transition: none;
  }

  .theme-cell:hover {
    transform: none;
  }
}
</style>
