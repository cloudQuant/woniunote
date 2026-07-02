/**
 * @module stores/article
 * @description 文章状态管理 Store
 * 管理文章分类、热门文章等全局共享数据。
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { articleApi } from '@/api'

export const useArticleStore = defineStore('article', () => {
  // 状态
  /**
   * 文章类型映射表
   * @type {import('vue').Ref<Object<number, string>>}
   */
  const articleTypes = ref({})

  /**
   * 文章分类扁平列表
   * @type {import('vue').Ref<Array>}
   */
  const articleTypeFlat = ref([])

  /**
   * 文章分类树
   * @type {import('vue').Ref<Array>}
   */
  const articleTypeTree = ref([])

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
  function buildFallbackFlat(types) {
    return Object.entries(types).map(([id, name]) => {
      const typeId = parseInt(id)
      const parentId = typeId >= 100 ? Math.floor(typeId / 100) : null
      return {
        id: typeId,
        parent_id: parentId && types[parentId] ? parentId : null,
        name,
        sort_order: typeId,
        visible: 1
      }
    })
  }

  function buildTreeFromFlat(flat) {
    const nodes = new Map()
    const roots = []

    for (const item of flat) {
      nodes.set(item.id, { ...item, children: [] })
    }

    for (const node of nodes.values()) {
      if (node.parent_id && nodes.has(node.parent_id)) {
        nodes.get(node.parent_id).children.push(node)
      } else {
        roots.push(node)
      }
    }

    const sortNodes = (items) => {
      items.sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.id - b.id)
      items.forEach((item) => sortNodes(item.children || []))
      return items
    }

    return sortNodes(roots)
  }

  function normalizeArticleTypes(payload) {
    const data = payload || {}
    const types = data.types || {}
    const flat = Array.isArray(data.flat) && data.flat.length > 0
      ? data.flat
      : buildFallbackFlat(types)
    const tree = Array.isArray(data.tree) && data.tree.length > 0
      ? data.tree
      : buildTreeFromFlat(flat)

    articleTypes.value = types
    articleTypeFlat.value = flat
    articleTypeTree.value = tree
    return articleTypes.value
  }

  async function fetchArticleTypes(force = false) {
    if (!force && Object.keys(articleTypes.value).length > 0) {
      return articleTypes.value
    }

    const res = await articleApi.getTypes()
    return normalizeArticleTypes(res.data)
  }

  async function refreshArticleTypes() {
    return fetchArticleTypes(true)
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

  function getTypePath(typeId) {
    const id = parseInt(typeId)
    if (!id) return []

    const byId = new Map(articleTypeFlat.value.map((item) => [item.id, item]))
    if (byId.size === 0 && Object.keys(articleTypes.value).length > 0) {
      articleTypeFlat.value = buildFallbackFlat(articleTypes.value)
      return getTypePath(id)
    }

    const path = []
    const seen = new Set()
    let current = id
    while (byId.has(current) && !seen.has(current)) {
      seen.add(current)
      path.unshift(current)
      const parentId = byId.get(current).parent_id
      if (!parentId) break
      current = parentId
    }
    return path
  }

  function toCascaderOption(node) {
    const option = {
      value: node.id,
      label: node.name
    }
    if (Array.isArray(node.children) && node.children.length > 0) {
      option.children = node.children.map(toCascaderOption)
    }
    return option
  }

  const categoryOptions = computed(() => {
    if (articleTypeTree.value.length > 0) {
      return articleTypeTree.value.map(toCascaderOption)
    }
    return buildTreeFromFlat(buildFallbackFlat(articleTypes.value)).map(toCascaderOption)
  })

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
    articleTypeFlat,
    articleTypeTree,
    categoryOptions,
    hotArticles,
    fetchArticleTypes,
    refreshArticleTypes,
    getTypeName,
    getTypePath,
    fetchHotArticles
  }
})
