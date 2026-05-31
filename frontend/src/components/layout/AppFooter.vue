<template>
  <footer class="app-footer">
    <div class="footer-container">
      <div class="footer-row">
        <!-- 版权信息 -->
        <div class="footer-col">
          <p class="footer-title">版权所有 © 云金杞</p>
          <p>
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">
              京 ICP 备 2021040304号
            </a>
          </p>
          <p>
            <a href="http://www.beian.gov.cn/portal/registerSystemInfo?recordcode=11010702002337" 
               target="_blank" rel="noopener noreferrer">
              京公网安备 11010702002337 号
            </a>
          </p>
        </div>
        
        <!-- 友情链接 -->
        <div class="footer-col">
          <p class="footer-title">友情链接</p>
          <p>
            <a href="https://blog.csdn.net/qq_26948675/category_11503023.html" target="_blank">CSDN博客</a>
            <a href="https://www.zhihu.com/people/yun-jin-qi" target="_blank">个人知乎</a>
          </p>
        </div>
        
        <!-- 联系博主 -->
        <div class="footer-col">
          <p class="footer-title">联系博主</p>
          <p>北京★孵化园&nbsp;&nbsp;&nbsp;微信：tianjixuetu</p>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
/**
 * @component AppFooter
 * @description 应用底部组件
 * 显示版权信息、备案号、友情链接和联系方式。
 */
</script>

<style scoped>
.app-footer {
  background: var(--wn-color-nav-bg);
  color: var(--wn-color-text-muted);
  padding: var(--wn-space-7) 0;
  margin-top: auto;
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--wn-space-5);
}

.footer-row {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--wn-space-7);
}

.footer-col {
  flex: 1;
  min-width: 200px;
}

.footer-title {
  color: var(--wn-color-nav-text);
  font-size: var(--wn-font-size-md);
  margin-bottom: var(--wn-space-3);
  font-weight: 500;
}

.footer-col p {
  margin: var(--wn-space-2) 0;
  font-size: var(--wn-font-size-base);
  line-height: var(--wn-line-height-normal);
}

.footer-col a {
  color: var(--wn-color-text-muted);
  text-decoration: none;
  margin-right: var(--wn-space-4);
  transition: color 0.3s;
  display: inline-flex;
  align-items: center;
  gap: var(--wn-space-1);
}

.footer-col a:hover {
  color: var(--wn-color-primary);
}

@media (max-width: 768px) {
  .footer-row {
    flex-direction: column;
    text-align: center;
  }
  
  .footer-col {
    min-width: 100%;
  }
}
</style>
