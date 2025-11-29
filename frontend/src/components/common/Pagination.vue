<template>
  <div class="pagination" v-if="totalPages > 1">
    <!-- 上一页 -->
    <a 
      v-if="currentPage > 1" 
      class="page-link" 
      @click.prevent="changePage(currentPage - 1)"
    >上一页</a>
    <span v-else class="page-link disabled">上一页</span>
    
    <!-- 页码 -->
    <template v-for="page in displayPages" :key="page">
      <span v-if="page === '...'" class="pagination-ellipsis">...</span>
      <a 
        v-else
        :class="['page-link', { 'current-page': page === currentPage }]"
        @click.prevent="changePage(page)"
      >{{ page }}</a>
    </template>
    
    <!-- 下一页 -->
    <a 
      v-if="currentPage < totalPages" 
      class="page-link" 
      @click.prevent="changePage(currentPage + 1)"
    >下一页</a>
    <span v-else class="page-link disabled">下一页</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: {
    type: Number,
    required: true
  },
  totalPages: {
    type: Number,
    required: true
  },
  maxVisible: {
    type: Number,
    default: 7
  }
})

const emit = defineEmits(['change'])

// 计算要显示的页码
const displayPages = computed(() => {
  const pages = []
  const total = props.totalPages
  const current = props.currentPage
  const halfRange = Math.floor(props.maxVisible / 2)
  
  let startPage = Math.max(1, current - halfRange)
  let endPage = Math.min(total, current + halfRange)
  
  // 调整范围确保显示足够页码
  if (endPage - startPage + 1 < props.maxVisible) {
    if (startPage === 1) {
      endPage = Math.min(total, startPage + props.maxVisible - 1)
    } else if (endPage === total) {
      startPage = Math.max(1, endPage - props.maxVisible + 1)
    }
  }
  
  // 显示第一页和省略号
  if (startPage > 1) {
    pages.push(1)
    if (startPage > 2) {
      pages.push('...')
    }
  }
  
  // 显示页码范围
  for (let i = startPage; i <= endPage; i++) {
    if (i !== 1 && i !== total) {
      pages.push(i)
    } else if (i === 1 && startPage === 1) {
      pages.push(i)
    } else if (i === total && endPage === total) {
      pages.push(i)
    }
  }
  
  // 显示最后一页和省略号
  if (endPage < total) {
    if (endPage < total - 1) {
      pages.push('...')
    }
    pages.push(total)
  }
  
  return pages
})

function changePage(page) {
  if (page !== props.currentPage && page >= 1 && page <= props.totalPages) {
    emit('change', page)
  }
}
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 15px;
  background: #fff;
  border-radius: 5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-top: 15px;
}

.page-link {
  color: #007bff;
  text-decoration: none;
  padding: 5px 10px;
  cursor: pointer;
  transition: color 0.3s;
}

.page-link:hover:not(.disabled):not(.current-page) {
  color: #0056b3;
  text-decoration: underline;
}

.page-link.disabled {
  color: #999;
  cursor: not-allowed;
}

.page-link.current-page {
  color: red;
  font-weight: bold;
  cursor: default;
}

.pagination-ellipsis {
  color: #666;
  padding: 5px;
}
</style>
