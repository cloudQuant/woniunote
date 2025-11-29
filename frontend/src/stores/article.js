import { defineStore } from 'pinia'
import { ref } from 'vue'
import { articleApi } from '@/api'

export const useArticleStore = defineStore('article', () => {
  // 文章类型配置
  const articleTypes = ref({})
  
  // 热门文章
  const hotArticles = ref({
    latest: [],
    most: [],
    recommended: []
  })

  // 获取文章类型
  async function fetchArticleTypes() {
    if (Object.keys(articleTypes.value).length > 0) {
      return articleTypes.value
    }
    
    const res = await articleApi.getTypes()
    articleTypes.value = res.data.types
    return articleTypes.value
  }

  // 获取类型名称
  function getTypeName(typeId) {
    return articleTypes.value[typeId] || '未知分类'
  }

  // 获取热门文章
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
