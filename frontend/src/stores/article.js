/**
 * @module stores/article
 * @description 文章状态管理 Store
 * 管理文章分类、热门文章等全局共享数据。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { articleApi } from '@/api'

export const useArticleStore = defineStore('article', () => {
  // 状态
  /**
   * 文章类型映射表
   * @type {import('vue').Ref<Object<number, string>>}
   */
  const articleTypes = ref({})

  /**
   * 热门文章数据
   * @type {import('vue').Ref<Object>}
   */
  const hotArticles = ref({
    latest: [],
    most: [],
    recommended: []
  })

  // Actions

  /**
   * 获取文章类型列表
   * 如果已缓存则直接返回，否则从 API 获取
   * 
   * @returns {Promise<Object>} 文章类型映射表
   */
  async function fetchArticleTypes() {
    if (Object.keys(articleTypes.value).length > 0) {
      return articleTypes.value
    }

    const res = await articleApi.getTypes()
    articleTypes.value = res.data.types
    return articleTypes.value
  }

  /**
   * 根据类型 ID 获取类型名称
   * 
   * @param {number} typeId - 类型 ID
   * @returns {string} 类型名称
   */
  function getTypeName(typeId) {
    return articleTypes.value[typeId] || '未知分类'
  }

  /**
   * 获取热门文章数据
   * 包括最新、最热和推荐文章
   * 
   * @returns {Promise<Object>} 热门文章数据
   */
  async function fetchHotArticles() {
    const res = await articleApi.getHot()
    hotArticles.value = res.data
    return hotArticles.value
  }

  return {
    articleTypes,
    hotArticles,
    fetchArticleTypes,
    getTypeName,
    fetchHotArticles
  }
})
