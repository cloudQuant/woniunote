<template>
  <el-popover
    placement="bottom-end"
    :width="320"
    trigger="click"
    popper-class="theme-switcher-popover"
  >
    <template #reference>
      <span class="theme-switcher-trigger" :title="`当前主题：${themeStore.currentMeta?.name || ''}`">
        <el-icon class="trigger-icon"><Brush /></el-icon>
        <span class="trigger-label">主题</span>
      </span>
    </template>

    <div class="theme-panel">
      <div class="theme-panel-header">
        <span class="theme-panel-title">选择主题风格</span>
        <span class="theme-panel-count">{{ themeStore.themes.length }} 套</span>
      </div>

      <div class="theme-grid">
        <button
          v-for="t in themeStore.themes"
          :key="t.key"
          type="button"
          :class="['theme-cell', { active: t.key === themeStore.currentTheme }]"
          :title="t.desc"
          @click="select(t.key)"
        >
          <span class="theme-swatch">
            <span
              v-for="(c, i) in t.swatch"
              :key="i"
              class="swatch-dot"
              :style="{ background: c }"
            />
          </span>
          <span class="theme-name">{{ t.name }}</span>
          <span class="theme-tag">{{ t.dark ? '暗' : '浅' }}</span>
          <el-icon v-if="t.key === themeStore.currentTheme" class="theme-check"><Select /></el-icon>
        </button>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
/**
 * @component ThemeSwitcher
 * @description 主题切换器。
 * 导航栏放置一个「主题」入口按钮，点击弹出九宫格主题面板。
 * 每格显示色板小样 + 名称 + 明/暗标记，当前主题高亮，点击即时切换并持久化。
 */
import { Brush, Select } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

/**
 * 选择并应用主题。
 * @param {string} key - 主题 key
 */
function select(key) {
  themeStore.setTheme(key)
}
</script>

<style scoped>
.theme-switcher-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--wn-color-nav-text);
  font-size: 14px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.3s;
}

.theme-switcher-trigger:hover {
  background: var(--wn-color-nav-hover);
}

.trigger-icon {
  font-size: 16px;
}

.theme-panel {
  padding: 4px 2px;
}

.theme-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 2px;
}

.theme-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--wn-color-text);
}

.theme-panel-count {
  font-size: 12px;
  color: var(--wn-color-text-muted);
}

.theme-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.theme-cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 8px;
  border: 1px solid var(--wn-color-border);
  border-radius: var(--wn-radius-md);
  background: var(--wn-color-surface);
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
  text-align: left;
}

.theme-cell:hover {
  transform: translateY(-2px);
  box-shadow: var(--wn-shadow-card);
  border-color: var(--wn-color-primary);
}

.theme-cell.active {
  border-color: var(--wn-color-primary);
  box-shadow: 0 0 0 2px var(--wn-color-primary) inset;
}

.theme-swatch {
  display: flex;
  width: 100%;
  height: 28px;
  border-radius: var(--wn-radius-sm);
  overflow: hidden;
  border: 1px solid var(--wn-color-border);
}

.swatch-dot {
  flex: 1;
}

.theme-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--wn-color-text);
  line-height: 1.2;
}

.theme-tag {
  font-size: 10px;
  color: var(--wn-color-text-muted);
}

.theme-check {
  position: absolute;
  top: 6px;
  right: 6px;
  font-size: 14px;
  color: var(--wn-color-primary);
  background: var(--wn-color-surface);
  border-radius: 50%;
}
</style>
