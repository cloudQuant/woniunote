<template>
  <nav class="article-navigation" aria-label="同类文章导航">
    <div class="article-navigation__item article-navigation__previous">
      <span class="article-navigation__label">上一篇文章：</span>
      <router-link
        v-if="previousArticle"
        class="article-navigation__link"
        :to="{ name: 'ArticleDetail', params: { id: previousArticle.articleid } }"
      >
        {{ previousArticle.headline }}
      </router-link>
      <span v-else class="article-navigation__empty">暂无上一篇文章</span>
    </div>
    <div class="article-navigation__item article-navigation__next">
      <span class="article-navigation__label">下一篇文章：</span>
      <router-link
        v-if="nextArticle"
        class="article-navigation__link"
        :to="{ name: 'ArticleDetail', params: { id: nextArticle.articleid } }"
      >
        {{ nextArticle.headline }}
      </router-link>
      <span v-else class="article-navigation__empty">暂无下一篇文章</span>
    </div>
  </nav>
</template>

<script setup>
/**
 * @component ArticleNavigation
 * @description 同类文章上一篇/下一篇导航组件
 * 无相邻文章时降级为占位文案。
 */
defineProps({
  /**
   * 上一篇文章（{ articleid, headline } 或 null）
   */
  previousArticle: {
    type: Object,
    default: null
  },
  /**
   * 下一篇文章（{ articleid, headline } 或 null）
   */
  nextArticle: {
    type: Object,
    default: null
  }
})
</script>

<style scoped>
.article-navigation {
  display: grid;
  gap: 10px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--wn-color-border);
}

.article-navigation__item {
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
  color: var(--wn-color-text-secondary);
  line-height: 1.6;
}

.article-navigation__label {
  flex: 0 0 auto;
  color: var(--wn-color-text);
  font-weight: 500;
}

.article-navigation__link {
  min-width: 0;
  color: var(--wn-color-primary);
  overflow-wrap: anywhere;
  text-decoration: none;
}

.article-navigation__link:hover {
  text-decoration: underline;
}

.article-navigation__link:focus-visible {
  outline: 2px solid var(--wn-color-primary);
  outline-offset: 2px;
  border-radius: 2px;
}

.article-navigation__empty {
  color: var(--wn-color-text-muted);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .article-navigation__item {
    align-items: flex-start;
  }
}
</style>
